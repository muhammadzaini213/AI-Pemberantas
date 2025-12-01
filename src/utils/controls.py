import pygame
from ..environment import CAM_SPEED

# ===== Controls =====
def controls(viewer, shared, GRAPH, range_x, range_y, vehicles, running, dt):

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            shared.simulation_running = False
            break
        
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if shared.paused:  # Only handle clicks when paused
                viewer.handle_mouse_click(event.pos, GRAPH, vehicles)
        
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            viewer.scale = min(viewer.WIDTH / range_x, viewer.HEIGHT / range_y) * 0.95
            viewer.offset_x = viewer.WIDTH/2 - ((viewer.min_x+viewer.max_x)/2 - viewer.min_x)*viewer.scale
            viewer.offset_y = viewer.HEIGHT/2 - ((viewer.max_y+viewer.min_y)/2 - viewer.min_y)*viewer.scale
        
    
    # ===== CAMERA CONTROLS (continuous key press) =====
    cam_speed = CAM_SPEED * 100 * 0.7
    fast_cam_speed = CAM_SPEED * 300 * 0.7
    keys = pygame.key.get_pressed()

    if keys[pygame.K_LEFT]:  viewer.offset_x += cam_speed * dt
    if keys[pygame.K_RIGHT]: viewer.offset_x -= cam_speed * dt
    if keys[pygame.K_UP]:    viewer.offset_y += cam_speed * dt
    if keys[pygame.K_DOWN]:  viewer.offset_y -= cam_speed * dt

    if keys[pygame.K_LEFT] and keys[pygame.K_SPACE]:  viewer.offset_x += fast_cam_speed * dt
    if keys[pygame.K_RIGHT] and keys[pygame.K_SPACE]: viewer.offset_x -= fast_cam_speed * dt
    if keys[pygame.K_UP] and keys[pygame.K_SPACE]:    viewer.offset_y += fast_cam_speed * dt
    if keys[pygame.K_DOWN] and keys[pygame.K_SPACE]:  viewer.offset_y -= fast_cam_speed * dt

    old_scale = viewer.scale
    zoom_factor = 1
    fast_zoom_factor = 1.5

    if keys[pygame.K_UP] and keys[pygame.K_LSHIFT]: viewer.scale *= 1 + zoom_factor * dt
    if keys[pygame.K_DOWN] and keys[pygame.K_LSHIFT]: viewer.scale *= 1 - zoom_factor * dt
    if keys[pygame.K_UP] and keys[pygame.K_LCTRL]: viewer.scale *= 1 + fast_zoom_factor * dt
    if keys[pygame.K_DOWN] and keys[pygame.K_LCTRL]: viewer.scale *= 1 - fast_zoom_factor * dt

    center_x = viewer.WIDTH / 2
    center_y = viewer.HEIGHT / 2
    viewer.offset_x = center_x - (center_x - viewer.offset_x) * (viewer.scale / old_scale)
    viewer.offset_y = center_y - (center_y - viewer.offset_y) * (viewer.scale / old_scale)