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

    # =====================================================================
    #                        ACTUATORS (No Brain Logic)
    # =====================================================================
    # Fungsi-fungsi utility untuk actuator tanpa AI/logika pengambilan keputusan
    
    def actuator_set_path(self, path):
        """Actuator: Set path dan mulai bergerak"""
        self.set_path(path)

    def actuator_go_to_location(self, target_node):
        """Actuator: Pergi ke lokasi tertentu"""
        if target_node == self.current:
            return False
        try:
            path = nx.shortest_path(self.G, self.current, target_node, weight="length")
            self.set_path(path)
            return True
        except:
            return False

    def actuator_go_to_tps(self):
        """Actuator: Pergi ke TPS (random jika ada beberapa)"""
        if not self.TPS_nodes:
            return False
        old_state = self.state
        goal = random.choice(self.TPS_nodes)
        try:
            path = nx.shortest_path(self.G, self.current, goal, weight="length")
            self.set_path(path)
            self.state = "to_tps"
            if old_state == "idle":
                self._update_state_in_garage_stats(old_state)
            return True
        except:
            return False

    def actuator_go_to_tpa(self):
        """Actuator: Pergi ke TPA"""
        if not self.TPA_node:
            return False
        old_state = self.state
        try:
            path = nx.shortest_path(self.G, self.current, self.TPA_node, weight="length")
            self.set_path(path)
            self.state = "to_tpa"
            if old_state == "idle":
                self._update_state_in_garage_stats(old_state)
            return True
        except:
            return False

    def actuator_go_to_garage(self):
        """Actuator: Kembali ke garage"""
        if not self.garage_node:
            return False
        try:
            path = nx.shortest_path(self.G, self.current, self.garage_node, weight="length")
            self.set_path(path)
            self.state = "to_garage"
            return True
        except:
            return False

    def actuator_load_garbage(self, amount):
        """Actuator: Ambil sampah (increment load)"""
        can_load = min(amount, self.max_load - self.load)
        self.load += can_load
        return can_load

    def actuator_unload_garbage(self):
        """Actuator: Buang semua sampah"""
        old_load = self.load
        self.load = 0
        return old_load

    def actuator_get_load_percentage(self):
        """Actuator: Dapatkan persentase load"""
        return (self.load / self.max_load) * 100 if self.max_load > 0 else 0

    def actuator_is_full(self):
        """Actuator: Cek apakah penuh"""
        return self.load >= self.max_load

    def actuator_is_empty(self):
        """Actuator: Cek apakah kosong"""
        return self.load <= 0

    def actuator_get_status(self):
        """Actuator: Dapatkan status lengkap vehicle"""
        return {
            "id": self.id,
            "state": self.state,
            "current_node": self.current,
            "target_node": self.target_node,
            "load": self.load,
            "max_load": self.max_load,
            "load_percentage": self.actuator_get_load_percentage(),
            "is_full": self.actuator_is_full(),
            "is_empty": self.actuator_is_empty(),
            "daily_dist": self.daily_dist,
            "total_dist": self.total_dist,
            "garage_node": self.garage_node,
            "route": self.route
        }

    def actuator_idle(self):
        """Actuator: Kembali ke idle state"""
        old_state = self.state
        self.state = "idle"
        if old_state != "idle":
            self._update_state_in_garage_stats(old_state)
        return True

    # =====================================================================
    #                   DISCOVERY & AGENT INTERACTION
    # =====================================================================
    # Methods untuk agent berinteraksi dengan vehicle dan discover information

    def actuator_arrive_at_tps(self):
        """Actuator: Vehicle tiba di TPS - discover sampah"""
        if self.current in self.TPS_nodes and self.shared:
            tps_data = self.shared.node_type[self.current].get("tps_data", {})
            current_garbage = tps_data.get("sampah_kg", 0)
            
            # Discover sampah di knowledge model
            if hasattr(self.shared, 'knowledge_model'):
                self.shared.knowledge_model.discover_garbage(self.current, current_garbage)
            
            self.state = "at_tps"
            print(f"[Vehicle {self.id}] Arrived at TPS {self.current}, found {current_garbage:.2f} kg")
            return True
        return False

    def actuator_load_from_tps(self, amount=None):
        """Actuator: Load sampah dari TPS saat tiba disana"""
        if self.state != "at_tps" or self.current not in self.TPS_nodes:
            return 0
        
        tps_data = self.shared.node_type[self.current].get("tps_data", {})
        available = tps_data.get("sampah_kg", 0)
        
        # Jika amount tidak ditentukan, ambil semua atau sampai penuh
        if amount is None:
            amount = available
        
        # Load amount yang bisa diambil
        loaded = self.actuator_load_garbage(amount)
        
        # Kurangi sampah di TPS
        tps_data["sampah_kg"] = max(0, available - loaded)
        
        print(f"[Vehicle {self.id}] Loaded {loaded:.2f} kg from TPS {self.current} (remaining: {tps_data['sampah_kg']:.2f} kg)")
        return loaded

    def actuator_arrive_at_tpa(self):
        """Actuator: Vehicle tiba di TPA"""
        if self.current == self.TPA_node:
            self.state = "at_tpa"
            print(f"[Vehicle {self.id}] Arrived at TPA {self.current}")
            return True
        return False

    def actuator_unload_to_tpa(self):
        """Actuator: Unload sampah ke TPA"""
        if self.state != "at_tpa" or self.current != self.TPA_node:
            return 0
        
        unloaded = self.actuator_unload_garbage()
        
        # Update TPA total
        if self.current in self.shared.node_type:
            tpa_data = self.shared.node_type[self.current].get("tpa_data", {})
            tpa_data["total_sampah"] = tpa_data.get("total_sampah", 0) + unloaded
        
        print(f"[Vehicle {self.id}] Unloaded {unloaded:.2f} kg to TPA {self.current}")
        return unloaded

    def actuator_arrive_at_garage(self):
        """Actuator: Vehicle tiba di garage"""
        if self.current == self.garage_node:
            self.state = "idle"
            print(f"[Vehicle {self.id}] Arrived at garage {self.garage_node}")
            return True
        return False

    def actuator_discover_slowdown(self):
        """Actuator: Discover macet di edge saat vehicle melintasi"""
        if not self.target_node or not self.shared:
            return None
        
        edge_id = f"{self.current}-{self.target_node}"
        
        # Cek jika ada slowdown di edge ini
        if hasattr(self.shared, 'edge_type') and edge_id in self.shared.edge_type:
            slowdown = self.shared.edge_type[edge_id].get("slowdown", 0)
            
            # Discover ke knowledge model
            if slowdown > 0 and hasattr(self.shared, 'knowledge_model'):
                self.shared.knowledge_model.discover_slowdown(edge_id, slowdown)
            
            return slowdown
        
        return None

    def actuator_get_current_location(self):
        """Actuator: Dapatkan lokasi saat ini"""
        return self.current

    def actuator_at_target(self):
        """Actuator: Cek apakah sudah tiba di target"""
        return self.target_node is None or self.progress >= 1.0

    # =====================================================================
    #                        ORIGINAL METHODS
    # =====================================================================

    def set_path(self, path):
        self.path = path
        self.route = path.copy()
        if len(path) > 1:
            self.current = path[0]
            self.target_node = path[1]
            self.progress = 0.0

    def go_to_tps(self):
        """Deprecated: gunakan actuator_go_to_tps() sebagai gantinya"""
        return self.actuator_go_to_tps()

    def go_to_tpa(self):
        """Deprecated: gunakan actuator_go_to_tpa() sebagai gantinya"""
        return self.actuator_go_to_tpa()

    def go_to_garage(self):
        """Deprecated: gunakan actuator_go_to_garage() sebagai gantinya"""
        return self.actuator_go_to_garage()

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

        # ===== Apply edge slowdown (macet) =====
        edge_id = f"{self.current}-{self.target_node}"
        actual_speed = real_speed  # default normal speed
        
        if shared and hasattr(shared, 'edge_type') and edge_id in shared.edge_type:
            slowdown_value = shared.edge_type[edge_id].get("slowdown", 0)
            # slowdown > 0 berarti ada macet, ganti kecepatan dengan slowdown value
            if slowdown_value > 0:
                actual_speed = slowdown_value
                
                # ✨ AUTO-DISCOVER SLOWDOWN
                if hasattr(shared, 'knowledge_model'):
                    shared.knowledge_model.discover_slowdown(edge_id, slowdown_value)

        distance = actual_speed * dt
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