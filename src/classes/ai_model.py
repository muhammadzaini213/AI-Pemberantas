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

        self.decision_interval = 2.0
        self.last_decision_time = 0

        self.current_phase = "IDLE"
        self.dispatch_done = False

        self.assigned_tasks = {}
        self.tps_assignments = defaultdict(list)

        self.total_trips = 0
        self.total_garbage_collected = 0
        self.reschedule_count = 0

        self.historical_bad_edges = set()
        self.vehicle_last_reroute_time = {}

        # === REROUTE CONTROL ===
        self.MAX_REROUTE_PER_TICK = 3
        self.MIN_REROUTE_INTERVAL = 60

        print("[AIModel] Initialized with Matheuristic Rollout Controller")


    # ==================== MAIN LOOP ====================
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
            self.phase_reschedule(vehicles)

    # ==================== DISPATCH ====================
    def phase_dispatch(self, vehicles):
        print(f"\n{'='*50}")
        print(f"[AIModel] PHASE: DISPATCH - Shift Start at {self.shared.sim_hour:02d}:00")
        print(f"{'='*50}")

        idle_vehicles = [v for v in vehicles if getattr(v, "state", "").lower() == "idle"]

        if not idle_vehicles:
            print("[AIModel] No idle vehicles to dispatch")
            return

        tps_priorities = self._calculate_tps_priorities()

        sorted_tps = sorted(tps_priorities.items(), key=lambda x: x[1], reverse=True)

        dispatched_count = 0
        for vehicle in idle_vehicles:
            if not sorted_tps:
                break

            tps_id, priority = sorted_tps.pop(0)

            task = {
                "type": "collect",
                "tps_id": tps_id,
                "priority": priority,
                "assigned_at": f"Day {self.shared.sim_day} {self.shared.sim_hour:02d}:{self.shared.sim_min:02d}"
            }

            self._assign_task(vehicle, task)

            try:
                path = self._get_optimal_path(vehicle.current, tps_id, vehicle.G)
                if path:
                    vehicle.set_path(path)
                    vehicle.state = "to_tps"
                    dispatched_count += 1
                    
                    path_distance = sum(
                        vehicle.G[path[i]][path[i+1]][0]['length'] 
                        for i in range(len(path)-1)
                    )
                    print(f"[AIModel] Dispatched {vehicle.id} to TPS {tps_id} (priority: {priority:.2f}, distance: {path_distance:.0f}m)")
            except Exception as e:
                print(f"[AIModel] ✗ Failed to dispatch {vehicle.id} to TPS {tps_id}: {e}")

        print(f"[AIModel] Dispatch complete: {dispatched_count}/{len(idle_vehicles)} vehicles")

    def _calculate_tps_priorities(self):
        priorities = {}

        for tps_id in self.knowledge.TPS_nodes:
            tps_info = self.knowledge.known_tps.get(tps_id, {})
            sampah_per_hari = tps_info.get("sampah_per_hari", 0)

            discovered_garbage = self.knowledge.get_discovered_garbage(tps_id)
            current_garbage = discovered_garbage if discovered_garbage is not None else sampah_per_hari

            garbage_factor = current_garbage / 1000.0
            assignment_factor = 1.0 / (1 + len(self.tps_assignments[tps_id]))

            priority = garbage_factor * assignment_factor
            priorities[tps_id] = priority

        return priorities

    # ==================== GATHERING ====================
    def phase_gathering(self, vehicles):

        for vehicle in vehicles:
            st = getattr(vehicle, "state", "").lower()
            if st == "at_tps":
                self._handle_at_tps(vehicle)
            elif st == "at_tpa":
                self._handle_at_tpa(vehicle)
            elif st == "idle" and vehicle.current != vehicle.garage_node:
                self._reassign_vehicle(vehicle)

    def _handle_at_tps(self, vehicle):
        if vehicle.actuator_is_full():
            print(f"[AIModel] Vehicle {vehicle.id} already full ({vehicle.load:.2f} kg) - routing to TPA")
            self._route_to_tpa(vehicle)
            return

        loaded = vehicle.actuator_load_from_tps()

        if loaded > 0:
            print(f"[AIModel] Vehicle {vehicle.id} loaded {loaded:.2f} kg at TPS {vehicle.current}")
            self.total_garbage_collected += loaded

        if vehicle.actuator_is_full():
            print(f"[AIModel] Vehicle {vehicle.id} is full ({vehicle.load:.2f} kg) - routing to TPA")
            self._route_to_tpa(vehicle)
        else:
            tps_data = self.shared.node_type[vehicle.current].get("tps_data", {})
            remaining = tps_data.get("sampah_kg", 0)

            if remaining > 10:
                print(f"[AIModel] Vehicle {vehicle.id} staying at TPS {vehicle.current} (remaining: {remaining:.2f} kg)")
                vehicle.state = "at_tps"
            else:
                next_tps = self._find_next_tps(vehicle)
                if next_tps:
                    print(f"[AIModel] Vehicle {vehicle.id} moving to next TPS {next_tps}")
                    self._route_to_location(vehicle, next_tps, "to_tps")
                else:
                    if vehicle.load > 0:
                        print(f"[AIModel] Vehicle {vehicle.id} has load ({vehicle.load:.2f} kg) - going to TPA")
                        self._route_to_tpa(vehicle)
                    else:
                        print(f"[AIModel] Vehicle {vehicle.id} empty and no TPS - returning to garage")
                        self._route_to_garage(vehicle)

    def _handle_at_tpa(self, vehicle):
        unloaded = vehicle.actuator_unload_to_tpa()

        if unloaded > 0:
            print(f"[AIModel] Vehicle {vehicle.id} unloaded {unloaded:.2f} kg at TPA")
            self.total_trips += 1

        next_tps = self._find_next_tps(vehicle)
        if next_tps:
            print(f"[AIModel] Vehicle {vehicle.id} going to next TPS {next_tps}")
            self._route_to_location(vehicle, next_tps, "to_tps")
        else:
            print(f"[AIModel] Vehicle {vehicle.id} returning to garage")
            self._route_to_garage(vehicle)

    def _find_next_tps(self, vehicle):
        best_tps = None
        best_score = 0

        for tps_id in self.knowledge.TPS_nodes:
            discovered = self.knowledge.get_discovered_garbage(tps_id)
            if discovered is None:
                tps_info = self.knowledge.known_tps.get(tps_id, {})
                garbage = tps_info.get("sampah_per_hari", 0)
            else:
                garbage = discovered

            if garbage <= 0:
                continue

            path = self.knowledge.get_shortest_path(vehicle.current, tps_id)
            distance = self.knowledge.get_route_distance(path) if path else float('inf')

            if distance > 10000:
                continue

            score = garbage / (distance + 1)

            assignments = len(self.tps_assignments[tps_id])
            score = score / (1 + assignments)

            if score > best_score:
                best_score = score
                best_tps = tps_id

        return best_tps

    # =============== RESCHEDULER ===============
    def phase_reschedule(self, vehicles):
        current_sim_time = self.shared.sim_hour * 3600 + self.shared.sim_min * 60

        reroute_candidates = []

        # === DETECT BAD EDGES ON ACTIVE VEHICLES ===
        for vehicle in vehicles:
            if getattr(vehicle, "target_node", None) is None:
                continue

            path = getattr(vehicle, "path", None)
            if not path or len(path) < 2:
                continue

            progress = getattr(vehicle, "progress", 0.0)
            if progress > 0.01:
                continue

            last_reroute_time = self.vehicle_last_reroute_time.get(vehicle.id, 0)
            if current_sim_time - last_reroute_time < self.MIN_REROUTE_INTERVAL:
                continue

            bad_edges = self._find_bad_edges_in_path(vehicle, path)
            if not bad_edges:
                continue

            reroute_candidates.append((vehicle, bad_edges))

        if not reroute_candidates:
            return

        # === PRIORITIZE MOST PROBLEMATIC VEHICLES ===
        reroute_candidates.sort(key=lambda x: len(x[1]), reverse=True)
        reroute_candidates = reroute_candidates[:self.MAX_REROUTE_PER_TICK]

        # === EXECUTE LIMITED REROUTES ===
        for vehicle, bad_edges_in_path in reroute_candidates:
            destination = self._get_vehicle_destination(vehicle)
            if not destination:
                continue

            avoid_edges = set(self.historical_bad_edges)
            avoid_edges.update(bad_edges_in_path)

            new_path = self._shortest_path_excluding_edges(
                vehicle.G,
                vehicle.current,
                destination,
                avoid_edges
            )

            if not new_path or len(new_path) < 2:
                continue

            old_distance = sum(
                vehicle.G[vehicle.path[i]][vehicle.path[i+1]][0]['length']
                for i in range(len(vehicle.path) - 1)
            )
            new_distance = sum(
                vehicle.G[new_path[i]][new_path[i+1]][0]['length']
                for i in range(len(new_path) - 1)
            )

            if new_distance <= old_distance * 1.3:
                vehicle.set_path(new_path)
                self.vehicle_last_reroute_time[vehicle.id] = current_sim_time
                self.reschedule_count += 1

                print(
                    f"[AIModel] Rerouted {vehicle.id} "
                    f"(bad edges: {len(bad_edges_in_path)}, "
                    f"old: {old_distance:.0f}m, new: {new_distance:.0f}m)"
                )


    def _find_bad_edges_in_path(self, vehicle, path):
        bad_edges = []
        severe_threshold = max(1.0, VEHICLE_SPEED * 0.5)

        for i in range(len(path) - 1):
            edge_id = f"{path[i]}-{path[i+1]}"

            if edge_id in self.historical_bad_edges:
                bad_edges.append(edge_id)
                continue

            slowdown = self.knowledge.get_slowdown(edge_id)
            if slowdown is not None and slowdown < severe_threshold:
                bad_edges.append(edge_id)

        return bad_edges


    def _get_vehicle_destination(self, vehicle):
        task = self.assigned_tasks.get(vehicle.id)
        if task and task.get("type") == "collect":
            return task.get("tps_id")

        p = getattr(vehicle, "path", None)
        if p and len(p) > 0:
            return p[-1]

        if getattr(vehicle, "target_node", None) is not None:
            return getattr(vehicle, "target_node")

        return vehicle.garage_node

    def _shortest_path_excluding_edges(self, G, source, target, exclude_edges):
        if source == target:
            return [source]

        G2 = G.copy()
        removed_count = 0
        
        for e in list(exclude_edges):
            try:
                u_str, v_str = e.split("-", 1)
                u = self._maybe_cast_node(u_str)
                v = self._maybe_cast_node(v_str)
            except Exception:
                continue

            if G2.has_edge(u, v):
                try:
                    G2.remove_edge(u, v)
                    removed_count += 1
                except Exception:
                    pass
            if G2.has_edge(v, u):
                try:
                    G2.remove_edge(v, u)
                    removed_count += 1
                except Exception:
                    pass

        try:
            path = nx.shortest_path(G2, source, target, weight="length")
            return path
        except nx.NetworkXNoPath:
            return None
        except Exception:
            return None

    def _maybe_cast_node(self, s):
        try:
            return int(s)
        except Exception:
            return s

    def _is_vehicle_stuck(self, vehicle):
        return getattr(vehicle, "state", "") == "random"

    def _reschedule_vehicle(self, vehicle):
        if vehicle.id in self.assigned_tasks:
            old_task = self.assigned_tasks[vehicle.id]
            del self.assigned_tasks[vehicle.id]
            print(f"[AIModel] Cleared task for {vehicle.id}: {old_task}")

        vehicle.actuator_idle()
        self._reassign_vehicle(vehicle)

    def _path_contains_edge(self, path, edge_id):
        if not path or len(path) < 2:
            return False
        edge_set = { f"{path[i]}-{path[i+1]}" for i in range(len(path)-1) }
        return edge_id in edge_set

    def _get_optimal_path(self, start, end, G, allow_force=False):

        def edge_weight(u, v, d):
            base_length = d.get('length', 1)
            edge_id = f"{u}-{v}"

            slowdown = self.knowledge.get_slowdown(edge_id)
            penalty = 1.0

            if slowdown is not None and slowdown > 0:
                try:
                    penalty *= (VEHICLE_SPEED / max(slowdown, 0.1))
                except Exception:
                    penalty *= 5.0

            if edge_id in self.historical_bad_edges:
                penalty *= 5.0

            return base_length * penalty

        try:
            path = nx.shortest_path(G, start, end, weight=edge_weight)
            return path

        except Exception:
            if allow_force:
                try:
                    path = nx.shortest_path(G, start, end, weight="length")
                    return path
                except Exception:
                    return None

            return self._get_optimal_path(start, end, G, allow_force=True)





    # =============== REASSIGN ===============
    def _reassign_vehicle(self, vehicle):
        if getattr(vehicle, "load", 0) > 0:
            print(f"[AIModel] Vehicle {vehicle.id} has load ({vehicle.load:.2f} kg) - sending to TPA before new task")
            self._route_to_tpa(vehicle)
            return

        next_tps = self._find_next_tps(vehicle)

        if next_tps:
            task = {
                "type": "collect",
                "tps_id": next_tps,
                "assigned_at": f"Day {self.shared.sim_day} {self.shared.sim_hour:02d}:{self.shared.sim_min:02d}"
            }
            self._assign_task(vehicle, task)
            self._route_to_location(vehicle, next_tps, "to_tps")
            print(f"[AIModel] Reassigned {vehicle.id} to TPS {next_tps}")
        else:
            print(f"[AIModel] No TPS for {vehicle.id} - returning to garage")
            self._route_to_garage(vehicle)

    def phase_ending(self, vehicles):
        print(f"\n{'='*50}")
        print(f"[AIModel] PHASE: ENDING - Shift End Approaching at {self.shared.sim_hour:02d}:00")
        print(f"{'='*50}")

        for vehicle in vehicles:
            if vehicle.state != "to_garage" and vehicle.state != "idle":

                if vehicle.load > 0 and vehicle.state != "to_tpa" and vehicle.state != "at_tpa":
                    print(f"[AIModel] Vehicle {vehicle.id} has load ({vehicle.load:.2f} kg) - routing to TPA before garage")
                    self._route_to_tpa(vehicle)
                    continue

                if vehicle.state == "at_tpa":
                    vehicle.actuator_unload_to_tpa()
                    print(f"[AIModel] Vehicle {vehicle.id} unloading before return")

                if vehicle.load == 0:
                    print(f"[AIModel] Recalling vehicle {vehicle.id} to garage")
                    self._route_to_garage(vehicle)

            if vehicle.id in self.assigned_tasks:
                del self.assigned_tasks[vehicle.id]


    # ================ ROUTING METHODS ================
    def _route_to_tpa(self, vehicle):
        if not vehicle.TPA_node:
            print(f"[AIModel] ERROR: No TPA_node configured for {vehicle.id}!")
            return False
        
        if isinstance(vehicle.TPA_node, (set, list)):
            if len(vehicle.TPA_node) == 0:
                print(f"[AIModel] ERROR: TPA_node is empty for {vehicle.id}!")
                return False
            tpa_target = list(vehicle.TPA_node)[0]
        else:
            tpa_target = vehicle.TPA_node
        
        if vehicle.current == tpa_target:
            print(f"[AIModel] Vehicle {vehicle.id} already at TPA {tpa_target}")
            vehicle.state = "at_tpa"
            return True
        
        path = self._get_optimal_path(vehicle.current, tpa_target, vehicle.G)
        
        if not path or len(path) < 2:
            print(f"[AIModel] ERROR: No path to TPA for {vehicle.id}!")
            return False
        
        vehicle.set_path(path)
        vehicle.state = "to_tpa"
        
        path_distance = sum(
            vehicle.G[path[i]][path[i+1]][0]['length'] 
            for i in range(len(path)-1)
        )
        print(f"[AIModel] Routing {vehicle.id} to TPA {tpa_target} (distance: {path_distance:.0f}m, avoiding {len(self.historical_bad_edges)} known slow edges)")
        return True

    def _route_to_garage(self, vehicle):
        if not vehicle.garage_node:
            print(f"[AIModel] ERROR: No garage for {vehicle.id}!")
            return False
        
        if vehicle.current == vehicle.garage_node:
            vehicle.state = "idle"
            return True
        
        path = self._get_optimal_path(vehicle.current, vehicle.garage_node, vehicle.G)
        
        if not path:
            print(f"[AIModel] ERROR: No path to garage for {vehicle.id}!")
            return False
        
        vehicle.set_path(path)
        vehicle.state = "to_garage"
        
        path_distance = sum(
            vehicle.G[path[i]][path[i+1]][0]['length'] 
            for i in range(len(path)-1)
        )
        print(f"[AIModel] Routing {vehicle.id} to garage (distance: {path_distance:.0f}m)")
        return True

    def _route_to_location(self, vehicle, target_node, new_state):
        if target_node == vehicle.current:
            vehicle.state = new_state
            return True
        
        path = self._get_optimal_path(vehicle.current, target_node, vehicle.G)
        
        if not path:
            print(f"[AIModel] ERROR: No path to {target_node} for {vehicle.id}!")
            return False
        
        vehicle.set_path(path)
        vehicle.state = new_state
        
        path_distance = sum(
            vehicle.G[path[i]][path[i+1]][0]['length'] 
            for i in range(len(path)-1)
        )
        
        bad_edges_in_path = self._find_bad_edges_in_path(vehicle, path)
        if bad_edges_in_path:
            print(f"[AIModel] Routing {vehicle.id} to {target_node} (distance: {path_distance:.0f}m) - WARNING: path contains {len(bad_edges_in_path)} slow edges (unavoidable)")
        else:
            print(f"[AIModel] Routing {vehicle.id} to {target_node} (distance: {path_distance:.0f}m)")
        
        return True

    def _assign_task(self, vehicle, task):
        self.assigned_tasks[vehicle.id] = task

        if task.get("type") == "collect":
            tps_id = task.get("tps_id")
            if tps_id:
                self.tps_assignments[tps_id].append(vehicle.id)

        self.knowledge.assign_task(vehicle.id, task)



    # =================== UTILS ===================
    def get_statistics(self):
        return {
            "current_phase": self.current_phase,
            "total_trips": self.total_trips,
            "total_garbage_collected": self.total_garbage_collected,
            "reschedule_count": self.reschedule_count,
            "assigned_tasks": len(self.assigned_tasks),
            "dispatch_done": self.dispatch_done,
            "known_bad_edges": len(self.historical_bad_edges)
        }

    def reset_daily(self):
        self.dispatch_done = False
        self.current_phase = "IDLE"
        self.assigned_tasks.clear()
        self.tps_assignments.clear()
        self.historical_bad_edges.clear()
        self.vehicle_last_reroute_time.clear()
        print(f"[AIModel] Daily reset complete for Day {self.shared.sim_day}")