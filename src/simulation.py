import pygame
import osmnx as ox
from .vehicle import Vehicle
from .utils.viewer import GraphViewer
from .environment import *
from .utils.timesync import sync, getDt
from .utils.controls import controls
from .utils.knowledge import KnowledgeModel
from .utils.ai_model import AIModel
import time
import random

def run_simulation(GRAPH, shared):
    # ===== CLEAR EXISTING VEHICLES FIRST! =====
    print(f"\n{'='*60}")
    print(f"[Simulation] Starting simulation...")
    print(f"{'='*60}")
    print(f"[Simulation] Existing vehicles: {len(shared.vehicles)}")
    
    # Clear vehicles list
    shared.vehicles.clear()
    shared.total_vehicles = 0
    
    print(f"[Simulation] Vehicles cleared: {len(shared.vehicles)}")
    
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
    
    # Update shared stats
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
                sampah_per_hari = tps_data.get("sampah_per_hari", 0)
                
                if sampah_per_hari > 0:
                    variance = sampah_per_hari * 0.30
                    random_variance = random.uniform(-variance, variance)
                    actual_sampah = sampah_per_hari + random_variance
                    actual_sampah = max(0, actual_sampah)
                    
                    tps_data["sampah_kg"] = actual_sampah
                    print(f"[Simulation] TPS {tps_id}: Initial garbage {actual_sampah:.2f} kg")

    generate_tps_garbage()

    # ===== CREATE VEHICLES =====
    print(f"\n{'='*60}")
    print(f"[Simulation] CREATING VEHICLES")
    print(f"{'='*60}")
    
    # PENTING: Gunakan list lokal dulu, baru assign ke shared di akhir
    vehicles = []
    garage_list = list(GARAGE_nodes)
    
    if garage_list:
        total_vehicles_created = 0
        
        # Reset garage stats sebelum create vehicles
        print(f"[Simulation] Resetting garage stats...")
        for garage_id in garage_list:
            if garage_id in shared.node_type:
                garage_data = shared.node_type[garage_id].get("garage_data", {})
                garage_data["armada_bertugas"] = 0
                garage_data["armada_standby"] = 0
                print(f"[Simulation]   Garage {garage_id}: total_armada={garage_data.get('total_armada', 0)} (reset bertugas/standby)")
        
        # Create vehicles berdasarkan total_armada di setiap garage
        print(f"\n[Simulation] Creating vehicles for each garage...")
        for garage_id in garage_list:
            if garage_id in shared.node_type:
                garage_data = shared.node_type[garage_id].get("garage_data", {})
                armada_count = garage_data.get("total_armada", 0)
                
                if armada_count > 0:
                    print(f"\n[Simulation] Garage {garage_id}: Creating {armada_count} vehicles...")
                    
                    for i in range(armada_count):
                        # Create vehicle (garage_node akan di-set setelah ini)
                        vehicle = Vehicle(GRAPH, TPS_nodes, TPA_nodes, garage_list, shared=shared)
                        
                        # Set garage dan current position SETELAH create
                        vehicle.garage_node = garage_id
                        vehicle.current = garage_id
                        
                        # SEKARANG baru update stats (hanya increment standby/bertugas, bukan total_armada)
                        vehicle._update_garage_stats()
                        
                        # Append ke LOCAL list (bukan shared.vehicles!)
                        vehicles.append(vehicle)
                        total_vehicles_created += 1
                        
                        # Debug: print setiap 10 vehicles
                        if total_vehicles_created % 10 == 0:
                            print(f"[Simulation]   Progress: {total_vehicles_created} vehicles created...")
                    
                    print(f"[Simulation]   ✓ Garage {garage_id}: {armada_count} vehicles created")
        
        print(f"\n{'='*60}")
        print(f"[Simulation] ✓ Total vehicles created: {total_vehicles_created}")
        print(f"{'='*60}")
        
        # Fallback jika tidak ada armada
        if total_vehicles_created == 0:
            print(f"\n[WARNING] No armada configured in any garage!")
            print(f"[WARNING] Skipping vehicle creation...")
        
        shared.total_vehicles = total_vehicles_created
    else:
        print("[WARNING] No garage nodes found!")
    
    # ===== ASSIGN KE SHARED (SEKALI SAJA!) =====
    print(f"\n[Simulation] Assigning vehicles to shared state...")
    print(f"[Simulation]   Local vehicles list: {len(vehicles)}")
    print(f"[Simulation]   Shared vehicles (before): {len(shared.vehicles)}")
    
    shared.vehicles = vehicles
    
    print(f"[Simulation]   Shared vehicles (after): {len(shared.vehicles)}")
    
    # Validasi
    if len(shared.vehicles) != len(vehicles):
        print(f"[ERROR] Mismatch! Local: {len(vehicles)}, Shared: {len(shared.vehicles)}")
    else:
        print(f"[Simulation] ✓ Vehicle assignment successful!")
    
    # Check for duplicates
    vehicle_ids = [v.id for v in shared.vehicles]
    unique_ids = set(vehicle_ids)
    if len(vehicle_ids) != len(unique_ids):
        print(f"[WARNING] Duplicate vehicle IDs detected!")
        print(f"[WARNING]   Total: {len(vehicle_ids)}, Unique: {len(unique_ids)}")
    
    print(f"{'='*60}\n")

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
    
    print(f"[Simulation] KnowledgeModel initialized")
    print(f"[Simulation] Agent knowledge: {knowledge_model.get_knowledge_summary()}")

    # ===== Initialize AIModel =====
    ai_model = AIModel(knowledge_model, shared)
    shared.ai_model = ai_model
    
    print(f"[Simulation] AIModel initialized with Matheuristic Rollout")
    
    # ===== Main loop =====
    running = True
    shared.paused = True
    
    print(f"\n[Simulation] Entering main loop...")
    print(f"[Simulation] simulation_running flag: {shared.simulation_running}")
    
    # ===== CRITICAL: CEK FLAG DALAM LOOP! =====
    while running and shared.simulation_running:
        # Handle pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                shared.simulation_running = False
                break
        
        # ===== CEK FLAG SETIAP ITERASI =====
        if not shared.simulation_running:
            print("[Simulation] simulation_running = False, breaking loop...")
            break
        
        sim_time_acc = sync(shared, sim_time_acc)
        shared.fps = int(clock.get_fps())

        dt, last_time = getDt(time, last_time)

        if not shared.paused:
            sim_time_acc += dt * shared.speed * (60 ** 1)
            total_minutes = int(sim_time_acc / 60)
            shared.sim_hour = (8 + (total_minutes // 60)) % 24
            shared.sim_min = total_minutes % 60
            shared.sim_day = 1 + (total_minutes // (24 * 60))
            
            # ===== Generate garbage harian =====
            if shared.sim_day > last_garbage_generation_day:
                print(f"\n[Simulation] Day {shared.sim_day}: Generating daily garbage...")
                
                # Reset AI daily statistics
                ai_model.reset_daily()
                
                # Generate garbage baru dan tambahkan ke yang sudah ada
                for tps_id in TPS_nodes:
                    if tps_id in shared.node_type:
                        tps_data = shared.node_type[tps_id].get("tps_data", {})
                        sampah_per_hari = tps_data.get("sampah_per_hari", 0)
                        
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
            
            # ===== Update AI Model =====
            ai_model.update(dt, vehicles)
        
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
    
    # ===== CLEANUP =====
    print(f"\n{'='*60}")
    print(f"[Simulation] Main loop ended")
    print(f"[Simulation] Final vehicle count: {len(shared.vehicles)}")
    print(f"{'='*60}\n")
    pygame.quit()