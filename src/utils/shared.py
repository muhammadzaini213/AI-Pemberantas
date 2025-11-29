import json
import os
from ..environment import GRAPH_FILE

class SharedState:
    def __init__(self):
        self.fps = 0
        self.sim_hour = 8
        self.sim_min = 0
        self.sim_day = 1
        self.speed = 1.0
        self.paused = False
        self.simulation_running = False
        
        self.node_state_window = None
        self.edge_state_window = None
        self.tps_state_window = None
        self.tpa_state_window = None
        self.garage_state_window = None
        self.car_state_window = None

        # === TIPE NODE (TPS / TPA / GARAGE) ===
        self.node_type = {}
        self.edge_type = {}
        self.vehicles = []
        self.total_vehicles = 0
        
        # === STATS ===
        self.node_count = 0
        self.edge_count = 0
        self.num_tps = 0
        self.num_tpa = 0
        self.num_garage = 0
        
        # === DYNAMIC PATH FILE DATA ===
        self.data_dir = os.path.join("data", "saved")
        self.graph_base_name = self._extract_graph_name(GRAPH_FILE)
        self.node_data_file = os.path.join(self.data_dir, f"{self.graph_base_name}_node_data.json")
        self.edge_data_file = os.path.join(self.data_dir, f"{self.graph_base_name}_edge_data.json")

    def _extract_graph_name(self, graph_file):
        filename = os.path.basename(graph_file)
        name_without_ext = os.path.splitext(filename)[0]
        return name_without_ext

    def init_node_types(self, G, tps_nodes, tpa_nodes, garage_nodes):
        self.node_type = {
            n: {
                "tps": n in tps_nodes,
                "tpa": n in tpa_nodes,
                "garage": n in garage_nodes,
                "tps_data": {"nama": "", "sampah_kg": 0, "sampah_per_hari": 0,},
                "tpa_data": {"nama": "", "total_sampah": 0},
                "garage_data": {"nama": "Garage", "total_armada": 0, "armada_bertugas": 0, "armada_standby": 0}
            }
            for n in G.nodes()
        }

        print("[SharedState] Attempting to load saved data...")
        self.load_all_data()

    def get_total_vehicles(self):
        total = 0
        for node_id, node_data in self.node_type.items():
            if node_data.get("garage", False):
                garage_data = node_data.get("garage_data", {})
                total += garage_data.get("total_armada", 0)
        return total

    def get_num_vehicle(self):
        return self.get_total_vehicles()

    def on_refresh(self):
        self.validate_time()

        time_tuple, day = self.get_simulation_time()
        hour, minute = time_tuple.split(":")

        self.sim_hour = int(hour)
        self.sim_min = int(minute)
        self.sim_day = int(day)

        s = self.get_simulation_speed()
        self.speed = float(s.replace("x", ""))

        self.paused = self.get_pause_state()

    def reset_vehicles(self):
        print(f"[SharedState] Resetting {len(self.vehicles)} vehicles...")
        
        vehicle_count_before = len(self.vehicles)
        
        for node_id, node_data in self.node_type.items():
            if node_data.get("garage", False):
                garage_data = node_data.get("garage_data", {})
                garage_data["armada_bertugas"] = 0
                garage_data["armada_standby"] = 0
        
        self.vehicles.clear()
        self.total_vehicles = 0
        
        print(f"[SharedState] Vehicles reset: {vehicle_count_before} → {len(self.vehicles)}")
        
        if len(self.vehicles) != 0:
            print("[ERROR] Vehicles list not empty after reset!")
        
        return vehicle_count_before

    # ============== SAVE LOAD ==============    
    def ensure_data_dir(self):
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            print(f"[SharedState] Created data directory: {self.data_dir}")

    def _serialize_node_for_save(self, node_id, node_data):
        return {
            "tps": node_data.get("tps", False),
            "tpa": node_data.get("tpa", False),
            "garage": node_data.get("garage", False),
            "tps_data": node_data.get("tps_data", {}),
            "tpa_data": node_data.get("tpa_data", {}),
            # HANYA simpan total_armada
            "garage_data": {
                "nama": node_data.get("garage_data", {}).get("nama", "Garage"),
                "total_armada": node_data.get("garage_data", {}).get("total_armada", 0)
            }
        }

    def save_node_data(self):
        self.ensure_data_dir()
        
        try:
            serializable_data = {
                str(node_id): self._serialize_node_for_save(node_id, data)
                for node_id, data in self.node_type.items()
            }
            
            with open(self.node_data_file, 'w') as f:
                json.dump(serializable_data, f, indent=2)
            
            print(f"[SharedState] Node data saved to {self.node_data_file}")
            return True
        except Exception as e:
            print(f"[SharedState] Error saving node data: {e}")
            return False

    def save_edge_data(self):
        self.ensure_data_dir()
        
        try:
            with open(self.edge_data_file, 'w') as f:
                json.dump(self.edge_type, f, indent=2)
            
            print(f"[SharedState] Edge data saved to {self.edge_data_file}")
            return True
        except Exception as e:
            print(f"[SharedState] Error saving edge data: {e}")
            return False

    def save_all_data(self):
        node_success = self.save_node_data()
        edge_success = self.save_edge_data()
        
        if node_success and edge_success:
            print("[SharedState] All data saved successfully!")
            return True
        else:
            print("[SharedState] Failed to save some data")
            return False

    def load_node_data(self):
        if not os.path.exists(self.node_data_file):
            print(f"[SharedState] Node data file not found: {self.node_data_file}")
            print(f"[SharedState] Starting with fresh node data")
            return False
        
        try:
            with open(self.node_data_file, 'r') as f:
                loaded_data = json.load(f)
            
            loaded_count = 0
            for node_id_str, data in loaded_data.items():
                try:
                    node_id = int(node_id_str)
                    if node_id in self.node_type:
                        self.node_type[node_id]["tps"] = data.get("tps", False)
                        self.node_type[node_id]["tpa"] = data.get("tpa", False)
                        self.node_type[node_id]["garage"] = data.get("garage", False)
                        
                        if "tps_data" in data:
                            self.node_type[node_id]["tps_data"] = data["tps_data"]
                        
                        if "tpa_data" in data:
                            self.node_type[node_id]["tpa_data"] = data["tpa_data"]
                        
                        if "garage_data" in data:
                            loaded_garage_data = data["garage_data"]
                            self.node_type[node_id]["garage_data"]["nama"] = loaded_garage_data.get("nama", "Garage")
                            self.node_type[node_id]["garage_data"]["total_armada"] = loaded_garage_data.get("total_armada", 0)
                            self.node_type[node_id]["garage_data"]["armada_bertugas"] = 0
                            self.node_type[node_id]["garage_data"]["armada_standby"] = 0
                        
                        loaded_count += 1
                except ValueError:
                    print(f"[SharedState] Warning: Invalid node_id {node_id_str}")
                    continue
            
            print(f"[SharedState] Node data loaded from {self.node_data_file} ({loaded_count} nodes)")
            return True
        except Exception as e:
            print(f"[SharedState] Error loading node data: {e}")
            return False

    def load_edge_data(self):
        if not os.path.exists(self.edge_data_file):
            print(f"[SharedState] Edge data file not found: {self.edge_data_file}")
            print(f"[SharedState] Starting with fresh edge data")
            return False
        
        try:
            with open(self.edge_data_file, 'r') as f:
                self.edge_type = json.load(f)
            
            print(f"[SharedState] Edge data loaded from {self.edge_data_file} ({len(self.edge_type)} edges)")
            return True
        except Exception as e:
            print(f"[SharedState] Error loading edge data: {e}")
            return False

    def load_all_data(self):
        node_success = self.load_node_data()
        edge_success = self.load_edge_data()
        
        if node_success and edge_success:
            print("[SharedState] ✓ All data loaded successfully!")
            return True
        elif node_success or edge_success:
            print("[SharedState] ⚠ Partial data loaded")
            return True
        else:
            print("[SharedState] ℹ No saved data found, using defaults")
            return False

    def auto_save(self):
        return self.save_all_data()