import networkx as nx
from collections import defaultdict
from ..environment import SHIFT_START, SHIFT_END, VEHICLE_SPEED, VEHICLE_CAP

class AIModel:
    def __init__(self, knowledge_model, shared):
        self.knowledge = knowledge_model
        self.shared = shared
        
        self.SHIFT_START = SHIFT_START
        self.SHIFT_END = SHIFT_END
        self.OVERTIME_BUFFER = 1
        
        self.decision_interval = 1.0
        self.last_decision_time = 0
        
        self.current_phase = "IDLE"
        self.dispatch_done = False
        
        self.assigned_tasks = {}
        self.tps_assignments = defaultdict(list)
        
        self.total_trips = 0
        self.total_garbage_collected = 0
        self.reschedule_count = 0
        
        self._distance_cache = {}
        
        # Weight factors untuk scoring
        self.DISTANCE_WEIGHT = 3.0  # Tingkatkan bobot jarak
        self.GARBAGE_WEIGHT = 1.0
        self.ASSIGNMENT_WEIGHT = 0.5
        
        print("[AIModel] Initialized")

    # ============ MAIN LOOP ============
    def update(self, dt, vehicles):
        if self.shared.paused:
            return
        
        self.last_decision_time += dt
        
        if self.last_decision_time >= self.decision_interval:
            self.last_decision_time = 0
            self.make_decisions(vehicles)
    
    def make_decisions(self, vehicles):
        current_hour = self.shared.sim_hour
        
        if current_hour >= self.SHIFT_START and not self.dispatch_done:
            self.phase_dispatch(vehicles)
            self.current_phase = "GATHERING"
            self.dispatch_done = True
            return
        
        if current_hour >= (self.SHIFT_END - self.OVERTIME_BUFFER):
            if self.current_phase != "ENDING":
                self.phase_ending(vehicles)
                self.current_phase = "ENDING"
            return
        
        if self.current_phase == "GATHERING":
            self.phase_gathering(vehicles)

    # ============ DISPATCH ============
    def phase_dispatch(self, vehicles):
        print(f"\n[AIModel] DISPATCH - Hour {self.shared.sim_hour:02d}:00")
        
        idle_vehicles = [v for v in vehicles if getattr(v, "state", "").lower() == "idle"]
        if not idle_vehicles:
            return
        
        # Sort vehicles by some criteria (optional)
        # idle_vehicles.sort(key=lambda v: v.id)
        
        count = 0
        for vehicle in idle_vehicles:
            # Cari TPS terdekat yang belum diassign untuk vehicle ini
            next_tps = self._find_nearest_unassigned_tps(vehicle)
            
            if not next_tps:
                print(f"[AIModel] No suitable TPS for {vehicle.id}")
                continue
            
            path = self._safe_path(vehicle.current, next_tps, vehicle.G)
            if path is None:
                print(f"[AIModel] TPS {next_tps} skipped - no safe path")
                continue
            
            # Hitung prioritas untuk logging
            priorities = self._calc_tps_priority_for_vehicle(vehicle)
            priority = priorities.get(next_tps, 0)
            
            task = {
                "type": "collect",
                "tps_id": next_tps,
                "priority": priority,
                "assigned_at": f"Day {self.shared.sim_day} {self.shared.sim_hour:02d}:{self.shared.sim_min:02d}"
            }
            
            self._assign_task(vehicle, task)
            
            vehicle.set_path(path)
            vehicle.state = "to_tps"
            count += 1
            
            dist = self._path_distance(path, vehicle.G)
            print(f"[AIModel] {vehicle.id} -> TPS {next_tps} (dist={dist:.0f}m, priority={priority:.3f})")
        
        print(f"[AIModel] Dispatched: {count}/{len(idle_vehicles)}")
    
    def _calc_tps_priority_for_vehicle(self, vehicle):
        """
        Hitung prioritas TPS untuk vehicle tertentu dengan fokus pada jarak
        """
        priorities = {}
        current_hour = self.shared.sim_hour
        
        for tps_id in self.knowledge.TPS_nodes:
            if tps_id == vehicle.current:
                continue
            
            # Skip TPS yang sudah diassign
            if len(self.tps_assignments[tps_id]) > 0:
                continue
            
            # Ambil info sampah
            tps_info = self.knowledge.known_tps.get(tps_id, {})
            base_garbage = tps_info.get("sampah_per_hari", 0)
            discovered = self.knowledge.get_discovered_garbage(tps_id)
            garbage = discovered if discovered is not None else base_garbage
            
            # Skip TPS dengan sampah terlalu sedikit
            if garbage <= 10:
                continue
            
            # Hitung jarak
            key = (vehicle.current, tps_id, current_hour)
            if key in self._distance_cache:
                distance = self._distance_cache[key]
            else:
                path = self._safe_path(vehicle.current, tps_id, vehicle.G)
                if path is None:
                    distance = float('inf')
                else:
                    distance = self._path_distance(path, vehicle.G)
                self._distance_cache[key] = distance
            
            if distance == float('inf') or distance == 0:
                continue
            
            # SCORING BARU: Prioritaskan jarak terdekat
            # Semakin dekat = semakin tinggi score
            distance_score = 10000.0 / (distance + 100)  # Normalisasi dengan denominator
            garbage_score = garbage / 1000.0
            assignment_penalty = 1.0 / (1 + len(self.tps_assignments[tps_id]))
            
            # Kombinasi dengan bobot
            score = (
                self.DISTANCE_WEIGHT * distance_score +
                self.GARBAGE_WEIGHT * garbage_score
            ) * assignment_penalty
            
            priorities[tps_id] = score
        
        return priorities
    
    def _find_nearest_unassigned_tps(self, vehicle):
        """
        Cari TPS terdekat yang belum diassign
        """
        priorities = self._calc_tps_priority_for_vehicle(vehicle)
        
        if not priorities:
            return None
        
        # Sort by priority (highest first)
        sorted_tps = sorted(priorities.items(), key=lambda x: x[1], reverse=True)
        
        # Return TPS dengan priority tertinggi (seharusnya terdekat)
        best_tps = sorted_tps[0][0]
        
        return best_tps

    # ============ GATHERING ============
    def phase_gathering(self, vehicles):
        for vehicle in vehicles:
            state = getattr(vehicle, "state", "").lower()
            
            if state == "at_tps":
                self._handle_at_tps(vehicle)
            elif state == "at_tpa":
                self._handle_at_tpa(vehicle)
            elif state == "idle" and vehicle.current != vehicle.garage_node:
                self._reassign(vehicle)
            else:
                # preventive reroute saat perjalanan
                self._preventive_reroute(vehicle)
    
    def _handle_at_tps(self, vehicle):
        if vehicle.actuator_is_full():
            print(f"[AIModel] {vehicle.id} full - to TPA")
            self._route_to_tpa(vehicle)
            return
        
        current_hour = self.shared.sim_hour
        if current_hour >= (self.SHIFT_END - self.OVERTIME_BUFFER):
            if vehicle.load > VEHICLE_CAP * (1 - 0.1):
                print(f"[AIModel] {vehicle.id} shift ending with load -> TPA")
                self._route_to_tpa(vehicle)
            else:
                print(f"[AIModel] {vehicle.id} shift ending -> garage")
                self._route_to_garage(vehicle)
            return
        
        tps_data = self.shared.node_type.get(vehicle.current, {}).get("tps_data", {})
        remaining = tps_data.get("sampah_kg", 0)
        
        if remaining > 10:
            loaded = vehicle.actuator_load_from_tps()
            if loaded > 0:
                self.total_garbage_collected += loaded
                print(f"[AIModel] {vehicle.id} loaded {loaded:.2f}kg")
            
            if vehicle.actuator_is_full():
                print(f"[AIModel] {vehicle.id} full - to TPA")
                self._route_to_tpa(vehicle)
        else:
            if vehicle.load > VEHICLE_CAP * (1-0.9):
                print(f"[AIModel] {vehicle.id} has {vehicle.load:.2f}kg - to TPA")
                self._route_to_tpa(vehicle)
            else:
                next_tps = self._find_next_tps(vehicle)
                if next_tps:
                    path = self._safe_path(vehicle.current, next_tps, vehicle.G)
                    if path:
                        print(f"[AIModel] {vehicle.id} -> TPS {next_tps}")
                        task = {"type":"collect","tps_id":next_tps,"assigned_at":f"Day {self.shared.sim_day} {self.shared.sim_hour:02d}:{self.shared.sim_min:02d}"}
                        self._assign_task(vehicle, task)
                        vehicle.set_path(path)
                        vehicle.state = "to_tps"
                    else:
                        print(f"[AIModel] {vehicle.id} no safe path -> garage")
                        self._route_to_garage(vehicle)
                else:
                    print(f"[AIModel] {vehicle.id} no TPS -> garage")
                    self._route_to_garage(vehicle)
    
    def _handle_at_tpa(self, vehicle):
        if vehicle.load > 0:
            unloaded = vehicle.actuator_unload_to_tpa()
            if unloaded > 0:
                self.total_trips += 1
                print(f"[AIModel] {vehicle.id} unloaded {unloaded:.2f}kg")
        
        current_hour = self.shared.sim_hour
        if current_hour >= (self.SHIFT_END - self.OVERTIME_BUFFER):
            print(f"[AIModel] {vehicle.id} shift ending -> garage")
            self._route_to_garage(vehicle)
            return
        
        next_tps = self._find_next_tps(vehicle)
        if next_tps:
            path = self._safe_path(vehicle.current, next_tps, vehicle.G)
            if path:
                task = {"type":"collect","tps_id":next_tps,"assigned_at":f"Day {self.shared.sim_day} {self.shared.sim_hour:02d}:{self.shared.sim_min:02d}"}
                self._assign_task(vehicle, task)
                vehicle.set_path(path)
                vehicle.state = "to_tps"
            else:
                self._route_to_garage(vehicle)
        else:
            self._route_to_garage(vehicle)
    
    # ============ FIND NEXT TPS (FIXED) ============
    def _find_next_tps(self, vehicle):
        """
        Cari TPS berikutnya dengan prioritas: JARAK TERDEKAT > Sampah > Assignment
        """
        best_tps = None
        best_score = -float('inf')
        current_hour = self.shared.sim_hour
        
        # Debug: simpan semua kandidat
        candidates = []

        for tps_id in self.knowledge.TPS_nodes:
            if tps_id == vehicle.current:
                continue
            
            # Skip TPS yang sudah diassign ke vehicle lain
            if len(self.tps_assignments[tps_id]) > 0:
                continue
            
            # Ambil info sampah
            discovered = self.knowledge.get_discovered_garbage(tps_id)
            if discovered is None:
                tps_info = self.knowledge.known_tps.get(tps_id, {})
                garbage = tps_info.get("sampah_per_hari", 0)
            else:
                garbage = discovered
            
            if garbage <= 10:
                continue
            
            # Hitung jarak
            key = (vehicle.current, tps_id, current_hour)
            if key in self._distance_cache:
                distance = self._distance_cache[key]
            else:
                path = self._safe_path(vehicle.current, tps_id, vehicle.G)
                if path is None:
                    distance = float('inf')
                else:
                    distance = self._path_distance(path, vehicle.G)
                self._distance_cache[key] = distance
            
            if distance == float('inf') or distance == 0:
                continue
            
            # SCORING: Prioritaskan jarak terdekat
            # Formula: score tinggi untuk jarak dekat
            distance_score = 10000.0 / (distance + 100)  # Semakin dekat = semakin tinggi
            garbage_score = garbage / 1000.0
            assignment_penalty = 1.0 / (1 + len(self.tps_assignments[tps_id]))
            
            # Kombinasi dengan weight yang memprioritaskan jarak
            score = (
                self.DISTANCE_WEIGHT * distance_score +
                self.GARBAGE_WEIGHT * garbage_score
            ) * assignment_penalty
            
            candidates.append({
                'tps_id': tps_id,
                'distance': distance,
                'garbage': garbage,
                'score': score
            })
            
            if score > best_score:
                best_score = score
                best_tps = tps_id
        
        # Debug: print top 3 candidates
        if candidates:
            candidates.sort(key=lambda x: x['score'], reverse=True)
            print(f"\n[AIModel] {vehicle.id} TPS candidates (top 3):")
            for i, c in enumerate(candidates[:3]):
                print(f"  {i+1}. TPS {c['tps_id']}: dist={c['distance']:.0f}m, garbage={c['garbage']:.0f}kg, score={c['score']:.3f}")

        return best_tps

    # ============ PREVENTIVE REROUTE ============
    def _preventive_reroute(self, vehicle):
        if not vehicle.path or len(vehicle.path) < 2:
            return
        
        next_node = vehicle.path[1]
        edge_id = f"{vehicle.current}-{next_node}"
        slowdown = self.knowledge.get_slowdown(edge_id, hour=self.shared.sim_hour)
        
        if slowdown is not None and slowdown < 5:
            new_path = self._safe_path(vehicle.current, vehicle.path[-1], vehicle.G)
            if new_path:
                vehicle.set_path(new_path)
                self.reschedule_count += 1
                print(f"[AIModel] Preventively rerouted {vehicle.id} from slow edge {edge_id}")

    # ============ SAFE PATH ============
    def _safe_path(self, start, end, G):
        current_hour = self.shared.sim_hour
        def weight(u, v, d):
            edge_id = f"{u}-{v}"
            length = d.get("length", 1)
            slowdown = self.knowledge.get_slowdown(edge_id, hour=current_hour)
            if slowdown is not None and slowdown < 5:
                return float("inf")
            elif slowdown is not None and slowdown > 0:
                return length * (VEHICLE_SPEED / slowdown)
            return length
        try:
            path = nx.shortest_path(G, start, end, weight=weight)
            # pastikan semua edge aman
            for i in range(len(path) - 1):
                edge_id = f"{path[i]}-{path[i+1]}"
                slowdown = self.knowledge.get_slowdown(edge_id, hour=current_hour)
                if slowdown is not None and slowdown < 5:
                    return None
            return path
        except:
            return None

    # ============ REASSIGN ============
    def _reassign(self, vehicle):
        if getattr(vehicle, "load", 0) > 0:
            self._route_to_tpa(vehicle)
            return
        
        next_tps = self._find_next_tps(vehicle)
        
        if next_tps:
            path = self._safe_path(vehicle.current, next_tps, vehicle.G)
            if path:
                task = {"type":"collect","tps_id":next_tps,"assigned_at":f"Day {self.shared.sim_day} {self.shared.sim_hour:02d}:{self.shared.sim_min:02d}"}
                self._assign_task(vehicle, task)
                vehicle.set_path(path)
                vehicle.state = "to_tps"
            else:
                self._route_to_garage(vehicle)
        else:
            self._route_to_garage(vehicle)

    # ============ ENDING ============
    def phase_ending(self, vehicles):
        print(f"\n[AIModel] ENDING - Hour {self.shared.sim_hour:02d}:00")
        for vehicle in vehicles:
            if vehicle.state in ["to_garage", "idle"]:
                continue
            
            if vehicle.load > 0 and vehicle.state not in ["to_tpa", "at_tpa"]:
                self._route_to_tpa(vehicle)
                continue
            
            if vehicle.state == "at_tpa":
                vehicle.actuator_unload_to_tpa()
            
            if vehicle.load == 0:
                self._route_to_garage(vehicle)
            
            if vehicle.id in self.assigned_tasks:
                del self.assigned_tasks[vehicle.id]

    # ============ ROUTING ============
    def _route_to_tpa(self, vehicle):
        tpa = vehicle.TPA_node
        if isinstance(tpa, (set, list)):
            tpa = list(tpa)[0]
        
        if vehicle.current == tpa:
            vehicle.state = "at_tpa"
            return True
        
        path = self._safe_path(vehicle.current, tpa, vehicle.G)
        if not path:
            return False
        
        vehicle.set_path(path)
        vehicle.state = "to_tpa"
        return True
    
    def _route_to_garage(self, vehicle):
        if vehicle.current == vehicle.garage_node:
            vehicle.state = "idle"
            return True
        
        path = self._safe_path(vehicle.current, vehicle.garage_node, vehicle.G)
        if not path:
            return False
        
        vehicle.set_path(path)
        vehicle.state = "to_garage"
        return True

    # ============ ASSIGN TASK ============
    def _assign_task(self, vehicle, task):
        self.assigned_tasks[vehicle.id] = task
        if task.get("type") == "collect":
            tps_id = task.get("tps_id")
            if tps_id:
                self.tps_assignments[tps_id].append(vehicle.id)
        self.knowledge.assign_task(vehicle.id, task)

    # ============ PATH UTILITIES ============
    def _path_distance(self, path, G):
        if not path or len(path) < 2:
            return 0
        return sum(G[path[i]][path[i+1]][0]['length'] for i in range(len(path)-1))

    # ============ STATISTICS ============
    def get_statistics(self):
        total_garbage = sum(
            data["tpa_data"]["total_sampah"]
            for n, data in self.node_type.items()
            if data["tpa"]  # hanya node TPA
        )

        return {
            "current_phase": self.current_phase,
            "total_trips": self.total_trips,
            "total_garbage_collected": total_garbage,
            "reschedule_count": self.reschedule_count,
            "assigned_tasks": len(self.assigned_tasks),
            "dispatch_done": self.dispatch_done
        }
        
    def reset_daily(self):
        self.dispatch_done = False
        self.current_phase = "IDLE"
        self.assigned_tasks.clear()
        self.tps_assignments.clear()
        self._distance_cache.clear()
        print(f"[AIModel] Daily reset - Day {self.shared.sim_day}")