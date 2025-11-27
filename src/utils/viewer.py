import pygame
from ..environment import WIDTH, HEIGHT

class GraphViewer:
    def __init__(self, pos_dict, width=WIDTH, height=HEIGHT, node_size=2):
        self.pos = pos_dict
        self.WIDTH = width
        self.HEIGHT = height
        self.NODE_SIZE = node_size
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0

        # range
        self.min_x = min(p[0] for p in pos_dict.values())
        self.max_x = max(p[0] for p in pos_dict.values())
        self.min_y = min(p[1] for p in pos_dict.values())
        self.max_y = max(p[1] for p in pos_dict.values())

        # === CACHE SCREEN COORDINATES ===
        self.cache = {}
        self.last_scale = None
        self.last_offx = None
        self.last_offy = None

    def transform(self, x, y):
        px = (x - self.min_x) * self.scale + self.offset_x
        py = (self.max_y - y) * self.scale + self.offset_y
        return int(px), int(py)

    def transform_cached(self, node):
        x, y = self.pos[node]

        # bila scale/offset berubah → invalidate cache
        if (self.scale != self.last_scale or
            self.offset_x != self.last_offx or
            self.offset_y != self.last_offy):
            self.cache = {}

        # jika sudah ada cache, pakai
        if node in self.cache:
            return self.cache[node]

        # compute baru
        screen_pos = self.transform(x, y)
        self.cache[node] = screen_pos
        return screen_pos

    def finish_frame(self):
        # update last transform state
        self.last_scale = self.scale
        self.last_offx = self.offset_x
        self.last_offy = self.offset_y

    # Draw edges + nodes + culling
    def draw_graph(self, screen, G, node_color, edge_color):
        # edges
        for u, v in G.edges():
            x1, y1 = self.transform_cached(u)
            x2, y2 = self.transform_cached(v)

            if (x1 < -10 and x2 < -10) or (x1 > self.WIDTH+10 and x2 > self.WIDTH+10):
                continue
            if (y1 < -10 and y2 < -10) or (y1 > self.HEIGHT+10 and y2 > self.HEIGHT+10):
                continue

            pygame.draw.line(screen, edge_color, (x1, y1), (x2, y2), 2)

        # nodes
        for n in G.nodes():
            x, y = self.transform_cached(n)
            if -10 <= x <= self.WIDTH+10 and -10 <= y <= self.HEIGHT+10:
                pygame.draw.circle(screen, node_color, (x, y), self.NODE_SIZE)

    def draw_nodes_list(self, screen, nodes, color, radius):
        for node in nodes:
            x, y = self.transform_cached(node)
            if -radius <= x <= self.WIDTH+radius and -radius <= y <= self.HEIGHT+radius:
                pygame.draw.circle(screen, color, (x, y), radius)

    def draw_dynamic_objects(self, screen, vehicles):
        for vehicle in vehicles:
            x, y = vehicle.get_pos(self.pos)
            ax, ay = self.transform(x, y)  # dynamic object tidak perlu cache
            if -6 <= ax <= self.WIDTH+6 and -6 <= ay <= self.HEIGHT+6:
                pygame.draw.circle(screen, (0,255,0), (ax, ay), 6)
