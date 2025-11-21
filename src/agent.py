import random
import networkx as nx

class Vehicle:
    def __init__(self, graph, tps_nodes, tpa_node, speed=0.005):
        self.G = graph
        self.TPS_nodes = tps_nodes
        self.TPA_node = tpa_node
        self.current = random.choice(list(graph.nodes()))
        self.path = []
        self.progress = 0.0
        self.target_node = None
        # To tps itu jalan ke tps, kalau to tpa bakal ke tpa
        self.state = "to_tps"
        self.speed = speed

    def set_path(self, path):
        self.path = path
        if len(path) > 1:
            self.current = path[0]
            self.target_node = path[1]
            self.progress = 0.0

    def update(self):
        if not self.path or self.target_node is None:
            # Pilih TPS atau TPA
            goal = random.choice(self.TPS_nodes) if self.state=="to_tps" else self.TPA_node
            path = nx.shortest_path(self.G, self.current, goal, weight="length")
            self.set_path(path)
            return

        self.progress += self.speed
        if self.progress >= 1.0:
            idx = self.path.index(self.target_node)
            if idx + 1 < len(self.path):
                self.current = self.target_node
                self.target_node = self.path[idx + 1]
                self.progress = 0.0
            else:
                self.current = self.target_node
                self.target_node = None
                self.path = []
                # Ganti state
                self.state = "to_tpa" if self.state=="to_tps" else "to_tps"

    def get_pos(self, pos_dict):
        if self.target_node is None:
            return pos_dict[self.current]
        x1, y1 = pos_dict[self.current]
        x2, y2 = pos_dict[self.target_node]
        x = x1 + (x2 - x1) * self.progress
        y = y1 + (y2 - y1) * self.progress
        return (x, y)
