import pygame
import osmnx as ox
from .vehicle import Vehicle
from .utils.viewer import GraphViewer
from .environment import *
from .utils.timesync import sync, getDt
from .utils.controls import controls
from .utils.knowledge import KnowledgeModel
import time
import random

def run_simulation(GRAPH, shared):
    sim_time_acc = 0.0  
    last_time = time.time()
    SCALE_DIV = 1000.0
    pos = {n: (data['x'] / SCALE_DIV, data['y'] / SCALE_DIV)
           for n, data in GRAPH.nodes(data=True)}

    # ===== Viewer =====
    viewer = GraphViewer(pos, shared)
    range_x = viewer.max_x - viewer.min_x
    range_y = viewer.max_y - viewer.min_y

    viewer.scale = min(viewer.WIDTH / range_x, viewer.HEIGHT / range_y) * 0.95
    viewer.offset_x = viewer.WIDTH/2 - ((viewer.min_x+viewer.max_x)/2 - viewer.min_x)*viewer.scale
    viewer.offset_y = viewer.HEIGHT/2 - ((viewer.max_y+viewer.min_y)/2 - viewer.min_y)*viewer.scale

    # ===== INITIALIZE NODE TYPES WITH EMPTY SETS =====
    TPS_nodes = set()
    TPA_nodes = set()
    GARAGE_nodes = set()

    # Initialize node_types (semua node default = bukan TPS/TPA/Garage)
    shared.init_node_types(GRAPH, TPS_nodes, TPA_nodes, GARAGE_nodes)
    
    # ===== EXTRACT ACTUAL TPS/TPA/GARAGE FROM LOADED DATA =====
    # Setelah load, ambil node yang benar-benar bertipe TPS/TPA/Garage
    for node_id, node_data in shared.node_type.items():
        if node_data.get("tps", False):
            TPS_nodes.add(node_id)
        if node_data.get("tpa", False):
            TPA_nodes.add(node_id)
        if node_data.get("garage", False):
            GARAGE_nodes.add(node_id)
    
    print(f"[Simulation] Loaded TPS nodes: {len(TPS_nodes)}")
    print(f"[Simulation] Loaded TPA nodes: {len(TPA_nodes)}")
    print(f"[Simulation] Loaded Garage nodes: {len(GARAGE_nodes)}")
    
    # Update shared stats untuk UI
    shared.node_count = GRAPH.number_of_nodes()
    shared.edge_count = GRAPH.number_of_edges()
    shared.num_tps = len(TPS_nodes)
    shared.num_tpa = len(TPA_nodes)
    shared.num_garage = len(GARAGE_nodes)

    # ===== Initialize garbage di setiap TPS =====
    def generate_tps_garbage():
        """Generate sampah hari pertama di setiap TPS dengan variasi ±30%"""
        for tps_id in TPS_nodes:
            if tps_id in shared.node_type:
                tps_data = shared.node_type[tps_id].get("tps_data", {})
                sampah_per_hari = tps_data.get("sampah_per_hari", 0)  # FIX: Baca dari sampah_per_hari, bukan sampah_kg
                
                print(f"[Simulation] TPS {tps_id}: sampah_per_hari={sampah_per_hari}")
                
                if sampah_per_hari > 0:
                    # Generate dengan variasi random ±30%
                    variance = sampah_per_hari * 0.30  # 30% dari nilai
                    random_variance = random.uniform(-variance, variance)
                    actual_sampah = sampah_per_hari + random_variance
                    actual_sampah = max(0, actual_sampah)  # tidak boleh negatif
                    
                    # SET (bukan tambah) - awal simulasi
                    tps_data["sampah_kg"] = actual_sampah
                    print(f"[Simulation] TPS {tps_id}: Initial garbage {actual_sampah:.2f} kg (dari {sampah_per_hari} ±30%)")
                else:
                    print(f"[Simulation] TPS {tps_id}: No daily garbage configured")

    # Generate garbage di awal simulasi
    generate_tps_garbage()

    # ===== Vehicles - Berdasarkan total_armada per garage =====
    vehicles = []
    garage_list = list(GARAGE_nodes)
    
    if garage_list:
        # Build vehicle allocation berdasarkan total_armada di setiap garage
        vehicles_allocation = {}  # garage_id -> [list of vehicles]
        total_vehicles_created = 0
        
        for garage_id in garage_list:
            if garage_id in shared.node_type:
                garage_data = shared.node_type[garage_id].get("garage_data", {})
                armada_count = garage_data.get("total_armada", 0)
                
                print(f"[Simulation] Garage {garage_id}: {armada_count} armada")
                
                # Create vehicles untuk garage ini
                for i in range(armada_count):
                    vehicle = Vehicle(GRAPH, TPS_nodes, TPA_nodes, [], shared=None)
                    vehicle.shared = shared
                    vehicle.garage_node = garage_id
                    vehicle.current = garage_id
                    vehicle.garage_nodes = list(GARAGE_nodes)
                    vehicle._update_garage_stats()
                    
                    vehicles.append(vehicle)
                    total_vehicles_created += 1
        shared.total_vehicles = total_vehicles_created
        print(f"[Simulation] Total vehicles created: {total_vehicles_created}")
        
        if total_vehicles_created == 0:
            print(f"[Simulation] WARNING: No armada configured in any garage!")
            print(f"[Simulation] Fallback: Creating {shared.get_total_vehicles()} vehicles with round-robin distribution")
            
            for i in range(shared.get_total_vehicles()):
                assigned_garage = garage_list[i % len(garage_list)]
                
                vehicle = Vehicle(GRAPH, TPS_nodes, TPA_nodes, [], shared=None)
                vehicle.shared = shared
                vehicle.garage_node = assigned_garage
                vehicle.current = assigned_garage
                vehicle.garage_nodes = list(GARAGE_nodes)
                vehicle._update_garage_stats()
                
                vehicles.append(vehicle)
    else:
        # Tidak ada garage
        print("[Simulation] WARNING: No garage nodes found!")
    
    shared.vehicles = vehicles

    # ===== Pygame init =====
    pygame.init()
    screen = pygame.display.set_mode((viewer.WIDTH, viewer.HEIGHT))
    pygame.display.set_caption(APP_NAME)
    clock = pygame.time.Clock()

    # ===== Tracking variables =====
    last_garbage_generation_day = shared.sim_day

    # ===== Initialize KnowledgeModel =====
    knowledge_model = KnowledgeModel(GRAPH, shared, TPS_nodes, TPA_nodes, GARAGE_nodes)
    shared.knowledge_model = knowledge_model
    
    # ===== Main loop =====
    running = True
    shared.paused = True
    while running:
        sim_time_acc = sync(shared, sim_time_acc)
        shared.fps = int(clock.get_fps())

        dt, last_time = getDt(time, last_time)
        
        print(f"[Simulation] KnowledgeModel initialized")
        print(f"[Simulation] Agent knowledge: {knowledge_model.get_knowledge_summary()}")

        if not shared.paused:
            sim_time_acc += dt * shared.speed * (60 ** 1)
            total_minutes = int(sim_time_acc / 60)
            shared.sim_hour = (8 + (total_minutes // 60)) % 24
            shared.sim_min = total_minutes % 60
            shared.sim_day = 1 + (total_minutes // (24 * 60))
            
            # ===== Generate garbage harian =====
            if shared.sim_day > last_garbage_generation_day:
                print(f"\n[Simulation] Day {shared.sim_day}: Generating daily garbage...")
                
                # Generate garbage baru dan tambahkan ke yang sudah ada
                for tps_id in TPS_nodes:
                    if tps_id in shared.node_type:
                        tps_data = shared.node_type[tps_id].get("tps_data", {})
                        sampah_per_hari = tps_data.get("sampah_kg", 0)
                        
                        if sampah_per_hari > 0:
                            # Generate dengan variasi random ±30%
                            variance = sampah_per_hari * 0.30
                            random_variance = random.uniform(-variance, variance)
                            daily_garbage = sampah_per_hari + random_variance
                            daily_garbage = max(0, daily_garbage)
                            
                            # TAMBAHKAN ke sampah yang sudah ada (belum diambil)
                            tps_data["sampah_kg"] += daily_garbage
                            print(f"[Simulation] TPS {tps_id}: +{daily_garbage:.2f} kg (total now: {tps_data['sampah_kg']:.2f} kg)")
                
                last_garbage_generation_day = shared.sim_day
        
        controls(viewer, range_x, range_y, GRAPH, vehicles)
        screen.fill((20,20,20))

        viewer.draw_graph(screen, GRAPH, NODE_COL, LINE_COL)
        viewer.draw_dynamic_objects(screen, vehicles)

        for v in vehicles:
            v.update(dt, shared)

        # ===== Update KnowledgeModel dengan vehicle status =====
        for v in vehicles:
            knowledge_model.update_vehicle_status(v.id, v.actuator_get_status())
        
        pygame.display.flip()
        clock.tick(MAX_FPS)