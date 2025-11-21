import random
import networkx as nx
from environment import VEHICLE_SPEED

class Vehicle:
    def __init__(self, graph, tps_nodes=None, tpa_node=None, speed=VEHICLE_SPEED):
        self.G = graph
        self.TPS_nodes = tps_nodes
        self.TPA_node = tpa_node
        self.current = random.choice(list(graph.nodes()))
        self.path = []
        self.progress = 0.0
        self.target_node = None
        self.state = "random"  # ini bisa pakai to_tps atau to_tpa tergantung kebutuhan, sementara random dulu
        self.speed = speed

    def set_path(self, path):
        self.path = path
        if len(path) > 1:
            self.current = path[0]
            self.target_node = path[1]
            self.progress = 0.0

    def go_to_tps(self):
        if not self.TPS_nodes:
            return
        goal = random.choice(self.TPS_nodes)
        path = nx.shortest_path(self.G, self.current, goal, weight="length")
        self.set_path(path)
        self.state = "to_tps"

    def go_to_tpa(self):
        if not self.TPA_node:
            return
        goal = self.TPA_node
        path = nx.shortest_path(self.G, self.current, goal, weight="length")
        self.set_path(path)
        self.state = "to_tpa"

    def update(self):
        if not self.path or self.target_node is None:
            neighbors = list(self.G.neighbors(self.current))
            if not neighbors:
                return
            goal = random.choice(neighbors)
            path = nx.shortest_path(self.G, self.current, goal, weight="length")
            self.set_path(path)
            self.state = "random"
            return

        edge_data = self.G.get_edge_data(self.current, self.target_node)
        length = edge_data[0]['length']
        self.progress += self.speed / length

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

    def get_pos(self, pos_dict):
        if self.target_node is None:
            return pos_dict[self.current]
        x1, y1 = pos_dict[self.current]
        x2, y2 = pos_dict[self.target_node]
        x = x1 + (x2 - x1) * self.progress
        y = y1 + (y2 - y1) * self.progress
        return (x, y)
