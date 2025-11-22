import pygame
from ..environment import CAM_SPEED

# ===== Controls =====
def controls(viewer):
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