import pygame
import os
import osmnx as ox
from .vehicle import Vehicle
from .utils.location import generate_tps_tpa_garage_nodes
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
    viewer = GraphViewer(pos)
    range_x = viewer.max_x - viewer.min_x
    range_y = viewer.max_y - viewer.min_y

    viewer.scale = min(viewer.WIDTH / range_x, viewer.HEIGHT / range_y) * 0.95
    viewer.offset_x = viewer.WIDTH/2 - ((viewer.min_x+viewer.max_x)/2 - viewer.min_x)*viewer.scale
    viewer.offset_y = viewer.HEIGHT/2 - ((viewer.max_y+viewer.min_y)/2 - viewer.min_y)*viewer.scale

    # ===== TPS / TPA / GARAGE =====
    TPS_nodes, TPA_nodes, GARAGE_nodes = generate_tps_tpa_garage_nodes(
        GRAPH, NUM_TPS, NUM_TPA, NUM_GARAGE
    )

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
        
        controls(viewer, range_x, range_y)
        screen.fill((20,20,20))

        viewer.draw_graph(screen, GRAPH, NODE_COL, LINE_COL)
        viewer.draw_nodes_list(screen, TPS_nodes, TPS_COL, 2)
        viewer.draw_nodes_list(screen, TPA_nodes, TPA_COL, 3)
        viewer.draw_nodes_list(screen, GARAGE_nodes, GARAGE_COL, 4)
        viewer.draw_dynamic_objects(screen, vehicles)

        for v in vehicles:
            v.update(dt, shared)


        pygame.display.flip()
        clock.tick(MAX_FPS)
