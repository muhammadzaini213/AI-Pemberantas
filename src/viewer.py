import pygame

# ======== Viewer / Transform ==========

class GraphViewer:
    def __init__(self, pos_dict, width=1000, height=800, node_size=3):
        self.pos = pos_dict
        self.WIDTH = width
        self.HEIGHT = height
        self.NODE_SIZE = node_size
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.min_x = min(p[0] for p in pos_dict.values())
        self.max_x = max(p[0] for p in pos_dict.values())
        self.min_y = min(p[1] for p in pos_dict.values())
        self.max_y = max(p[1] for p in pos_dict.values())

    def transform(self, x, y):
        px = (x - self.min_x) * self.scale + self.offset_x
        py = (self.max_y - y) * self.scale + self.offset_y
        return int(px), int(py)

    def draw_graph(self, screen, G, node_color=(255,120,120), edge_color=(150,150,150)):
        for u, v in G.edges():
            pygame.draw.line(screen, edge_color,
                             self.transform(*self.pos[u]),
                             self.transform(*self.pos[v]), 1)
        for n in G.nodes():
            pygame.draw.circle(screen, node_color,
                               self.transform(*self.pos[n]),
                               self.NODE_SIZE)

    def draw_nodes_list(self, screen, nodes, color, radius):
        for node in nodes:
            x, y = self.transform(*self.pos[node])
            pygame.draw.circle(screen, color, (x, y), radius)
