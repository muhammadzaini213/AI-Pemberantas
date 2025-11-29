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
    
    # ===== DEBUG: Print TPA details =====
    if TPA_nodes:
        print(f"[Simulation] TPA nodes list: {list(TPA_nodes)}")
    else:
        print(f"[Simulation] ⚠️ WARNING: NO TPA NODES CONFIGURED!")
    
    shared.node_count = GRAPH.number_of_nodes()
    shared.edge_count = GRAPH.number_of_edges()
    shared.num_tps = len(TPS_nodes)
    shared.num_tpa = len(TPA_nodes)
    shared.num_garage = len(GARAGE_nodes)

    # ===== Initialize garbage di setiap TPS =====
    def generate_tps_garbage():
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
    
    vehicles = []
    garage_list = list(GARAGE_nodes)
    
    if garage_list:
        total_vehicles_created = 0
        
        print(f"[Simulation] Resetting garage stats...")
        for garage_id in garage_list:
            if garage_id in shared.node_type:
                garage_data = shared.node_type[garage_id].get("garage_data", {})
                garage_data["armada_bertugas"] = 0
                garage_data["armada_standby"] = 0
                print(f"[Simulation]   Garage {garage_id}: total_armada={garage_data.get('total_armada', 0)}")
        
        print(f"\n[Simulation] Creating vehicles for each garage...")
        for garage_id in garage_list:
            if garage_id in shared.node_type:
                garage_data = shared.node_type[garage_id].get("garage_data", {})
                armada_count = garage_data.get("total_armada", 0)
                
                if armada_count > 0:
                    print(f"\n[Simulation] Garage {garage_id}: Creating {armada_count} vehicles...")
                    
                    for i in range(armada_count):
                        vehicle = Vehicle(GRAPH, TPS_nodes, TPA_nodes, garage_list, shared=shared)
                        vehicle.garage_node = garage_id
                        vehicle.current = garage_id
                        vehicle._update_garage_stats()
                        
                        vehicles.append(vehicle)
                        total_vehicles_created += 1
                        
                        if total_vehicles_created % 10 == 0:
                            print(f"[Simulation]   Progress: {total_vehicles_created} vehicles created...")
                    
                    print(f"[Simulation]   ✓ Garage {garage_id}: {armada_count} vehicles created")
        
        print(f"\n{'='*60}")
        print(f"[Simulation] ✓ Total vehicles created: {total_vehicles_created}")
        print(f"{'='*60}")
        
        if total_vehicles_created == 0:
            print(f"\n[WARNING] No armada configured in any garage!")
        
        shared.total_vehicles = total_vehicles_created
    else:
        print("[WARNING] No garage nodes found!")
    
    # ===== ASSIGN KE SHARED =====
    print(f"\n[Simulation] Assigning vehicles to shared state...")
    print(f"[Simulation]   Local: {len(vehicles)}, Shared (before): {len(shared.vehicles)}")
    
    shared.vehicles = vehicles
    
    print(f"[Simulation]   Shared (after): {len(shared.vehicles)}")
    
    if len(shared.vehicles) != len(vehicles):
        print(f"[ERROR] Mismatch! Local: {len(vehicles)}, Shared: {len(shared.vehicles)}")
    else:
        print(f"[Simulation] ✓ Vehicle assignment successful!")
    
    vehicle_ids = [v.id for v in shared.vehicles]
    unique_ids = set(vehicle_ids)
    if len(vehicle_ids) != len(unique_ids):
        print(f"[WARNING] Duplicate vehicle IDs!")
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
    
    # ===== MAIN LOOP WITH CENTRALIZED EVENT HANDLING =====
    while running and shared.simulation_running:
        # ===== CENTRALIZED EVENT HANDLING =====
        # Handle ALL events di satu tempat untuk menghindari event queue kosong
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                shared.simulation_running = False
                break
            
            # Handle mouse click untuk node/vehicle/edge selection
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if shared.paused:  # Only handle clicks when paused
                    viewer.handle_mouse_click(event.pos, GRAPH, vehicles)
            
            # Handle reset view (R key)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                viewer.scale = min(viewer.WIDTH / range_x, viewer.HEIGHT / range_y) * 0.95
                viewer.offset_x = viewer.WIDTH/2 - ((viewer.min_x+viewer.max_x)/2 - viewer.min_x)*viewer.scale
                viewer.offset_y = viewer.HEIGHT/2 - ((viewer.max_y+viewer.min_y)/2 - viewer.min_y)*viewer.scale
        
        # ===== CEK FLAG =====
        if not shared.simulation_running:
            print("[Simulation] simulation_running = False, breaking loop...")
            break
        
        # ===== CAMERA CONTROLS (continuous key press) =====
        # Handle camera movement dengan continuous key press
        cam_speed = CAM_SPEED
        fast_cam_speed = CAM_SPEED * 3
        keys = pygame.key.get_pressed()

        # Pan camera
        if keys[pygame.K_LEFT]:  viewer.offset_x += cam_speed
        if keys[pygame.K_RIGHT]: viewer.offset_x -= cam_speed
        if keys[pygame.K_UP]:    viewer.offset_y += cam_speed
        if keys[pygame.K_DOWN]:  viewer.offset_y -= cam_speed

        # Fast pan
        if keys[pygame.K_LEFT] and keys[pygame.K_SPACE]:  viewer.offset_x += fast_cam_speed
        if keys[pygame.K_RIGHT] and keys[pygame.K_SPACE]: viewer.offset_x -= fast_cam_speed
        if keys[pygame.K_UP] and keys[pygame.K_SPACE]:    viewer.offset_y += fast_cam_speed
        if keys[pygame.K_DOWN] and keys[pygame.K_SPACE]:  viewer.offset_y -= fast_cam_speed

        # Zoom
        old_scale = viewer.scale
        zoom_factor = 0.05
        fast_zoom_factor = 0.15

        if keys[pygame.K_UP] and keys[pygame.K_LSHIFT]: viewer.scale *= 1 + zoom_factor
        if keys[pygame.K_DOWN] and keys[pygame.K_LSHIFT]: viewer.scale *= 1 - zoom_factor
        if keys[pygame.K_UP] and keys[pygame.K_LCTRL]: viewer.scale *= 1 + fast_zoom_factor
        if keys[pygame.K_DOWN] and keys[pygame.K_LCTRL]: viewer.scale *= 1 - fast_zoom_factor

        # Center zoom
        center_x = viewer.WIDTH / 2
        center_y = viewer.HEIGHT / 2
        viewer.offset_x = center_x - (center_x - viewer.offset_x) * (viewer.scale / old_scale)
        viewer.offset_y = center_y - (center_y - viewer.offset_y) * (viewer.scale / old_scale)
        
        # ===== SIMULATION UPDATE =====
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
                
                ai_model.reset_daily()
                
                for tps_id in TPS_nodes:
                    if tps_id in shared.node_type:
                        tps_data = shared.node_type[tps_id].get("tps_data", {})
                        sampah_per_hari = tps_data.get("sampah_per_hari", 0)
                        
                        if sampah_per_hari > 0:
                            variance = sampah_per_hari * 0.30
                            random_variance = random.uniform(-variance, variance)
                            daily_garbage = sampah_per_hari + random_variance
                            daily_garbage = max(0, daily_garbage)
                            
                            tps_data["sampah_kg"] += daily_garbage
                            print(f"[Simulation] TPS {tps_id}: +{daily_garbage:.2f} kg (total: {tps_data['sampah_kg']:.2f} kg)")
                
                last_garbage_generation_day = shared.sim_day
            
            # ===== Update AI Model =====
            ai_model.update(dt, vehicles)
        
        # ===== RENDERING =====
        screen.fill((20,20,20))

        viewer.draw_graph(screen, GRAPH, NODE_COL, LINE_COL)
        viewer.draw_dynamic_objects(screen, vehicles)

        # ===== Update vehicles =====
        for v in vehicles:
            v.update(dt, shared)

        # ===== Update KnowledgeModel =====
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