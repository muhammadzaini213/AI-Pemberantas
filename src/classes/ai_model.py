import networkx as nx
from collections import defaultdict
from ..environment import SHIFT_START, SHIFT_END, VEHICLE_SPEED

class AIModel:
    def __init__(self, knowledge_model, shared):
        self.knowledge = knowledge_model
        self.shared = shared

        self.SHIFT_START = SHIFT_START
        self.SHIFT_END = SHIFT_END
        self.OVERTIME_BUFFER = 1

        self.decision_interval = 0.2
        self.last_decision_time = 0

        self.current_phase = "IDLE"
        self.dispatch_done = False

        self.assigned_tasks = {}
        self.tps_assignments = defaultdict(list)

        self.total_trips = 0
        self.total_garbage_collected = 0
        self.reschedule_count = 0

        self._distance_cache = {}
        self._locked_tps = {}

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
        hour = self.shared.sim_hour
        if hour >= self.SHIFT_START and not self.dispatch_done:
            self.phase_dispatch(vehicles)
            self.current_phase = "GATHERING"
            self.dispatch_done = True
            return

        if hour >= self.SHIFT_END - self.OVERTIME_BUFFER:
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

        sorted_tps = sorted(self._calc_tps_priority().items(), key=lambda x: x[1], reverse=True)
        count = 0

        for vehicle in idle_vehicles:
            if not sorted_tps:
                break
            tps_id, priority = sorted_tps.pop(0)
            path = self._safe_path(vehicle.current, tps_id, vehicle.G)
            if path is None:
                continue
            task = {"type": "collect", "tps_id": tps_id, "priority": priority,
                    "assigned_at": f"Day {self.shared.sim_day} {self.shared.sim_hour:02d}:{self.shared.sim_min:02d}"}
            self._assign_task(vehicle, task)
            vehicle.set_path(path)
            vehicle.state = "to_tps"
            count += 1
            print(f"[AIModel] {vehicle.id} -> TPS {tps_id} ({self._path_distance(path, vehicle.G):.0f}m)")
        print(f"[AIModel] Dispatched: {count}/{len(idle_vehicles)}")

    def _calc_tps_priority(self):
        priorities = {}
        for tps_id in self.knowledge.TPS_nodes:
            # sampah yang diketahui atau default
            garbage = self.knowledge.get_discovered_garbage(tps_id) or self.knowledge.known_tps.get(tps_id, {}).get("sampah_per_hari", 0)
            if garbage <= 0:
                continue
            
            # faktor truk yang sudah menuju TPS
            assign_factor = 1.0 / (1 + len(self.tps_assignments[tps_id]))
            
            # faktor lama tidak dilayani
            if tps_id in self.knowledge.discovered_garbage:
                # hitung selisih waktu dalam jam
                last_time = self.knowledge.discovered_garbage[tps_id]["last_check_time"]
                last_day, last_hm = last_time.split(" ")[1], last_time.split(" ")[2]
                last_hour = int(last_hm.split(":")[0]) + int(last_hm.split(":")[1])/60
                last_day = int(last_day)
                
                # total jam sejak terakhir dicek
                hours_since_check = (self.shared.sim_day - last_day) * 24 + (self.shared.sim_hour - last_hour)
                freq_factor = 1 + hours_since_check / 24.0   # bisa skala 1 + hari
            else:
                freq_factor = 2.0  # jika belum pernah dicek
            
            priorities[tps_id] = (garbage / 1000.0) * assign_factor * freq_factor
        
        return priorities


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
                self._preventive_reroute(vehicle)

    def _handle_at_tps(self, vehicle):
        tps_data = self.shared.node_type.get(vehicle.current, {}).get("tps_data", {})
        remaining = tps_data.get("sampah_kg", 0)

        if remaining > 10:
            loaded = vehicle.actuator_load_from_tps()
            if loaded > 0:
                self.total_garbage_collected += loaded

        if vehicle.current in self._locked_tps:
            del self._locked_tps[vehicle.current]

        if vehicle.load >= vehicle.max_load:
            self._route_to_tpa(vehicle)
            return

        hour = self.shared.sim_hour
        if hour >= self.SHIFT_END - self.OVERTIME_BUFFER:
            self._route_to_tpa(vehicle) if vehicle.load > 0 else self._route_to_garage(vehicle)
            return

        next_tps = self._find_next_tps(vehicle)
        if next_tps:
            path = self._safe_path(vehicle.current, next_tps, vehicle.G)
            if path:
                task = {"type": "collect", "tps_id": next_tps,
                        "assigned_at": f"Day {self.shared.sim_day} {hour:02d}:{self.shared.sim_min:02d}"}
                self._assign_task(vehicle, task)
                vehicle.set_path(path)
                vehicle.state = "to_tps"
            else:
                self._route_to_garage(vehicle)
        else:
            self._route_to_tpa(vehicle) if vehicle.load > 0 else self._route_to_garage(vehicle)

    def _handle_at_tpa(self, vehicle):
        if vehicle.load > 0:
            unloaded = vehicle.actuator_unload_to_tpa()
            if unloaded > 0:
                self.total_trips += 1
                print(f"[AIModel] {vehicle.id} unloaded {unloaded:.2f}kg")
        hour = self.shared.sim_hour
        if hour >= self.SHIFT_END - self.OVERTIME_BUFFER:
            self._route_to_garage(vehicle)
            return
        next_tps = self._find_next_tps(vehicle)
        if next_tps:
            path = self._safe_path(vehicle.current, next_tps, vehicle.G)
            if path:
                task = {"type": "collect", "tps_id": next_tps,
                        "assigned_at": f"Day {self.shared.sim_day} {hour:02d}:{self.shared.sim_min:02d}"}
                self._assign_task(vehicle, task)
                vehicle.set_path(path)
                vehicle.state = "to_tps"
            else:
                self._route_to_garage(vehicle)
        else:
            self._route_to_garage(vehicle)

    # ============ FIND NEXT TPS ============
    def _find_next_tps(self, vehicle):
        best_tps, best_score = None, 0
        hour = self.shared.sim_hour
        sorted_tps = sorted(self._calc_tps_priority().items(), key=lambda x: x[1], reverse=True)

        for tps_id, _ in sorted_tps[:10]:
            if tps_id == vehicle.current:
                continue
            # cek TPS locked
            if tps_id in self._locked_tps and self._locked_tps[tps_id] != vehicle.id:
                continue

            garbage = self.knowledge.get_discovered_garbage(tps_id) or self.knowledge.known_tps.get(tps_id, {}).get("sampah_per_hari", 0)
            if garbage <= 10:
                continue

            key = (vehicle.current, tps_id, hour)
            if key in self._distance_cache:
                distance = self._distance_cache[key]
            else:
                path = self._safe_path(vehicle.current, tps_id, vehicle.G)
                distance = float('inf') if path is None else self._path_distance(path, vehicle.G)
                self._distance_cache[key] = distance
            if distance == float('inf'):
                continue

            assignments = len(self.tps_assignments[tps_id])
            score = garbage / (distance + 1) / (1 + assignments)
            if score > best_score:
                best_score, best_tps = score, tps_id

        # lock TPS untuk truk ini
        if best_tps:
            self._locked_tps[best_tps] = vehicle.id

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
        hour = self.shared.sim_hour
        def weight(u, v, d):
            edge_id = f"{u}-{v}"
            length = d.get("length", 1)
            slowdown = self.knowledge.get_slowdown(edge_id, hour=hour)
            if slowdown is not None:
                if slowdown < 5: return float('inf')
                return length * (VEHICLE_SPEED / slowdown)
            return length
        try:
            path = nx.shortest_path(G, start, end, weight=weight)
            for i in range(len(path)-1):
                edge_id = f"{path[i]}-{path[i+1]}"
                if self.knowledge.get_slowdown(edge_id, hour=hour) is not None and self.knowledge.get_slowdown(edge_id, hour=hour) < 5:
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
                task = {"type": "collect", "tps_id": next_tps,
                        "assigned_at": f"Day {self.shared.sim_day} {self.shared.sim_hour:02d}:{self.shared.sim_min:02d}"}
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
            elif vehicle.state == "at_tpa":
                vehicle.actuator_unload_to_tpa()
            if vehicle.load == 0:
                self._route_to_garage(vehicle)
            self.assigned_tasks.pop(vehicle.id, None)

    # ============ ROUTING ============
    def _route_to_tpa(self, vehicle):
        tpa = vehicle.TPA_node
        if isinstance(tpa, (list, set)):
            tpa = list(tpa)[0]
        if vehicle.current == tpa:
            vehicle.state = "at_tpa"
            return True
        path = self._safe_path(vehicle.current, tpa, vehicle.G)
        if path:
            vehicle.set_path(path)
            vehicle.state = "to_tpa"
            return True
        return False

    def _route_to_garage(self, vehicle):
        if vehicle.current == vehicle.garage_node:
            vehicle.state = "idle"
            return True
        path = self._safe_path(vehicle.current, vehicle.garage_node, vehicle.G)
        if path:
            vehicle.set_path(path)
            vehicle.state = "to_garage"
            return True
        return False

    # ============ ASSIGN TASK ============
    def _assign_task(self, vehicle, task):
        self.assigned_tasks[vehicle.id] = task
        if task.get("type") == "collect" and task.get("tps_id"):
            self.tps_assignments[task["tps_id"]].append(vehicle.id)
        self.knowledge.assign_task(vehicle.id, task)

    # ============ PATH UTILITIES ============
    def _path_distance(self, path, G):
        if not path or len(path) < 2:
            return 0
        return sum(G[path[i]][path[i+1]][0]['length'] for i in range(len(path)-1))

    # ============ STATISTICS ============
    def get_statistics(self):
        return {
            "current_phase": self.current_phase,
            "total_trips": self.total_trips,
            "total_garbage_collected": self.total_garbage_collected,
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
