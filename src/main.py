import os
import osmnx as ox
import pygame
from agent import Vehicle
from location import generate_tps_tpa_nodes
from viewer import GraphViewer

GRAPH_FILE = "./data/klandasan_ilir_drive.graphml"
NUM_AGENTS = 3
NUM_TPS = 3

# ===== Load graph =====
if not os.path.exists(GRAPH_FILE):
    print("Graph file tidak ditemukan:", GRAPH_FILE)
    exit()

G = ox.load_graphml(GRAPH_FILE)
pos = {n: (data['x'], data['y']) for n, data in G.nodes(data=True)}

# ===== Viewer init =====
viewer = GraphViewer(pos)
range_x = viewer.max_x - viewer.min_x
range_y = viewer.max_y - viewer.min_y
viewer.scale = min(viewer.WIDTH / range_x, viewer.HEIGHT / range_y) * 0.95
viewer.offset_x = viewer.WIDTH/2 - ((viewer.min_x+viewer.max_x)/2 - viewer.min_x)*viewer.scale
viewer.offset_y = viewer.HEIGHT/2 - ((viewer.max_y+viewer.min_y)/2 - viewer.min_y)*viewer.scale

# ===== TPS & TPA =====
TPS_nodes, TPA_node = generate_tps_tpa_nodes(G, NUM_TPS)
print("TPS nodes:", TPS_nodes)
print("TPA node:", TPA_node)

# ===== Agents =====
agents = [Vehicle(G, TPS_nodes, TPA_node) for _ in range(NUM_AGENTS)]

# ===== Pygame init =====
pygame.init()
screen = pygame.display.set_mode((viewer.WIDTH, viewer.HEIGHT))
pygame.display.set_caption("Balikpapan Graph + Agent TPS/TPA")
clock = pygame.time.Clock()
move_speed = 20

# ===== Main loop =====
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                # reset view
                viewer.scale = min(viewer.WIDTH / range_x, viewer.HEIGHT / range_y) * 0.95
                viewer.offset_x = viewer.WIDTH/2 - ((viewer.min_x+viewer.max_x)/2 - viewer.min_x)*viewer.scale
                viewer.offset_y = viewer.HEIGHT/2 - ((viewer.max_y+viewer.min_y)/2 - viewer.min_y)*viewer.scale
        elif event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            old_scale = viewer.scale
            viewer.scale += event.y * 0.1
            viewer.scale = max(0.02, min(viewer.scale, 60))
            viewer.offset_x = mx - (mx - viewer.offset_x) * (viewer.scale/old_scale)
            viewer.offset_y = my - (my - viewer.offset_y) * (viewer.scale/old_scale)

    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:  viewer.offset_x += move_speed
    if keys[pygame.K_RIGHT]: viewer.offset_x -= move_speed
    if keys[pygame.K_UP]:    viewer.offset_y += move_speed
    if keys[pygame.K_DOWN]:  viewer.offset_y -= move_speed

    screen.fill((20,20,20))

    # Draw everything
    viewer.draw_graph(screen, G)
    viewer.draw_nodes_list(screen, TPS_nodes, (255,220,0), 10)
    viewer.draw_nodes_list(screen, [TPA_node], (0,150,255), 14)

    # Update & draw agents
    for agent in agents:
        agent.update()
        ax, ay = viewer.transform(*agent.get_pos(pos))
        pygame.draw.circle(screen, (0,255,0), (ax, ay), 6)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
