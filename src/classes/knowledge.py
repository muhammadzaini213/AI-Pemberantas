import networkx as nx

class KnowledgeModel:
    
    def __init__(self, graph, shared, tps_nodes, tpa_nodes, garage_nodes):
        self.graph = graph
        self.shared = shared
        self.TPS_nodes = tps_nodes
        self.TPA_nodes = tpa_nodes
        self.GARAGE_nodes = garage_nodes
        
        # ===== Known information (statis) =====
        self.known_garages = {node_id: self._get_garage_info(node_id) for node_id in garage_nodes}
        self.known_tps = {node_id: self._get_tps_static_info(node_id) for node_id in tps_nodes}
        self.known_tpa = {node_id: self._get_tpa_info(node_id) for node_id in tpa_nodes}
        

        # ===== Discovered information (dinamis) =====
        self.discovered_slowdowns = {}
        self.discovered_garbage = {}

        
        # ===== Vehicle tracking =====
        self.vehicle_statuses = {}
        self.vehicle_assignments = {}
        self.all_vehicle_ids = set()
        


    # ============== STATIC KNOWLEDGE ==============
    def _get_garage_info(self, garage_id):
        if garage_id in self.shared.node_type:
            garage_data = self.shared.node_type[garage_id].get("garage_data", {})
            return {
                "node_id": garage_id,
                "nama": garage_data.get("nama", "Garage"),
                "total_armada": garage_data.get("total_armada", 0),
                "position": garage_id
            }
        return {}
    
    def _get_tps_static_info(self, tps_id):
        if tps_id in self.shared.node_type:
            tps_data = self.shared.node_type[tps_id].get("tps_data", {})
            return {
                "node_id": tps_id,
                "nama": tps_data.get("nama", ""),
                "sampah_per_hari": tps_data.get("sampah_per_hari", 0),  # Known
                "position": tps_id,
                "dilayanin": tps_data.get("dilayanin", False)
            }
        return {}
    
    def _get_tpa_info(self, tpa_id):
        if tpa_id in self.shared.node_type:
            tpa_data = self.shared.node_type[tpa_id].get("tpa_data", {})
            return {
                "node_id": tpa_id,
                "nama": tpa_data.get("nama", "TPA"),
                "position": tpa_id
            }
        return {}
    
    def get_all_garages(self):
        return self.known_garages
    
    def get_all_tps(self):
        return self.known_tps
    
    def get_all_tpa(self):
        return self.known_tpa
    
    def get_shortest_path(self, start, end):
        try:
            return nx.shortest_path(self.graph, start, end, weight="length")
        except:
            return None
    
    def get_route_distance(self, path):
        if not path or len(path) < 2:
            return 0
        
        total_dist = 0
        for i in range(len(path) - 1):
            edge_data = self.graph.get_edge_data(path[i], path[i+1])
            if edge_data:
                total_dist += edge_data[0].get('length', 0)
        return total_dist
    





    # ============== DISCOVERED/DYNAMIC KNOWLEDGE ==============
    def discover_slowdown(self, edge_id, slowdown_value):
        if edge_id not in self.discovered_slowdowns:
            self.discovered_slowdowns[edge_id] = {
                "slowdown": slowdown_value,
                "discovered_at": f"Day {self.shared.sim_day} {self.shared.sim_hour:02d}:{self.shared.sim_min:02d}",
                "times_encountered": 1
            }
            print(f"[KnowledgeModel] 🚨 DISCOVERED slowdown at {edge_id}: {slowdown_value} km/jam")
        else:
            self.discovered_slowdowns[edge_id]["times_encountered"] += 1
            
            if self.discovered_slowdowns[edge_id]["slowdown"] != slowdown_value:
                old_value = self.discovered_slowdowns[edge_id]["slowdown"]
                self.discovered_slowdowns[edge_id]["slowdown"] = slowdown_value
                self.discovered_slowdowns[edge_id]["updated_at"] = f"Day {self.shared.sim_day} {self.shared.sim_hour:02d}:{self.shared.sim_min:02d}"
                print(f"[KnowledgeModel] ⚠️ UPDATED slowdown at {edge_id}: {old_value} → {slowdown_value} km/jam")
    
    def get_slowdown(self, edge_id):
        if edge_id in self.discovered_slowdowns:
            return self.discovered_slowdowns[edge_id]["slowdown"]
        return None
    
    def get_all_slowdowns(self):
        return self.discovered_slowdowns
    
    def get_slowdown_count(self):
        return len(self.discovered_slowdowns)
    
    def discover_garbage(self, tps_id, sampah_kg, sim_time=None):
        current_time = f"Day {self.shared.sim_day} {self.shared.sim_hour:02d}:{self.shared.sim_min:02d}" if sim_time is None else sim_time
        
        if tps_id not in self.discovered_garbage:
            self.discovered_garbage[tps_id] = {
                "sampah_kg": sampah_kg,
                "last_check_time": current_time,
                "history": [sampah_kg]
            }
            print(f"[KnowledgeModel] DISCOVERED garbage at TPS {tps_id}: {sampah_kg:.2f} kg (at {current_time})")
        else:
            old_amount = self.discovered_garbage[tps_id]["sampah_kg"]
            self.discovered_garbage[tps_id]["sampah_kg"] = sampah_kg
            self.discovered_garbage[tps_id]["last_check_time"] = current_time
            self.discovered_garbage[tps_id]["history"].append(sampah_kg)
            print(f"[KnowledgeModel] UPDATED garbage at TPS {tps_id}: {sampah_kg:.2f} kg (was {old_amount:.2f} at {current_time})")
    
    def get_discovered_garbage(self, tps_id):
        if tps_id in self.discovered_garbage:
            return self.discovered_garbage[tps_id]["sampah_kg"]
        return None
    
    def get_garbage_history(self, tps_id):
        if tps_id in self.discovered_garbage:
            return self.discovered_garbage[tps_id]["history"]
        return []
    




    # ============== VEHICLE TRACKER ==============
    def update_vehicle_status(self, vehicle_id, status):
        self.all_vehicle_ids.add(vehicle_id)
        self.vehicle_statuses[vehicle_id] = {
            "status": status,
            "location": status.get("current_node"),
            "load": status.get("load", 0),
            "load_percentage": status.get("load_percentage", 0),
            "state": status.get("state"),
            "timestamp": f"Day {self.shared.sim_day} {self.shared.sim_hour:02d}:{self.shared.sim_min:02d}"
        }
    
    def get_vehicle_status(self, vehicle_id):
        return self.vehicle_statuses.get(vehicle_id, None)
    
    def assign_task(self, vehicle_id, task):
        self.vehicle_assignments[vehicle_id] = task
        print(f"[KnowledgeModel] ASSIGNED task to vehicle {vehicle_id}: {task}")
    
    def get_task(self, vehicle_id):
        return self.vehicle_assignments.get(vehicle_id, None)
    
    def clear_task(self, vehicle_id):
        if vehicle_id in self.vehicle_assignments:
            del self.vehicle_assignments[vehicle_id]
    


    # ============== AGENT QUERIES (SENSOR) ==============    
    def get_optimal_tps(self, current_pos, prefer_known=False):
        best_tps = None
        best_distance = float('inf')
        
        if prefer_known and self.discovered_garbage:
            for tps_id in self.discovered_garbage.keys():
                if tps_id in self.known_tps:
                    dist = self.get_route_distance(
                        self.get_shortest_path(current_pos, tps_id)
                    )
                    if dist < best_distance:
                        best_distance = dist
                        best_tps = tps_id
        
        if best_tps is None:
            for tps_id in self.TPS_nodes:
                dist = self.get_route_distance(
                    self.get_shortest_path(current_pos, tps_id)
                )
                if dist < best_distance:
                    best_distance = dist
                    best_tps = tps_id
        
        return best_tps

    def get_vehicles_by_state(self, state):
        return [
            vid for vid, status in self.vehicle_statuses.items()
            if status.get("state") == state
        ]

    def get_knowledge_summary(self):
        total_encounters = sum(
            data["times_encountered"] 
            for data in self.discovered_slowdowns.values()
        )
        
        return {
            "known_garages": len(self.known_garages),
            "known_tps": len(self.known_tps),
            "known_tpa": len(self.known_tpa),
            "discovered_slowdowns": len(self.discovered_slowdowns),
            "total_slowdown_encounters": total_encounters,
            "discovered_garbage": len(self.discovered_garbage),
            "active_vehicles": len(self.all_vehicle_ids),
            "vehicles_with_task": len(self.vehicle_assignments),
            "idle_vehicles": len(self.get_vehicles_by_state("idle")),
            "busy_vehicles": len(self.all_vehicle_ids) - len(self.get_vehicles_by_state("idle"))
        }