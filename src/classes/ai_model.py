import networkx as nx
from collections import defaultdict
from ..environment import SHIFT_START, SHIFT_END, VEHICLE_CAP

class AIModel:
    def __init__(self, knowledge_model, shared):
        self.knowledge = knowledge_model
        self.shared = shared
        
        self.SHIFT_START = SHIFT_START
        self.SHIFT_END = SHIFT_END
        self.OVERTIME_BUFFER = 1
        
        self.decision_interval = 0.1
        self.last_decision_time = 0
        
        self.current_phase = "IDLE"
        self.dispatch_done = False
        
        self.assigned_tasks = {}
        self.tps_assignments = defaultdict(list)
        
        self.total_trips = 0
        self.total_garbage_collected = 0
        self.reschedule_count = 0
        
        self._distance_cache = {}
        
        self.DISTANCE_WEIGHT = 3.0
        self.GARBAGE_WEIGHT = 1.0
        
        self.STEAL_DISTANCE_RATIO = 0.2
        self.STEAL_MIN_ADVANTAGE = 5000

        print("[AIModel] Initialized")

    # ================== MAIN LOOP ==================
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

    # ================== DISPATCH ==================
    def phase_dispatch(self, vehicles):
        print(f"\n[AIModel] DISPATCH - Hour {self.shared.get_effective_hour():02d}:00")
        
        idle_vehicles = [v for v in vehicles if getattr(v, "state", "").lower() == "idle"]
        if not idle_vehicles:
            return
        
        idle_vehicles.sort(key=lambda v: v.id)
        
        count = 0
        for vehicle in idle_vehicles:
            next_tps = self._find_nearest_unassigned_tps_for_dispatch(vehicle)
            
            if not next_tps:
                print(f"[AIModel] No suitable TPS for {vehicle.id}")
                continue
            
            path = self._safe_path(vehicle.current, next_tps, vehicle.G)
            if path is None:
                print(f"[AIModel] TPS {next_tps} skipped - no safe path")
                continue
            
            my_distance = self._path_distance(path, vehicle.G)
            
            discovered = self.knowledge.get_discovered_garbage(next_tps)
            if discovered is None:
                tps_info = self.knowledge.known_tps.get(next_tps, {})
                garbage = tps_info.get("sampah_per_hari", 0)
                garbage_info = f"~{garbage:.0f}kg (estimated)"
            else:
                garbage = discovered
                garbage_info = f"{garbage:.2f}kg (known)"
            
            task = {
                "type": "collect",
                "tps_id": next_tps,
                "assigned_at": f"Day {self.shared.sim_day} {self.shared.get_effective_hour():02d}:{self.shared.sim_min:02d}"
            }
            
            self._assign_task(vehicle, task)
            
            vehicle.set_path(path)
            vehicle.state = "to_tps"
            count += 1
            
            print(f"[AIModel] ✓ ASSIGNED {vehicle.id} -> TPS {next_tps} (dist={my_distance:.0f}m, garbage={garbage_info})")
        
        print(f"[AIModel] Dispatched: {count}/{len(idle_vehicles)}")

    def _find_nearest_unassigned_tps_for_dispatch(self, vehicle):
        best_tps = None
        best_score = -float('inf')
        current_hour = self.shared.get_effective_hour()
        
        candidates = []

        for tps_id in self.knowledge.TPS_nodes:
            if len(self.tps_assignments[tps_id]) > 0:
                continue
            
            key = (vehicle.current, tps_id, current_hour)
            if key in self._distance_cache:
                my_distance = self._distance_cache[key]
            else:
                path = self._safe_path(vehicle.current, tps_id, vehicle.G)
                if path is None:
                    my_distance = float('inf')
                else:
                    my_distance = self._path_distance(path, vehicle.G)
                self._distance_cache[key] = my_distance
            
            if my_distance == float('inf') or my_distance == 0:
                continue
            
            tps_info = self.knowledge.known_tps.get(tps_id, {})
            base_garbage = tps_info.get("sampah_per_hari", 0)
            discovered = self.knowledge.get_discovered_garbage(tps_id)
            garbage = discovered if discovered is not None else base_garbage
            
            if garbage <= 100:
                continue
            
            distance_score = 10000.0 / (my_distance + 100)
            garbage_score = garbage / 1000.0
            
            score = (
                self.DISTANCE_WEIGHT * 2.0 * distance_score + 
                self.GARBAGE_WEIGHT * garbage_score
            )
            
            candidates.append({
                'tps_id': tps_id,
                'distance': my_distance,
                'garbage': garbage,
                'score': score
            })
            
            if score > best_score:
                best_score = score
                best_tps = tps_id
        
        if candidates:
            candidates.sort(key=lambda x: x['score'], reverse=True)
            print(f"\n[AIModel] {vehicle.id} dispatch candidates (top 3):")
            for i, c in enumerate(candidates[:3]):
                print(f"  {i+1}. TPS {c['tps_id']}: dist={c['distance']:.0f}m, garbage={c['garbage']:.0f}kg, score={c['score']:.3f}")

        return best_tps

    # ================== GATHERING ==================
    def phase_gathering(self, vehicles):
        # Cek dan cancel assignment ke TPS kosong
        self._cancel_invalid_assignments(vehicles)
        
        for vehicle in vehicles:
            state = getattr(vehicle, "state", "").lower()
            
            if state == "at_tps":
                self._handle_at_tps(vehicle)
            elif state == "at_tpa":
                self._handle_at_tpa(vehicle)
            elif state == "idle" and vehicle.current != vehicle.garage_node:
                # Jika exhausted, paksa ke TPA
                if self._all_tps_exhausted():
                    print(f"[AIModel] All TPS exhausted, forcing idle {vehicle.id} to TPA (load: {vehicle.load:.2f}kg)")
                    self._route_to_tpa(vehicle)
                else:
                    self._reassign(vehicle)
    
    def _cancel_invalid_assignments(self, vehicles):
        """Cancel assignments untuk vehicle yang menuju TPS kosong"""
        all_exhausted = self._all_tps_exhausted()
        
        for vehicle in vehicles:
            # Hanya cek vehicle yang sedang menuju TPS
            if vehicle.state != "to_tps":
                continue
            
            # Cek apakah ada assignment
            if vehicle.id not in self.assigned_tasks:
                continue
            
            task = self.assigned_tasks[vehicle.id]
            tps_id = task.get("tps_id")
            
            if not tps_id:
                continue
            
            # Jika semua TPS exhausted, langsung paksa ke TPA
            if all_exhausted:
                print(f"[AIModel] ⚠️ All TPS exhausted, forcing {vehicle.id} to TPA (was heading to TPS {tps_id})")
                self._cancel_assignment(vehicle, tps_id)
                self._route_to_tpa(vehicle)
                continue
            
            # Cek garbage di TPS tujuan
            discovered = self.knowledge.get_discovered_garbage(tps_id)
            
            # Jika TPS sudah diketahui kosong, cancel dan redirect
            if discovered is not None and discovered <= 10:
                print(f"[AIModel] ⚠️ {vehicle.id} heading to EMPTY TPS {tps_id} ({discovered:.2f}kg) - REDIRECTING")
                
                # Cancel assignment
                self._cancel_assignment(vehicle, tps_id)
                
                # Cari TPS lain yang masih ada isinya
                next_tps = self._find_next_tps(vehicle)
                if next_tps:
                    path = self._safe_path(vehicle.current, next_tps, vehicle.G)
                    if path:
                        discovered_new = self.knowledge.get_discovered_garbage(next_tps)
                        if discovered_new is None:
                            tps_info = self.knowledge.known_tps.get(next_tps, {})
                            garbage = tps_info.get("sampah_per_hari", 0)
                            garbage_info = f"~{garbage:.0f}kg (estimated)"
                        else:
                            garbage = discovered_new
                            garbage_info = f"{garbage:.2f}kg (known)"
                        
                        dist = self._path_distance(path, vehicle.G)
                        print(f"[AIModel] ✓ REDIRECTED {vehicle.id} -> TPS {next_tps} (dist={dist:.0f}m, garbage={garbage_info})")
                        
                        new_task = {
                            "type": "collect",
                            "tps_id": next_tps,
                            "assigned_at": f"Day {self.shared.sim_day} {self.shared.get_effective_hour():02d}:{self.shared.sim_min:02d}"
                        }
                        self._assign_task(vehicle, new_task)
                        vehicle.set_path(path)
                        vehicle.state = "to_tps"
                    else:
                        self._route_to_tpa(vehicle)
                else:
                    # Tidak ada TPS lain, ke TPA
                    print(f"[AIModel] No TPS available, forcing {vehicle.id} to TPA")
                    self._route_to_tpa(vehicle)

    def _handle_at_tps(self, vehicle):
        if vehicle.actuator_is_full():
            print(f"[AIModel] {vehicle.id} full - to TPA")
            self._route_to_tpa(vehicle)
            return
        
        current_hour = self.shared.sim_hour
        if current_hour >= (self.SHIFT_END - self.OVERTIME_BUFFER):
            if vehicle.load > VEHICLE_CAP:
                print(f"[AIModel] {vehicle.id} shift ending with load -> TPA")
                self._route_to_tpa(vehicle)
            else:
                print(f"[AIModel] {vehicle.id} shift ending -> garage")
                self._route_to_garage(vehicle)
            return
        
        # Ambil remaining SEBELUM load untuk pengecekan
        tps_data = self.shared.node_type.get(vehicle.current, {}).get("tps_data", {})
        remaining_before = tps_data.get("sampah_kg", 0)
        
        if remaining_before > 10:
            loaded = vehicle.actuator_load_from_tps()
            if loaded > 0:
                self.total_garbage_collected += loaded
                
                # Ambil remaining SETELAH load
                tps_data = self.shared.node_type.get(vehicle.current, {}).get("tps_data", {})
                remaining_after = tps_data.get("sampah_kg", 0)
                
                print(f"[AIModel] {vehicle.id} loaded {loaded:.2f}kg, remaining={remaining_after:.2f}kg")
            
            if vehicle.actuator_is_full():
                print(f"[AIModel] {vehicle.id} full - to TPA")
                self._route_to_tpa(vehicle)
        else:
            current_tps = vehicle.current
            if vehicle.id in self.assigned_tasks:
                task = self.assigned_tasks[vehicle.id]
                if task.get("tps_id") == current_tps:
                    if current_tps in self.tps_assignments:
                        if vehicle.id in self.tps_assignments[current_tps]:
                            self.tps_assignments[current_tps].remove(vehicle.id)
                            print(f"[AIModel] ✗ REMOVED assignment of {vehicle.id} from empty TPS {current_tps} (remaining={remaining_before:.2f}kg)")
            
            # Jika exhausted, langsung ke TPA
            if self._all_tps_exhausted():
                print(f"[AIModel] All TPS exhausted, forcing {vehicle.id} to TPA (load: {vehicle.load:.2f}kg)")
                self._force_to_tpa()
                return

            next_tps = self._find_next_tps(vehicle)
            if next_tps:
                path = self._safe_path(vehicle.current, next_tps, vehicle.G)
                if path:
                    discovered = self.knowledge.get_discovered_garbage(next_tps)
                    if discovered is None:
                        tps_info = self.knowledge.known_tps.get(next_tps, {})
                        garbage = tps_info.get("sampah_per_hari", 0)
                        garbage_info = f"~{garbage:.0f}kg (estimated)"
                    else:
                        garbage = discovered
                        garbage_info = f"{garbage:.2f}kg (known)"
                    
                    dist = self._path_distance(path, vehicle.G)
                    print(f"[AIModel] ASSIGNED {vehicle.id} -> TPS {next_tps} (dist={dist:.0f}m, garbage={garbage_info})")
                    
                    task = {
                        "type": "collect",
                        "tps_id": next_tps,
                        "assigned_at": f"Day {self.shared.sim_day} {self.shared.get_effective_hour():02d}:{self.shared.sim_min:02d}"
                    }
                    self._assign_task(vehicle, task)
                    vehicle.set_path(path)
                    vehicle.state = "to_tps"
                else:
                    print(f"[AIModel] {vehicle.id} no safe path -> TPA")
                    self._route_to_tpa(vehicle)
            else:
                print(f"[AIModel] {vehicle.id} no more TPS available -> TPA")
                self._route_to_tpa(vehicle)

    def _all_tps_exhausted(self):
        for tps_id in self.knowledge.TPS_nodes:
            discovered = self.knowledge.get_discovered_garbage(tps_id)
            
            if discovered is None:
                return False
            
            if discovered > 10:
                return False
        
        return True

    def _handle_at_tpa(self, vehicle):
        if vehicle.load > 0:
            unloaded = vehicle.actuator_unload_to_tpa()
            if unloaded > 0:
                self.total_trips += 1
                print(f"[AIModel] {vehicle.id} unloaded {unloaded:.2f}kg at TPA")
        
        current_hour = self.shared.get_effective_hour()
        if current_hour >= (self.SHIFT_END - self.OVERTIME_BUFFER):
            print(f"[AIModel] {vehicle.id} shift ending -> garage")
            self._route_to_garage(vehicle)
            return
        
        # Jika exhausted, langsung ke garage
        if self._all_tps_exhausted():
            print(f"[AIModel] All TPS exhausted, {vehicle.id} -> garage")
            self._route_to_garage(vehicle)
            return
        
        next_tps = self._find_next_tps(vehicle)
        if next_tps:
            path = self._safe_path(vehicle.current, next_tps, vehicle.G)
            if path:
                discovered = self.knowledge.get_discovered_garbage(next_tps)
                if discovered is None:
                    tps_info = self.knowledge.known_tps.get(next_tps, {})
                    garbage = tps_info.get("sampah_per_hari", 0)
                    garbage_info = f"~{garbage:.0f}kg (estimated)"
                else:
                    garbage = discovered
                    garbage_info = f"{garbage:.2f}kg (known)"
                
                dist = self._path_distance(path, vehicle.G)
                print(f"[AIModel] ✓ ASSIGNED {vehicle.id} -> TPS {next_tps} (dist={dist:.0f}m, garbage={garbage_info})")
                
                task = {"type":"collect","tps_id":next_tps,"assigned_at":f"Day {self.shared.sim_day} {self.shared.get_effective_hour():02d}:{self.shared.sim_min:02d}"}
                self._assign_task(vehicle, task)
                vehicle.set_path(path)
                vehicle.state = "to_tps"
            else:
                print(f"[AIModel] {vehicle.id} no safe path -> garage")
                self._route_to_garage(vehicle)
        else:
            print(f"[AIModel] {vehicle.id} no more TPS -> garage")
            self._route_to_garage(vehicle)

    # ================== FIND NEXT TPS ==================
    def _find_next_tps(self, vehicle):
        if self._all_tps_exhausted():
            return None

        best_tps = None
        best_score = -float('inf')
        current_hour = self.shared.get_effective_hour()
        
        candidates = []

        for tps_id in self.knowledge.TPS_nodes:
            discovered = self.knowledge.get_discovered_garbage(tps_id)
            if discovered is None:
                tps_info = self.knowledge.known_tps.get(tps_id, {})
                garbage = tps_info.get("sampah_per_hari", 0)
            else:
                garbage = discovered
            
            # Skip TPS kosong
            if garbage <= 10:
                if discovered is not None:
                    print(f"[AIModel] 🚫 Skipping TPS {tps_id} - known empty ({garbage:.2f}kg)")
                continue
            
            assigned_vehicles = self.tps_assignments[tps_id]
            
            key = (vehicle.current, tps_id, current_hour)
            if key in self._distance_cache:
                my_distance = self._distance_cache[key]
            else:
                path = self._safe_path(vehicle.current, tps_id, vehicle.G)
                if path is None:
                    my_distance = float('inf')
                else:
                    my_distance = self._path_distance(path, vehicle.G)
                self._distance_cache[key] = my_distance
            
            if my_distance == float('inf') or my_distance == 0:
                continue
            
            can_take = False
            if len(assigned_vehicles) == 0:
                can_take = True
            else:
                for assigned_vid in assigned_vehicles:
                    assigned_vehicle = None
                    for v in self.shared.vehicles:
                        if v.id == assigned_vid or assigned_vid.startswith(v.id):
                            assigned_vehicle = v
                            break
                    
                    if assigned_vehicle is None:
                        can_take = True 
                        break
                    
                    assigned_dist = self._vehicle_distance_to_tps(assigned_vehicle, tps_id)
                    distance_advantage = assigned_dist - my_distance

                    if (my_distance < assigned_dist * self.STEAL_DISTANCE_RATIO and 
                        distance_advantage >= self.STEAL_MIN_ADVANTAGE):
                        
                        print(f"[AIModel] 🔄 {vehicle.id} will STEAL TPS {tps_id} from {assigned_vid}")
                        print(f"         my_dist={my_distance:.0f}m vs their_dist={assigned_dist:.0f}m (advantage={distance_advantage:.0f}m)")
                        can_take = True
                        self._cancel_assignment(assigned_vehicle, tps_id)
                        break
            
            if not can_take:
                continue
            
            distance_score = 10000.0 / (my_distance + 100)
            garbage_score = garbage / 1000.0
            assignment_penalty = 1.0 / (1 + len(self.tps_assignments[tps_id]))
            
            score = (
                self.DISTANCE_WEIGHT * distance_score +
                self.GARBAGE_WEIGHT * garbage_score
            ) * assignment_penalty
            
            candidates.append({
                'tps_id': tps_id,
                'distance': my_distance,
                'garbage': garbage,
                'score': score
            })
            
            if score > best_score:
                best_score = score
                best_tps = tps_id
        
        if candidates:
            candidates.sort(key=lambda x: x['score'], reverse=True)
            print(f"\n[AIModel] {vehicle.id} TPS candidates (top 3):")
            for i, c in enumerate(candidates[:3]):
                discovered = self.knowledge.get_discovered_garbage(c['tps_id'])
                status = "known" if discovered is not None else "estimated"
                print(f"  {i+1}. TPS {c['tps_id']}: dist={c['distance']:.0f}m, garbage={c['garbage']:.0f}kg ({status}), score={c['score']:.3f}")

        return best_tps

    # ================== SAFE PATH ==================
    def _safe_path(self, start, end, G):
        try:
            return nx.shortest_path(G, start, end, weight="length")
        except Exception:
            return None

    def _cancel_assignment(self, vehicle, tps_id):
        """Batalkan assignment TPS dari kendaraan tertentu"""
        if tps_id in self.tps_assignments:
            if vehicle.id in self.tps_assignments[tps_id]:
                self.tps_assignments[tps_id].remove(vehicle.id)
            reserved_id = vehicle.id + "_reserved"
            if reserved_id in self.tps_assignments[tps_id]:
                self.tps_assignments[tps_id].remove(reserved_id)
        
        if vehicle.id in self.assigned_tasks:
            task = self.assigned_tasks[vehicle.id]
            if task.get("tps_id") == tps_id:
                del self.assigned_tasks[vehicle.id]
        
        print(f"[AIModel] ✗ CANCELLED TPS {tps_id} assignment from {vehicle.id}")

    # ================== REASSIGN ==================
    def _reassign(self, vehicle):
        if getattr(vehicle, "load", 0) > 0:
            self._route_to_tpa(vehicle)
            return
        
        next_tps = self._find_next_tps(vehicle)
        
        if next_tps:
            path = self._safe_path(vehicle.current, next_tps, vehicle.G)
            if path:
                discovered = self.knowledge.get_discovered_garbage(next_tps)
                if discovered is None:
                    tps_info = self.knowledge.known_tps.get(next_tps, {})
                    garbage = tps_info.get("sampah_per_hari", 0)
                    garbage_info = f"~{garbage:.0f}kg (estimated)"
                else:
                    garbage = discovered
                    garbage_info = f"{garbage:.2f}kg (known)"
                
                dist = self._path_distance(path, vehicle.G)
                print(f"[AIModel] ✓ REASSIGNED {vehicle.id} -> TPS {next_tps} (dist={dist:.0f}m, garbage={garbage_info})")
                
                task = {"type":"collect","tps_id":next_tps,"assigned_at":f"Day {self.shared.sim_day} {self.shared.get_effective_hour():02d}:{self.shared.sim_min:02d}"}
                self._assign_task(vehicle, task)
                vehicle.set_path(path)
                vehicle.state = "to_tps"
            else:
                self._route_to_garage(vehicle)
        else:
            self._route_to_garage(vehicle)

    # ================== ENDING ==================
    def phase_ending(self, vehicles):
        print(f"\n[AIModel] ENDING - Hour {self.shared.get_effective_hour():02d}:00")
        for vehicle in vehicles:
            if vehicle.state in ["to_garage", "idle"]:
                continue
            
            if vehicle.load > 0 and vehicle.state not in ["to_tpa", "at_tpa"]:
                self._force_to_tpa()
                continue
            
            if vehicle.state == "at_tpa":
                vehicle.actuator_unload_to_tpa()
            
            if vehicle.load == 0:
                self._route_to_garage(vehicle)
            
            if vehicle.id in self.assigned_tasks:
                del self.assigned_tasks[vehicle.id]

    # ================== ROUTING ==================
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
    
    def _force_to_tpa(self):
        for vehicle in self.shared.vehicles:
            self._route_to_tpa(vehicle)
        print("[AIModel] Forcing all vehicle to TPA")

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

    # ================== ASSIGN TASK ==================
    def _assign_task(self, vehicle, task):
        if vehicle.id in self.assigned_tasks:
            old_task = self.assigned_tasks[vehicle.id]
            if old_task.get("type") == "collect":
                old_tps = old_task.get("tps_id")
                if old_tps and old_tps in self.tps_assignments:
                    if vehicle.id in self.tps_assignments[old_tps]:
                        self.tps_assignments[old_tps].remove(vehicle.id)
        
        self.assigned_tasks[vehicle.id] = task
        if task.get("type") == "collect":
            tps_id = task.get("tps_id")
            if tps_id:
                self.tps_assignments[tps_id].append(vehicle.id)
        
        self.knowledge.assign_task(vehicle.id, task)

    # ================== PATH UTILITIES ==================
    def _path_distance(self, path, G):
        if not path or len(path) < 2:
            return 0
        return sum(G[path[i]][path[i+1]][0]['length'] for i in range(len(path)-1))

    def _vehicle_distance_to_tps(self, vehicle, tps_id):
        key = ("veh", vehicle.id, tps_id)
        if key in self._distance_cache:
            return self._distance_cache[key]

        path = self._safe_path(vehicle.current, tps_id, vehicle.G)
        if not path:
            dist = float("inf")
        else:
            dist = self._path_distance(path, vehicle.G)

        self._distance_cache[key] = dist
        return dist

    # ================== STATISTICS ==================
    def get_statistics(self):
        total_garbage = sum(
            data["tpa_data"]["total_sampah"]
            for n, data in self.shared.node_type.items()
            if data["tpa"]
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

    def _edge_id(self, u, v):
        return f"{min(u,v)}-{max(u,v)}"