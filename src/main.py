import pygame
import os
import osmnx as ox
from vehicle import Vehicle
from location import generate_tps_tpa_garage_nodes
from viewer import GraphViewer
from environment import *

# ===== Load graph =====
if not os.path.exists(GRAPH_FILE):
    print("Graph file tidak ditemukan:", GRAPH_FILE)
    exit()

GRAPH = ox.load_graphml(GRAPH_FILE)
pos = {n: (data['x'], data['y']) for n, data in GRAPH.nodes(data=True)}

# ===== Viewer =====
viewer = GraphViewer(pos)
range_x = viewer.max_x - viewer.min_x
range_y = viewer.max_y - viewer.min_y
viewer.scale = min(viewer.WIDTH / range_x, viewer.HEIGHT / range_y) * 0.95
viewer.offset_x = viewer.WIDTH/2 - ((viewer.min_x+viewer.max_x)/2 - viewer.min_x)*viewer.scale
viewer.offset_y = viewer.HEIGHT/2 - ((viewer.max_y+viewer.min_y)/2 - viewer.min_y)*viewer.scale

# ===== TPS / TPA / GARAGE =====
TPS_nodes, TPA_nodes, GARAGE_nodes = generate_tps_tpa_garage_nodes(GRAPH, NUM_TPS, NUM_TPA, NUM_GARAGE)

# ===== Vehicles =====
vehicles = [Vehicle(GRAPH, TPS_nodes, TPA_nodes) for _ in range(NUM_VEHICLE)]

# ===== Pygame init =====
pygame.init()
screen = pygame.display.set_mode((viewer.WIDTH, viewer.HEIGHT))
pygame.display.set_caption(APP_NAME)
clock = pygame.time.Clock()

# ===== Controls =====
def controls():
    cam_speed = CAM_SPEED
    fast_cam_speed = CAM_SPEED * 3
    keys = pygame.key.get_pressed()

    if keys[pygame.K_LEFT]:  viewer.offset_x += cam_speed
    if keys[pygame.K_RIGHT]: viewer.offset_x -= cam_speed
    if keys[pygame.K_UP]:    viewer.offset_y += cam_speed
    if keys[pygame.K_DOWN]:  viewer.offset_y -= cam_speed

    if keys[pygame.K_LEFT] and keys[pygame.K_SPACE]:  viewer.offset_x += fast_cam_speed
    if keys[pygame.K_RIGHT] and keys[pygame.K_SPACE]: viewer.offset_x -= fast_cam_speed
    if keys[pygame.K_UP] and keys[pygame.K_SPACE]:    viewer.offset_y += fast_cam_speed
    if keys[pygame.K_DOWN] and keys[pygame.K_SPACE]:  viewer.offset_y -= fast_cam_speed

    # zoom
    old_scale = viewer.scale
    zoom_factor = 0.05
    fast_zoom_factor = 0.15

    if keys[pygame.K_UP] and keys[pygame.K_LSHIFT]: viewer.scale *= 1 + zoom_factor
    if keys[pygame.K_DOWN] and keys[pygame.K_LSHIFT]: viewer.scale *= 1 - zoom_factor
    if keys[pygame.K_UP] and keys[pygame.K_LCTRL]: viewer.scale *= 1 + fast_zoom_factor
    if keys[pygame.K_DOWN] and keys[pygame.K_LCTRL]: viewer.scale *= 1 - fast_zoom_factor

    center_x = viewer.WIDTH / 2
    center_y = viewer.HEIGHT / 2
    viewer.offset_x = center_x - (center_x - viewer.offset_x) * (viewer.scale / old_scale)
    viewer.offset_y = center_y - (center_y - viewer.offset_y) * (viewer.scale / old_scale)

# ===== Main loop =====
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            # reset view
            viewer.scale = min(viewer.WIDTH / range_x, viewer.HEIGHT / range_y) * 0.95
            viewer.offset_x = viewer.WIDTH/2 - ((viewer.min_x+viewer.max_x)/2 - viewer.min_x)*viewer.scale
            viewer.offset_y = viewer.HEIGHT/2 - ((viewer.max_y+viewer.min_y)/2 - viewer.min_y)*viewer.scale

    controls()
    screen.fill((20,20,20))

    # draw graph + nodes + vehicles
    viewer.draw_graph(screen, GRAPH, NODE_COL, LINE_COL)
    viewer.draw_nodes_list(screen, TPS_nodes, TPS_COL, 2)
    viewer.draw_nodes_list(screen, TPA_nodes, TPA_COL, 3)
    viewer.draw_nodes_list(screen, GARAGE_nodes, GARAGE_COL, 4)
    viewer.draw_dynamic_objects(screen, vehicles)

    # update vehicle positions
    for v in vehicles:
        v.update()

    pygame.display.flip()
    clock.tick(MAX_FPS)

pygame.quit()
