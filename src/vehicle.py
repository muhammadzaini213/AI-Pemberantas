import random
import networkx as nx
from .environment import VEHICLE_SPEED
import uuid

class Vehicle:
    def __init__(self, graph, tps_nodes=None, tpa_node=None, garage_nodes=None, speed=VEHICLE_SPEED, shared=None):
        # Use UUID untuk ID yang truly unique (tidak peduli restart)
        self.id = str(uuid.uuid4())[:8]
        
        self.G = graph
        self.TPS_nodes = tps_nodes
        self.TPA_node = tpa_node
        self.garage_nodes = garage_nodes or []
        self.shared = shared
        
        # ===== Assign vehicle ke garage awal =====
        if garage_nodes and shared:
            self.garage_node = self._assign_to_garage(garage_nodes)
        else:
            self.garage_node = random.choice(list(graph.nodes())) if garage_nodes else None
        
        # Mulai dari garage
        self.current = self.garage_node if self.garage_node else random.choice(list(graph.nodes()))
        
        # ===== Vehicle tracking data =====
        self.path = []
        self.progress = 0.0
        self.target_node = None
        self.state = "idle"  # idle, to_tps, at_tps, to_tpa, at_tpa, to_garage, random
        self.speed = speed
        
        # ===== Tracking metrics =====
        self.daily_dist = 0.0
        self.total_dist = 0.0
        self.load = 0
        self.max_load = 1000
        self.route = []
        
        # Update garage stats di shared.node_type
        self._update_garage_stats()
        
        print(f"[Vehicle] Created ID: {self.id}, garage_node: {self.garage_node}")

    def _assign_to_garage(self, garage_nodes):
        """Assign vehicle ke garage dengan armada paling sedikit"""
        if not garage_nodes or not self.shared:
            return random.choice(garage_nodes) if garage_nodes else None
        
        min_armada = float('inf')
        best_garage = None
        
        for garage_node in garage_nodes:
            # Cek di shared.node_type[garage_node].garage_data.total_armada
            if garage_node in self.shared.node_type:
                garage_data = self.shared.node_type[garage_node].get("garage_data", {})
                total_armada = garage_data.get("total_armada", 0)
                if total_armada < min_armada:
                    min_armada = total_armada
                    best_garage = garage_node
        
        return best_garage if best_garage else random.choice(garage_nodes)

    def _decrement_garage_stats(self, garage_node):
        """Kurangi stats dari garage tertentu"""
        if not garage_node or not self.shared:
            return
        
        if garage_node in self.shared.node_type:
            garage_data = self.shared.node_type[garage_node].get("garage_data", {})
            garage_data["total_armada"] = max(0, garage_data.get("total_armada", 0) - 1)
            
            if self.state == "idle":
                garage_data["armada_standby"] = max(0, garage_data.get("armada_standby", 0) - 1)
            else:
                garage_data["armada_bertugas"] = max(0, garage_data.get("armada_bertugas", 0) - 1)

    def _update_garage_stats(self):
        """Update garage stats di shared.node_type[garage_node].garage_data"""
        if not self.garage_node or not self.shared:
            return
        
        if self.garage_node in self.shared.node_type:
            garage_data = self.shared.node_type[self.garage_node].get("garage_data", {})
            
            # Increment total_armada
            garage_data["total_armada"] = garage_data.get("total_armada", 0) + 1
            
            # Kategori: armada_standby atau armada_bertugas
            if self.state == "idle":
                garage_data["armada_standby"] = garage_data.get("armada_standby", 0) + 1
            else:
                garage_data["armada_bertugas"] = garage_data.get("armada_bertugas", 0) + 1

    def _update_state_in_garage_stats(self, old_state):
        """Update kategorisasi armada saat state berubah (idle ↔ bertugas)"""
        if not self.garage_node or not self.shared:
            return
        
        if self.garage_node in self.shared.node_type:
            garage_data = self.shared.node_type[self.garage_node].get("garage_data", {})
            
            # Kurangi dari kategori lama
            if old_state == "idle":
                garage_data["armada_standby"] = max(0, garage_data.get("armada_standby", 0) - 1)
            else:
                garage_data["armada_bertugas"] = max(0, garage_data.get("armada_bertugas", 0) - 1)
            
            # Tambah ke kategori baru
            if self.state == "idle":
                garage_data["armada_standby"] = garage_data.get("armada_standby", 0) + 1
            else:
                garage_data["armada_bertugas"] = garage_data.get("armada_bertugas", 0) + 1

    def update_garage_assignment(self, new_garage_node):
        """Update garage assignment (saat user pindah vehicle ke garage lain via UI)"""
        if not self.shared or not self.garage_node:
            return
        
        # Kurangi stats dari garage lama
        if self.garage_node in self.shared.node_type:
            old_garage_data = self.shared.node_type[self.garage_node].get("garage_data", {})
            old_garage_data["total_armada"] = max(0, old_garage_data.get("total_armada", 0) - 1)
            
            if self.state == "idle":
                old_garage_data["armada_standby"] = max(0, old_garage_data.get("armada_standby", 0) - 1)
            else:
                old_garage_data["armada_bertugas"] = max(0, old_garage_data.get("armada_bertugas", 0) - 1)
        
        # Assign ke garage baru
        self.garage_node = new_garage_node
        self._update_garage_stats()
        print(f"[Vehicle {self.id}] Reassigned to garage {new_garage_node}")

    def set_path(self, path):
        self.path = path
        self.route = path.copy()
        if len(path) > 1:
            self.current = path[0]
            self.target_node = path[1]
            self.progress = 0.0

    def go_to_tps(self):
        if not self.TPS_nodes:
            return
        old_state = self.state
        goal = random.choice(self.TPS_nodes)
        path = nx.shortest_path(self.G, self.current, goal, weight="length")
        self.set_path(path)
        self.state = "to_tps"
        # Update kategori di garage jika state berubah dari idle
        if old_state == "idle":
            self._update_state_in_garage_stats(old_state)

    def go_to_tpa(self):
        if not self.TPA_node:
            return
        old_state = self.state
        goal = self.TPA_node
        path = nx.shortest_path(self.G, self.current, goal, weight="length")
        self.set_path(path)
        self.state = "to_tpa"
        if old_state == "idle":
            self._update_state_in_garage_stats(old_state)

    def go_to_garage(self):
        if not self.garage_node:
            return
        path = nx.shortest_path(self.G, self.current, self.garage_node, weight="length")
        self.set_path(path)
        self.state = "to_garage"

    def return_to_idle(self):
        """Saat vehicle tiba di garage, kembali ke idle state"""
        old_state = self.state
        self.state = "idle"
        self._update_state_in_garage_stats(old_state)
        print(f"[Vehicle {self.id}] Returned to idle at garage {self.garage_node}")

    def update(self, dt, shared):
        if shared.paused:
            return

        real_speed = self.speed * shared.speed

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

        distance = real_speed * dt
        self.progress += distance / length
        
        # Update distance tracking
        self.daily_dist += distance
        self.total_dist += distance

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
                
                # Jika sudah tiba di garage, kembali ke idle
                if self.state == "to_garage" and self.current == self.garage_node:
                    self.return_to_idle()

    def get_pos(self, pos_dict):
        if self.target_node is None:
            return pos_dict[self.current]
        x1, y1 = pos_dict[self.current]
        x2, y2 = pos_dict[self.target_node]
        x = x1 + (x2 - x1) * self.progress
        y = y1 + (y2 - y1) * self.progress
        return (x, y)