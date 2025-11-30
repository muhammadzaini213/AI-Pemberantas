import random
import networkx as nx
from ..environment import VEHICLE_SPEED, VEHICLE_CAP
import uuid

class Vehicle:
    def __init__(self, graph, tps_nodes=None, tpa_node=None, garage_nodes=None, shared=None):
        self.id = str(uuid.uuid4())[:8]
        
        self.G = graph
        self.TPS_nodes = tps_nodes
        self.TPA_node = tpa_node
        self.garage_nodes = garage_nodes or []
        self.shared = shared
        self.garage_node = None 
        self.current = None
        
        # ===== Vehicle tracking data =====
        self.path = []
        self.progress = 0.0
        self.target_node = None
        self.state = "idle"
        self.speed = VEHICLE_SPEED  # Speed in meters/second or km/hour
        
        # ===== Tracking metrics (in meters) =====
        self.daily_dist = 0.0
        self.total_dist = 0.0
        self.load = 0
        self.max_load = VEHICLE_CAP
        self.route = []
        
        print(f"[Vehicle] Created ID: {self.id}")

    def _update_garage_stats(self):
        if not self.garage_node or not self.shared:
            return
        
        if self.garage_node in self.shared.node_type:
            garage_data = self.shared.node_type[self.garage_node].get("garage_data", {})
            
            if self.state == "idle":
                garage_data["armada_standby"] = garage_data.get("armada_standby", 0) + 1
            else:
                garage_data["armada_bertugas"] = garage_data.get("armada_bertugas", 0) + 1
            
            print(f"[Vehicle {self.id}] Updated garage {self.garage_node} stats: standby={garage_data.get('armada_standby', 0)}, bertugas={garage_data.get('armada_bertugas', 0)}")

    def _update_state_in_garage_stats(self, old_state):
        if not self.garage_node or not self.shared:
            return
        
        if self.garage_node in self.shared.node_type:
            garage_data = self.shared.node_type[self.garage_node].get("garage_data", {})
            
            if old_state == "idle":
                garage_data["armada_standby"] = max(0, garage_data.get("armada_standby", 0) - 1)
            else:
                garage_data["armada_bertugas"] = max(0, garage_data.get("armada_bertugas", 0) - 1)
            
            if self.state == "idle":
                garage_data["armada_standby"] = garage_data.get("armada_standby", 0) + 1
            else:
                garage_data["armada_bertugas"] = garage_data.get("armada_bertugas", 0) + 1

    def _decrement_garage_stats(self, garage_node):
        if not garage_node or not self.shared:
            return
        
        if garage_node in self.shared.node_type:
            garage_data = self.shared.node_type[garage_node].get("garage_data", {})
            
            if self.state == "idle":
                garage_data["armada_standby"] = max(0, garage_data.get("armada_standby", 0) - 1)
            else:
                garage_data["armada_bertugas"] = max(0, garage_data.get("armada_bertugas", 0) - 1)

    def update_garage_assignment(self, new_garage_node):
        if not self.shared or not self.garage_node:
            return
        
        self._decrement_garage_stats(self.garage_node)
        
        self.garage_node = new_garage_node
        self._update_garage_stats()
        print(f"[Vehicle {self.id}] Reassigned to garage {new_garage_node}")




    # ============== ACTUATOR (NO BRAIN LOGIC) ==============    
    def actuator_set_path(self, path):
        self.set_path(path)

    def actuator_go_to_location(self, target_node):
        if target_node == self.current:
            return False
        try:
            path = nx.shortest_path(self.G, self.current, target_node, weight="length")
            self.set_path(path)
            return True
        except:
            return False

    def actuator_go_to_tps(self):
        if not self.TPS_nodes:
            return False
        old_state = self.state
        goal = random.choice(list(self.TPS_nodes))
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
        if not self.TPA_node:
            print(f"[Vehicle {self.id}] ERROR: No TPA_node configured!")
            return False
        
        if isinstance(self.TPA_node, (set, list)):
            if len(self.TPA_node) == 0:
                print(f"[Vehicle {self.id}] ERROR: TPA_node is empty set/list!")
                return False
            tpa_target = list(self.TPA_node)[0]
        else:
            tpa_target = self.TPA_node
        
        if self.current == tpa_target:
            print(f"[Vehicle {self.id}] Already at TPA {tpa_target}")
            self.state = "at_tpa"
            return True
        
        old_state = self.state
        try:
            path = nx.shortest_path(self.G, self.current, tpa_target, weight="length")
            
            if not path or len(path) < 2:
                print(f"[Vehicle {self.id}] ERROR: Invalid path to TPA!")
                return False
            
            self.set_path(path)
            self.state = "to_tpa"
            
            if old_state == "idle":
                self._update_state_in_garage_stats(old_state)
            
            path_distance = sum(
            self.G[path[i]][path[i+1]][0]['length'] 
            for i in range(len(path)-1)
            )
            print(f"[Vehicle] {self.id} Routing to TPA {tpa_target} (distance: {path_distance:.0f}m / {path_distance/1000:.2f}km)")  # ✅ meter & km
            return True
        except Exception as e:
            print(f"[Vehicle {self.id}] ERROR: Failed to route to TPA: {e}")
            return False

    def actuator_go_to_garage(self):
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
        can_load = min(amount, self.max_load - self.load)
        self.load += can_load
        return can_load

    def actuator_unload_garbage(self):
        old_load = self.load
        self.load = 0
        return old_load

    def actuator_get_load_percentage(self):
        return (self.load / self.max_load) * 100 if self.max_load > 0 else 0

    def actuator_is_full(self):
        return self.load >= self.max_load

    def actuator_is_empty(self):
        return self.load <= 0

    def actuator_get_status(self):
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
            "daily_dist": self.daily_dist / 10_000_000,
            "total_dist": self.total_dist / 10_000_000,
            "garage_node": self.garage_node,
            "route": self.route
        }

    def actuator_idle(self):
        old_state = self.state
        self.state = "idle"
        if old_state != "idle":
            self._update_state_in_garage_stats(old_state)
        return True

    # ============== ACTUATORS + SENSORS LOGIC==============
    def actuator_arrive_at_tps(self):
        if self.current in self.TPS_nodes and self.shared:
            tps_data = self.shared.node_type[self.current].get("tps_data", {})
            current_garbage = tps_data.get("sampah_kg", 0)
            
            if hasattr(self.shared, 'knowledge_model'):
                self.shared.knowledge_model.discover_garbage(self.current, current_garbage)
            
            self.state = "at_tps"
            print(f"[Vehicle {self.id}] Arrived at TPS {self.current}, found {current_garbage:.2f} kg")
            return True
        return False

    def actuator_load_from_tps(self, amount=None):
        if self.state != "at_tps" or self.current not in self.TPS_nodes:
            return 0
        
        tps_data = self.shared.node_type[self.current].get("tps_data", {})
        available = tps_data.get("sampah_kg", 0)
        
        if amount is None:
            amount = available
        
        loaded = self.actuator_load_garbage(amount)
        tps_data["sampah_kg"] = max(0, available - loaded)
        
        print(f"[Vehicle {self.id}] Loaded {loaded:.2f} kg from TPS {self.current} (remaining: {tps_data['sampah_kg']:.2f} kg)")
        return loaded

    def actuator_arrive_at_tpa(self):
        if isinstance(self.TPA_node, (set, list)):
            is_at_tpa = self.current in self.TPA_node
        else:
            is_at_tpa = self.current == self.TPA_node
        
        if is_at_tpa:
            self.state = "at_tpa"
            print(f"[Vehicle {self.id}] Arrived at TPA {self.current}")
            return True
        return False

    def actuator_unload_to_tpa(self):
        if self.state != "at_tpa":
            print(f"[Vehicle {self.id}] ERROR: Not at TPA (state: {self.state})")
            return 0
        
        if isinstance(self.TPA_node, (set, list)):
            is_at_tpa = self.current in self.TPA_node
        else:
            is_at_tpa = self.current == self.TPA_node
        
        if not is_at_tpa:
            print(f"[Vehicle {self.id}] ERROR: Current node {self.current} is not a TPA!")
            return 0
        
        unloaded = self.actuator_unload_garbage()
        
        if unloaded > 0:
            if self.current in self.shared.node_type:
                tpa_data = self.shared.node_type[self.current].get("tpa_data", {})
                tpa_data["total_sampah"] = tpa_data.get("total_sampah", 0) + unloaded
            
            print(f"[Vehicle {self.id}] ✓ Unloaded {unloaded:.0f}kg to TPA {self.current}")
        
        return unloaded

    def actuator_arrive_at_garage(self):
        if self.current == self.garage_node:
            self.state = "idle"
            print(f"[Vehicle {self.id}] Arrived at garage {self.garage_node}")
            return True
        return False

    def actuator_discover_slowdown(self):
        if not self.target_node or not self.shared:
            return None
        
        edge_id = f"{self.current}-{self.target_node}"
        
        if hasattr(self.shared, 'edge_type') and edge_id in self.shared.edge_type:
            slowdown = self.shared.edge_type[edge_id].get("slowdown", 0)
            
            if slowdown > 0 and hasattr(self.shared, 'knowledge_model'):
                self.shared.knowledge_model.discover_slowdown(edge_id, slowdown)
            
            return slowdown
        
        return None

    def actuator_get_current_location(self):
        return self.current

    def actuator_at_target(self):
        return self.target_node is None or self.progress >= 1.0

    # ============== IF THIS WORKS IT WORKS ==============
    def set_path(self, path):
        if not path or len(path) == 0:
            print(f"[Vehicle {self.id}] Warning: Empty path provided")
            self.path = []
            self.route = []
            self.target_node = None
            self.progress = 0.0
            return
        
        self.path = path
        self.route = path.copy()
        
        if len(path) > 1:
            self.current = path[0]
            self.target_node = path[1]
            self.progress = 0.0
        else:
            self.current = path[0]
            self.target_node = None
            self.progress = 0.0

    def return_to_idle(self):
        old_state = self.state
        self.state = "idle"
        self._update_state_in_garage_stats(old_state)
        print(f"[Vehicle {self.id}] Returned to idle at garage {self.garage_node}")

    def update(self, dt, shared):
        if shared.paused:
            return

        real_speed = self.speed * shared.speed

        if not self.path or self.target_node is None:
            if self.state in ["idle", "at_tps", "at_tpa"]:
                return
            
            neighbors = list(self.G.neighbors(self.current))
            if not neighbors:
                return
            try:
                self.state = "random"
            except:
                pass
            return
        
        if self.target_node not in self.path:
            print(f"[Vehicle {self.id}] ERROR: target_node {self.target_node} not in path! Resetting path.")
            self.path = []
            self.target_node = None
            self.progress = 0.0
            return
        
        edge_data = self.G.get_edge_data(self.current, self.target_node)
        if not edge_data:
            print(f"[Vehicle {self.id}] ERROR: No edge between {self.current} and {self.target_node}! Resetting path.")
            self.path = []
            self.target_node = None
            self.progress = 0.0
            return
        
        length = edge_data[0]['length']

        edge_id = f"{self.current}-{self.target_node}"
        actual_speed = real_speed  # m/s
        
        if shared and hasattr(shared, 'edge_type') and edge_id in shared.edge_type:
            slowdown_value = shared.edge_type[edge_id].get("slowdown", 0)
            if slowdown_value > 0:
                actual_speed = slowdown_value * shared.speed
                
                if hasattr(shared, 'knowledge_model'):
                    shared.knowledge_model.discover_slowdown(edge_id, slowdown_value)
        
        distance = actual_speed * dt
        
        self.progress += distance / length
        
        self.daily_dist += distance / 1000
        self.total_dist += distance / 1000

        if self.progress >= 1.0:
            try:
                idx = self.path.index(self.target_node)
            except ValueError:
                print(f"[Vehicle {self.id}] ERROR: target_node {self.target_node} disappeared from path! Resetting.")
                self.current = self.target_node if self.target_node else self.current
                self.path = []
                self.target_node = None
                self.progress = 0.0
                return
            
            if idx + 1 < len(self.path):
                self.current = self.target_node
                self.target_node = self.path[idx + 1]
                self.progress = 0.0
            else:
                self.current = self.target_node
                self.target_node = None
                self.path = []
                self.progress = 0.0
                
                # ===== Handle arrival at destination =====
                if self.state == "to_garage" and self.current == self.garage_node:
                    self.return_to_idle()
                
                elif self.state == "to_tps" and self.current in self.TPS_nodes:
                    old_state = self.state
                    self.state = "at_tps"
                    if old_state != "at_tps":
                        self._update_state_in_garage_stats(old_state)
                    
                    if hasattr(shared, 'knowledge_model'):
                        tps_data = shared.node_type[self.current].get("tps_data", {})
                        current_garbage = tps_data.get("sampah_kg", 0)
                        shared.knowledge_model.discover_garbage(self.current, current_garbage)
                    
                    print(f"[Vehicle {self.id}] Arrived at TPS {self.current}")
                
                elif self.state == "to_tpa":
                    if isinstance(self.TPA_node, (set, list)):
                        is_at_tpa = self.current in self.TPA_node
                    else:
                        is_at_tpa = self.current == self.TPA_node
                    
                    if is_at_tpa:
                        old_state = self.state
                        self.state = "at_tpa"
                        if old_state != "at_tpa":
                            self._update_state_in_garage_stats(old_state)
                        print(f"[Vehicle {self.id}] Arrived at TPA {self.current}")
                
                else:
                    print(f"[Vehicle {self.id}] Arrived at node {self.current} (state: {self.state})")

    def get_pos(self, pos_dict):
        if self.target_node is None:
            return pos_dict[self.current]
        x1, y1 = pos_dict[self.current]
        x2, y2 = pos_dict[self.target_node]
        x = x1 + (x2 - x1) * self.progress
        y = y1 + (y2 - y1) * self.progress
        return (x, y)