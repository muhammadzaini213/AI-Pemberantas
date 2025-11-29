import pygame
import osmnx as ox
from .vehicle import Vehicle
from .sensor import KnowledgeModel
from .ai import AIController
from .utils.helper import (
    initialize_node_data, initialize_edge_data,
    get_tps_waste, sync_tps_waste,
    get_traffic_factor, sync_traffic,
    update_garage_stats, mark_tps_serviced,
    add_tpa_waste, add_tps_daily_waste, reset_daily_stats
)
from .utils.viewer import GraphViewer
from .environment import *
from .utils.timesync import sync, getDt
from .utils.controls import controls
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

    # Initialize node_types
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
    shared.num_vehicle = NUM_VEHICLE

    # ===== VALIDASI: Pastikan ada minimal 1 TPA dan 1 Garage =====
    if len(TPA_nodes) == 0:
        print("[WARNING] No TPA node found! Please set at least one TPA.")
        default_tpa = list(GRAPH.nodes())[0]
        TPA_nodes.add(default_tpa)
        shared.node_type[default_tpa]["tpa"] = True
        print(f"[INFO] Auto-set node {default_tpa} as TPA")
    
    if len(GARAGE_nodes) == 0:
        print("[WARNING] No Garage node found! Please set at least one Garage.")
        default_garage = list(GRAPH.nodes())[1] if len(GRAPH.nodes()) > 1 else list(GRAPH.nodes())[0]
        GARAGE_nodes.add(default_garage)
        shared.node_type[default_garage]["garage"] = True
        print(f"[INFO] Auto-set node {default_garage} as Garage")
    
    # Ambil TPA dan Garage pertama
    TPA_node = list(TPA_nodes)[0]
    GARAGE_node = list(GARAGE_nodes)[0]
    
    # ===== Initialize complete node and edge data =====
    initialize_node_data(shared, GRAPH, TPS_nodes, TPA_nodes, GARAGE_nodes)
    initialize_edge_data(shared, GRAPH)

    # ===== INITIALIZE AI SYSTEM =====
    # 1. Create Vehicles (Actuators)
    vehicles = [
        Vehicle(
            vehicle_id=i,
            graph=GRAPH,
            garage_node=GARAGE_node,
            speed=VEHICLE_SPEED
        )
        for i in range(NUM_VEHICLE)
    ]
    
    # 2. Create Knowledge Model (Sensor)
    knowledge = KnowledgeModel(
        graph=GRAPH,
        tps_nodes=list(TPS_nodes),
        tpa_node=TPA_node,
        garage_node=GARAGE_node
    )
    
    # 3. Create AI Controller (Brain)
    ai_controller = AIController(
        knowledge_model=knowledge,
        vehicles=vehicles,
        shift_start=SHIFT_START,
        shift_end=SHIFT_END
    )
    
    # ===== TPS Waste Simulation (Environment) =====
    # Initialize waste rates untuk semua TPS
    tps_waste_rate = {tps: random.uniform(WASTE_RATE_MIN, WASTE_RATE_MAX) for tps in TPS_nodes}
    
    # Initialize TPS dengan sampah awal
    for tps in TPS_nodes:
        sync_tps_waste(shared, tps, 50.0)  # 50 ton initial waste
    
    # ===== Environment Update Function =====
    def update_environment(dt):
        """Update environment: waste accumulation only"""
        # Update waste di TPS
        for tps in TPS_nodes:
            current_waste = get_tps_waste(shared, tps)
            new_waste = current_waste + tps_waste_rate[tps] * (dt / 3600.0)
            new_waste = min(new_waste, MAX_TPS_CAPACITY)
            sync_tps_waste(shared, tps, new_waste)
        
        # TRAFFIC TIDAK DIUBAH DI SINI
        # Traffic diubah oleh:
        # 1. User manual via edge_state_window
        # 2. AI observation saat vehicle stuck
    
    # ===== Pygame init =====
    pygame.init()
    debug_timer = 0.0
    debug_interval = 5.0  # Print every 5 seconds
    debug_font = pygame.font.Font(None, 20)
    screen = pygame.display.set_mode((viewer.WIDTH, viewer.HEIGHT))
    pygame.display.set_caption(APP_NAME)
    clock = pygame.time.Clock()

    # ===== Decision making interval =====
    decision_interval = AI_DECISION_INTERVAL
    decision_timer = 0.0
    
    # ===== Day tracking =====
    last_day = 1

    # ===== Main loop =====
    running = True
    shared.paused = True
    
    while running:
        sim_time_acc = sync(shared, sim_time_acc)
        shared.fps = int(clock.get_fps())

        dt, last_time = getDt(time, last_time)

        # ===== Update simulation time =====
        if not shared.paused:
            sim_time_acc += dt * shared.speed * (60 ** 1)
            total_minutes = int(sim_time_acc / 60)
            shared.sim_hour = (SHIFT_START + (total_minutes // 60)) % 24
            shared.sim_min = total_minutes % 60
            shared.sim_day = 1 + (total_minutes // (24 * 60))
            
            current_time = shared.sim_hour + shared.sim_min / 60.0
            
            debug_timer += dt
            if debug_timer >= debug_interval:
                debug_traffic_knowledge(shared, knowledge, vehicles, GRAPH)
                debug_timer = 0.0

            # Check if day changed (reset daily stats)
            if shared.sim_day > last_day:
                reset_daily_stats(shared, TPS_nodes)
                last_day = shared.sim_day
                print(f"[Simulation] Day {shared.sim_day} started")
            
            # Update environment
            update_environment(dt)
        
        # ===== Controls =====
        controls(viewer, range_x, range_y, GRAPH)
        screen.fill((20, 20, 20))

        # ===== Draw =====
        viewer.draw_graph(screen, GRAPH, NODE_COL, LINE_COL)
        viewer.draw_dynamic_objects(screen, vehicles)

        # ===== Update vehicles and collect events =====
        if not shared.paused:
            all_events = []
            
            for v in vehicles:
                # Get traffic factor for current edge
                traffic_factor = 1.0
                if v.target_node:
                    edge = (v.current, v.target_node)
                    traffic_factor = get_traffic_factor(shared, edge)
                
                # Update vehicle and collect events
                events = v.update(dt, shared, traffic_factor)
                all_events.extend(events)
                
                # Update vehicle status in knowledge model
                knowledge.update_vehicle_status(v)
            
            # ===== Process events in Knowledge Model =====
            for event in all_events:
                knowledge.process_event(event, current_time)
                
                # ===== Handle special events =====
                event_type = event.get("type")
                vehicle_id = event.get("vehicle_id")
                
                if event_type == "arrived":
                    node = event.get("node")
                    
                    # Arrived at TPS
                    if node in TPS_nodes:
                        actual_waste = get_tps_waste(shared, node)
                        ai_controller.handle_arrival_at_tps(vehicle_id, node, actual_waste)
                        
                        # Mark TPS as being serviced
                        vehicle = ai_controller.vehicles[vehicle_id]
                        if vehicle.state == "Loading":
                            mark_tps_serviced(shared, node, True)
                            # Truk ambil semua sampah
                            collected_waste = actual_waste
                            sync_tps_waste(shared, node, 0.0)
                            add_tps_daily_waste(shared, node, collected_waste)
                    
                    # Arrived at TPA
                    elif node == TPA_node:
                        ai_controller.handle_arrival_at_tpa(vehicle_id)
                    
                    # Arrived at Garage
                    elif node == GARAGE_node:
                        pass  # Standby di garage
                
                elif event_type == "loading_complete":
                    # TPS loading selesai
                    tps = event.get("tps")
                    if tps:
                        mark_tps_serviced(shared, tps, False)
                
                elif event_type == "unloading_complete":
                    # TPA unloading selesai
                    amount = event.get("amount", 0)
                    add_tpa_waste(shared, TPA_node, amount)
                
                elif event_type == "stuck":
                    # Truk застрял - AI learns about traffic
                    edge = event.get("edge")
                    traffic_factor = event.get("traffic_factor")
                    knowledge.observe_traffic(edge, traffic_factor, current_time)
                    # TIDAK mengubah shared.edge_type di sini
                    # Biarkan tetap sesuai yang user set
                    ai_controller.handle_stuck_vehicle(vehicle_id)
            
            # ===== AI Decision Making (periodic) =====
            decision_timer += dt
            if decision_timer >= decision_interval:
                decision_timer = 0.0
                
                # AI makes decisions
                commands = ai_controller.make_decisions(current_time)
                ai_controller.execute_commands(commands)
                
                # Debug: print decisions
                if commands and len(commands) > 0:
                    print(f"[AI] Made {len(commands)} decisions at {shared.sim_hour:02d}:{shared.sim_min:02d}")
            
            # ===== Update Garage Stats =====
            update_garage_stats(shared, GARAGE_node, vehicles)

        pygame.display.flip()
        add_debug_info_to_screen(screen, shared, knowledge, vehicles, debug_font)
        clock.tick(MAX_FPS)





def debug_traffic_knowledge(shared, knowledge, vehicles, GRAPH):
    """
    Print traffic knowledge untuk debugging.
    Call setiap beberapa detik untuk monitor.
    """
    print("\n" + "="*60)
    print("AI TRAFFIC KNOWLEDGE DEBUG")
    print("="*60)
    
    # 1. Check shared.edge_type (user manual settings)
    print("\n[1] USER MANUAL TRAFFIC SETTINGS (shared.edge_type):")
    congested_edges = []
    for edge_id, data in shared.edge_type.items():
        delay = data.get("delay", 0)
        slowdown = data.get("slowdown", 0)
        if delay > 0 or slowdown > 0:
            congested_edges.append((edge_id, delay, slowdown))
    
    if congested_edges:
        for edge_id, delay, slowdown in congested_edges:
            print(f"  Edge {edge_id}: delay={delay}, slowdown={slowdown}")
    else:
        print("  No congestion set by user")
    
    # 2. Check AI knowledge
    print("\n[2] AI KNOWLEDGE (knowledge_model.traffic_knowledge):")
    if knowledge.traffic_knowledge:
        for edge, info in knowledge.traffic_knowledge.items():
            factor = info.get("factor", 1.0)
            last_update = info.get("last_update", 0)
            print(f"  Edge {edge}: factor={factor:.2f}, last_update={last_update:.1f}")
    else:
        print("  AI has NO traffic knowledge yet")
    
    # 3. Check vehicle status on congested edges
    print("\n[3] VEHICLES ON CONGESTED EDGES:")
    for v in vehicles:
        if v.target_node and v.state == "Moving":
            edge = (v.current, v.target_node)
            edge_id = f"{edge[0]}-{edge[1]}"
            
            # Check if this edge is congested
            edge_data = shared.edge_type.get(edge_id, {})
            delay = edge_data.get("delay", 0)
            slowdown = edge_data.get("slowdown", 0)
            
            if delay > 0 or slowdown > 0:
                # Calculate traffic factor
                factor = get_traffic_factor(shared, edge)
                
                print(f"  Vehicle {v.id} on edge {edge_id}:")
                print(f"    State: {v.state}, Factor: {factor:.2f}")
                print(f"    Progress: {v.progress:.2f}, Speed: {v.speed * factor:.1f} m/s")
    
    # 4. Check stuck vehicles
    print("\n[4] STUCK VEHICLES:")
    stuck_vehicles = [v for v in vehicles if v.state == "Stuck"]
    if stuck_vehicles:
        for v in stuck_vehicles:
            edge = (v.current, v.target_node) if v.target_node else None
            print(f"  Vehicle {v.id} stuck at edge {edge}")
    else:
        print("  No vehicles stuck")
    
    # 5. Summary
    print("\n[5] SUMMARY:")
    print(f"  Total edges with congestion (user set): {len(congested_edges)}")
    print(f"  Total edges AI knows about: {len(knowledge.traffic_knowledge)}")
    print(f"  Vehicles stuck: {len(stuck_vehicles)}")
    print(f"  Vehicles moving: {sum(1 for v in vehicles if v.state == 'Moving')}")
    print("="*60 + "\n")


def add_debug_info_to_screen(screen, shared, knowledge, vehicles, font):
    """
    Draw debug info on screen (top-right corner).
    Call di main loop setelah draw everything.
    """
    import pygame
    
    if font is None:
        font = pygame.font.Font(None, 20)
    
    y = 10
    x = screen.get_width() - 300
    
    # Background
    pygame.draw.rect(screen, (0, 0, 0, 180), (x-10, y-10, 290, 200))
    
    # Title
    text = font.render("AI Traffic Debug", True, (255, 255, 0))
    screen.blit(text, (x, y))
    y += 25
    
    # User-set congestion
    congested_count = sum(
        1 for data in shared.edge_type.values() 
        if data.get("delay", 0) > 0 or data.get("slowdown", 0) > 0
    )
    text = font.render(f"Congested edges: {congested_count}", True, (255, 255, 255))
    screen.blit(text, (x, y))
    y += 20
    
    # AI knowledge
    text = font.render(f"AI knows: {len(knowledge.traffic_knowledge)} edges", True, (255, 255, 255))
    screen.blit(text, (x, y))
    y += 20
    
    # Stuck vehicles
    stuck_count = sum(1 for v in vehicles if v.state == "Stuck")
    color = (255, 100, 100) if stuck_count > 0 else (255, 255, 255)
    text = font.render(f"Stuck vehicles: {stuck_count}", True, color)
    screen.blit(text, (x, y))
    y += 20
    
    # Moving on congested
    moving_on_congested = 0
    for v in vehicles:
        if v.target_node and v.state == "Moving":
            edge_id = f"{v.current}-{v.target_node}"
            edge_data = shared.edge_type.get(edge_id, {})
            if edge_data.get("delay", 0) > 0 or edge_data.get("slowdown", 0) > 0:
                moving_on_congested += 1
    
    color = (255, 200, 100) if moving_on_congested > 0 else (255, 255, 255)
    text = font.render(f"On congested: {moving_on_congested}", True, color)
    screen.blit(text, (x, y))
    y += 25
    
    # Show traffic factors of active vehicles
    text = font.render("Active Vehicle Factors:", True, (200, 200, 200))
    screen.blit(text, (x, y))
    y += 20
    
    for v in vehicles:
        if v.target_node and v.state in ["Moving", "Stuck"]:
            edge = (v.current, v.target_node)
            factor = get_traffic_factor(shared, edge)
            
            if factor < 0.95:  # Only show if congested
                color = (255, 100, 100) if factor < 0.3 else (255, 200, 100)
                text = font.render(f"  V{v.id}: {factor:.2f}", True, color)
                screen.blit(text, (x, y))
                y += 18
                
                if y > screen.get_height() - 50:
                    break