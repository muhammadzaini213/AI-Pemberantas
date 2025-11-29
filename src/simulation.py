import pygame
from .utils.viewer import GraphViewer
from .environment import *
from .utils.timesync import sync, getDt
from .utils.controls import controls
from .utils.nodes import initNodes, generate_daily_garbage, generate_car_in_garage
from .classes.knowledge import KnowledgeModel
from .classes.ai_model import AIModel
import time

def run_simulation(GRAPH, shared):
    
    # ===== CLEAR EXISTING VEHICLES =====
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

    TPS_nodes, TPA_nodes, GARAGE_nodes = initNodes(GRAPH, shared)
    
    vehicles = []
    generate_car_in_garage(GARAGE_nodes, shared, vehicles, GRAPH, TPS_nodes, TPA_nodes)

    last_garbage_generation_day = shared.sim_day

    knowledge_model = KnowledgeModel(GRAPH, shared, TPS_nodes, TPA_nodes, GARAGE_nodes)
    shared.knowledge_model = knowledge_model
    
    print(f"[Simulation] KnowledgeModel initialized")
    print(f"[Simulation] Agent knowledge: {knowledge_model.get_knowledge_summary()}")

    ai_model = AIModel(knowledge_model, shared)
    shared.ai_model = ai_model
    
    print(f"[Simulation] AIModel initialized with Matheuristic Rollout")
    
    running = True
    shared.paused = True
    
    print(f"\n[Simulation] Entering main loop...")
    print(f"[Simulation] simulation_running flag: {shared.simulation_running}")
    

    # ============= INITIALIZE =============
    pygame.init()
    screen = pygame.display.set_mode((viewer.WIDTH, viewer.HEIGHT))
    pygame.display.set_caption(APP_NAME)
    clock = pygame.time.Clock()

    while running and shared.simulation_running:
        if not shared.simulation_running:
            print("[Simulation] simulation_running = False, breaking loop...")
            break
        
        controls(viewer, shared, GRAPH, range_x, range_y, vehicles, running)
        
        sim_time_acc = sync(shared, sim_time_acc)
        shared.fps = int(clock.get_fps())

        dt, last_time = getDt(time, last_time)

        if not shared.paused:
            sim_time_acc += dt * shared.speed * (60 ** 1)
            total_minutes = int(sim_time_acc / 60)
            shared.sim_hour = (8 + (total_minutes // 60)) % 24
            shared.sim_min = total_minutes % 60
            shared.sim_day = 1 + (total_minutes // (24 * 60))
            
            last_garbage_generation_day = generate_daily_garbage(shared, TPS_nodes, ai_model, last_garbage_generation_day)
            
            ai_model.update(dt, vehicles)
        
        screen.fill((20,20,20))
        viewer.draw_graph(screen, GRAPH, NODE_COL, LINE_COL)
        viewer.draw_dynamic_objects(screen, vehicles)

        for v in vehicles:
            v.update(dt, shared)

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