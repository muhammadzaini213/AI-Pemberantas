import pygame
import osmnx as ox
from .vehicle import Vehicle
from .utils.viewer import GraphViewer
from .environment import *
from .utils.timesync import sync, getDt
from .utils.controls import controls
import time

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
    # Node types akan diisi dari saved data atau manual via UI
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
    shared.num_vehicle = NUM_VEHICLE

    # ===== Vehicles =====
    vehicles = [Vehicle(GRAPH, TPS_nodes, TPA_nodes)
                for _ in range(NUM_VEHICLE)]

    # ===== Pygame init =====
    pygame.init()
    screen = pygame.display.set_mode((viewer.WIDTH, viewer.HEIGHT))
    pygame.display.set_caption(APP_NAME)
    clock = pygame.time.Clock()

    # ===== Main loop =====
    running = True
    shared.paused = True
    while running:
        sim_time_acc = sync(shared, sim_time_acc)
        shared.fps = int(clock.get_fps())

        dt, last_time = getDt(time, last_time)

        if not shared.paused:
            sim_time_acc += dt * shared.speed * 60000 
            total_minutes = int(sim_time_acc / 60)
            shared.sim_hour = (8 + (total_minutes // 60)) % 24
            shared.sim_min = total_minutes % 60
            shared.sim_day = 1 + (total_minutes // (24 * 60))
        
        controls(viewer, range_x, range_y, GRAPH)
        screen.fill((20,20,20))

        viewer.draw_graph(screen, GRAPH, NODE_COL, LINE_COL)
        viewer.draw_dynamic_objects(screen, vehicles)

        for v in vehicles:
            v.update(dt, shared)

        pygame.display.flip()
        clock.tick(MAX_FPS)