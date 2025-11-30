import networkx as nx
from collections import defaultdict
from ..environment import SHIFT_START, SHIFT_END, VEHICLE_SPEED

class AIModel:
    """
    AI Controller dengan Matheuristic Rollout untuk dispatch dan scheduling truk sampah.

    Phase:
    1. DISPATCH - Keluarkan semua truk dari garasi saat shift start
    2. GATHERING - Kumpulkan sampah dari TPS ke TPA
    3. RESCHEDULE - Handle masalah (slowdown, full vehicle)
    4. ENDING - Kembalikan semua truk ke garasi sebelum overtime
    """

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

        # Historical knowledge about bad edges discovered earlier in the day
        self.historical_bad_edges = set()

        # Track when vehicle was last rerouted to prevent too-frequent rerouting
        self.vehicle_last_reroute_time = {}  # vehicle_id -> sim_time

        print("[AIModel] Initialized with Matheuristic Rollout Controller")

    # -------------------------
    # Main loop
    # -------------------------
    def update(self, dt, vehicles):
        """Main AI update loop - dipanggil setiap frame"""
        if self.shared.paused:
            return

        self.last_decision_time += dt

        if self.last_decision_time >= self.decision_interval:
            self.last_decision_time = 0
            self.make_decisions(vehicles)

    def make_decisions(self, vehicles):
        """Core decision making logic"""
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

    # -------------------------
    # Dispatch
    # -------------------------
    def phase_dispatch(self, vehicles):
        """Dispatch semua truk dari garasi ke TPS optimal"""
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
                    
                    # Calculate path distance
                    path_distance = sum(
                        vehicle.G[path[i]][path[i+1]][0]['length'] 
                        for i in range(len(path)-1)
                    )
                    print(f"[AIModel] ✓ Dispatched {vehicle.id} to TPS {tps_id} (priority: {priority:.2f}, distance: {path_distance:.0f}m)")
            except Exception as e:
                print(f"[AIModel] ✗ Failed to dispatch {vehicle.id} to TPS {tps_id}: {e}")

        print(f"[AIModel] Dispatch complete: {dispatched_count}/{len(idle_vehicles)} vehicles")

    def _calculate_tps_priorities(self):
        """Calculate priority score untuk setiap TPS"""
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

    # -------------------------
    # Gathering
    # -------------------------
    def phase_gathering(self, vehicles):
        """Manage gathering operations - TPS collection and TPA disposal"""

        for vehicle in vehicles:
            st = getattr(vehicle, "state", "").lower()
            if st == "at_tps":
                self._handle_at_tps(vehicle)
            elif st == "at_tpa":
                self._handle_at_tpa(vehicle)
            elif st == "idle" and vehicle.current != vehicle.garage_node:
                self._reassign_vehicle(vehicle)

    def _handle_at_tps(self, vehicle):
        """Handle vehicle yang tiba di TPS"""
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
        """Handle vehicle yang tiba di TPA"""
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
        """Find next TPS dengan sampah paling banyak yang belum diassign terlalu banyak"""
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

    # -------------------------
    # Rescheduling & Reroute (FIXED)
    # -------------------------
    def phase_reschedule(self, vehicles):
        """
        Handle rescheduling karena masalah (slowdown, stuck, dll)
        
        FIXED: Sekarang memeriksa SELURUH path, bukan hanya next edge
        """
        current_sim_time = self.shared.sim_hour * 3600 + self.shared.sim_min * 60

        # Phase 1: Update historical bad edges dari vehicles yang sedang di dalam edge macet
        for vehicle in vehicles:
            if getattr(vehicle, "target_node", None) is not None and getattr(vehicle, "current", None) is not None:
                edge_id = f"{vehicle.current}-{vehicle.target_node}"
                slowdown = self.knowledge.get_slowdown(edge_id)
                progress = getattr(vehicle, "progress", 0.0)
                
                # Vehicle sedang traverse edge yang macet
                if slowdown is not None and progress > 0.0:
                    severe_threshold = max(1.0, VEHICLE_SPEED * 0.5)
                    if slowdown < severe_threshold:
                        if edge_id not in self.historical_bad_edges:
                            self.historical_bad_edges.add(edge_id)
                            print(f"[AIModel] 🚨 Marked historical bad edge: {edge_id} (speed {slowdown:.1f} km/h)")

        # Phase 2: Reroute vehicles yang akan melewati bad edges
        for vehicle in vehicles:
            # Skip stuck vehicles
            if self._is_vehicle_stuck(vehicle):
                print(f"[AIModel] 🚨 Vehicle {vehicle.id} is stuck - rescheduling")
                self._reschedule_vehicle(vehicle)
                self.reschedule_count += 1
                continue

            # Skip vehicles without path
            path = getattr(vehicle, "path", None)
            if not path or len(path) < 2:
                continue

            # Skip vehicles that are idle or at destination
            if getattr(vehicle, "target_node", None) is None:
                continue

            # Get vehicle's current progress
            progress = getattr(vehicle, "progress", 0.0)
            
            # Don't reroute if vehicle is already in the middle of an edge
            if progress > 0.1:  # Allow reroute only at start of edge
                continue

            # Check cooldown: don't reroute too frequently (minimum 30 seconds)
            last_reroute_time = self.vehicle_last_reroute_time.get(vehicle.id, 0)
            if current_sim_time - last_reroute_time < 30:
                continue

            # **CRITICAL FIX**: Check if ANY edge in remaining path is slow
            bad_edges_in_path = self._find_bad_edges_in_path(vehicle, path)
            
            if not bad_edges_in_path:
                continue  # Path is clean

            # Path contains bad edges - attempt reroute
            destination = self._get_vehicle_destination(vehicle)
            
            if not destination:
                continue

            # Build avoid set: all historical bad edges + discovered slow edges
            avoid_edges = set(self.historical_bad_edges)
            
            # Also check for currently known slow edges in the path
            for i in range(len(path) - 1):
                edge_id = f"{path[i]}-{path[i+1]}"
                slowdown = self.knowledge.get_slowdown(edge_id)
                if slowdown is not None:
                    severe_threshold = max(1.0, VEHICLE_SPEED * 0.5)
                    if slowdown < severe_threshold:
                        avoid_edges.add(edge_id)

            # Attempt reroute
            new_path = self._shortest_path_excluding_edges(
                vehicle.G, 
                vehicle.current, 
                destination, 
                avoid_edges
            )

            if new_path and len(new_path) > 1:
                # Verify new path doesn't contain bad edges
                new_bad_edges = self._find_bad_edges_in_path(vehicle, new_path)
                
                if len(new_bad_edges) < len(bad_edges_in_path):  # New path is better
                    # Calculate distances for comparison
                    old_distance = sum(
                        vehicle.G[path[i]][path[i+1]][0]['length'] 
                        for i in range(len(path)-1)
                    )
                    new_distance = sum(
                        vehicle.G[new_path[i]][new_path[i+1]][0]['length'] 
                        for i in range(len(new_path)-1)
                    )
                    
                    # Only reroute if new path isn't too much longer (max 50% longer)
                    if new_distance <= old_distance * 1.5:
                        vehicle.set_path(new_path)
                        self.vehicle_last_reroute_time[vehicle.id] = current_sim_time
                        
                        print(f"[AIModel] ✓ Rerouted {vehicle.id}: avoided {len(bad_edges_in_path)} slow edges")
                        print(f"    Old distance: {old_distance:.0f}m, New distance: {new_distance:.0f}m")
                        print(f"    Avoided edges: {', '.join(bad_edges_in_path)}")
                    else:
                        print(f"[AIModel] ✗ Alternative path for {vehicle.id} too long ({new_distance:.0f}m vs {old_distance:.0f}m)")
                else:
                    print(f"[AIModel] ✗ No better alternative for {vehicle.id} (still has {len(new_bad_edges)} slow edges)")
            else:
                print(f"[AIModel] ✗ No alternative path found for {vehicle.id}")

    def _find_bad_edges_in_path(self, vehicle, path):
        """
        CRITICAL: Find all slow/bad edges in the given path
        Returns list of edge_ids that are slow
        """
        bad_edges = []
        severe_threshold = max(1.0, VEHICLE_SPEED * 0.5)
        
        for i in range(len(path) - 1):
            edge_id = f"{path[i]}-{path[i+1]}"
            
            # Check if edge is in historical bad edges
            if edge_id in self.historical_bad_edges:
                bad_edges.append(edge_id)
                continue
            
            # Check current slowdown value
            slowdown = self.knowledge.get_slowdown(edge_id)
            if slowdown is not None and slowdown < severe_threshold:
                bad_edges.append(edge_id)
        
        return bad_edges

    def _get_vehicle_destination(self, vehicle):
        """
        Determine the vehicle's intended final node for current task.
        """
        # 1) If assigned task present
        task = self.assigned_tasks.get(vehicle.id)
        if task and task.get("type") == "collect":
            return task.get("tps_id")

        # 2) If vehicle.path exists, last element is destination
        p = getattr(vehicle, "path", None)
        if p and len(p) > 0:
            return p[-1]

        # 3) fallback to target_node or garage
        if getattr(vehicle, "target_node", None) is not None:
            return getattr(vehicle, "target_node")

        return vehicle.garage_node

    def _shortest_path_excluding_edges(self, G, source, target, exclude_edges):
        """
        Find shortest path from source to target while excluding edges in exclude_edges.
        exclude_edges: set of strings "u-v"
        Returns path list or None.
        """
        if source == target:
            return [source]

        # Create a copy of graph and remove excluded edges
        G2 = G.copy()
        removed_count = 0
        
        for e in list(exclude_edges):
            try:
                u_str, v_str = e.split("-", 1)
                u = self._maybe_cast_node(u_str)
                v = self._maybe_cast_node(v_str)
            except Exception:
                continue

            # Remove both directions (for undirected behavior)
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

        # Try shortest path on modified graph
        try:
            path = nx.shortest_path(G2, source, target, weight="length")
            return path
        except nx.NetworkXNoPath:
            return None
        except Exception:
            return None

    def _maybe_cast_node(self, s):
        """Try to cast node id strings back to ints if needed"""
        try:
            return int(s)
        except Exception:
            return s

    def _is_vehicle_stuck(self, vehicle):
        """Check if vehicle stuck"""
        return getattr(vehicle, "state", "") == "random"

    def _reschedule_vehicle(self, vehicle):
        """Reschedule stuck vehicle"""
        if vehicle.id in self.assigned_tasks:
            old_task = self.assigned_tasks[vehicle.id]
            del self.assigned_tasks[vehicle.id]
            print(f"[AIModel] Cleared task for {vehicle.id}: {old_task}")

        vehicle.actuator_idle()
        self._reassign_vehicle(vehicle)

    # -------------------------
    # Path helpers
    # -------------------------
    def _path_contains_edge(self, path, edge_id):
        """
        Check if path contains specific edge
        """
        if not path or len(path) < 2:
            return False
        edge_set = { f"{path[i]}-{path[i+1]}" for i in range(len(path)-1) }
        return edge_id in edge_set

    def _get_optimal_path(self, start, end, G, allow_force=False):
        """
        Get optimal path dengan penalti slowdown + historical congestion.
        Jika tidak ada jalur alternatif, fallback ke shortest path normal.
        """

        def edge_weight(u, v, d):
            base_length = d.get('length', 1)
            edge_id = f"{u}-{v}"

            slowdown = self.knowledge.get_slowdown(edge_id)
            penalty = 1.0

            if slowdown is not None and slowdown > 0:
                try:
                    # Inverse speed penalty: slower = higher penalty
                    penalty *= (VEHICLE_SPEED / max(slowdown, 0.1))
                except Exception:
                    penalty *= 5.0

            # Historical bad edge penalty
            if edge_id in self.historical_bad_edges:
                penalty *= 5.0  # Strong penalty

            return base_length * penalty

        try:
            path = nx.shortest_path(G, start, end, weight=edge_weight)
            return path

        except Exception:
            # Fallback: try without penalty
            if allow_force:
                try:
                    path = nx.shortest_path(G, start, end, weight="length")
                    return path
                except Exception:
                    return None

            return self._get_optimal_path(start, end, G, allow_force=True)

    # -------------------------
    # Reassignment + Ending
    # -------------------------
    def _reassign_vehicle(self, vehicle):
        """Reassign idle vehicle to new task"""
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
        """Return all vehicles to garage before overtime"""
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

    # -------------------------
    # Smart Routing Methods (MENGGUNAKAN OPTIMAL PATH)
    # -------------------------
    def _route_to_tpa(self, vehicle):
        """Route vehicle to TPA using optimal path that avoids bad edges"""
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
        
        # Use optimal path that avoids bad edges
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
        print(f"[AIModel] 🚛 Routing {vehicle.id} to TPA {tpa_target} (distance: {path_distance:.0f}m, avoiding {len(self.historical_bad_edges)} known slow edges)")
        return True

    def _route_to_garage(self, vehicle):
        """Route vehicle to garage using optimal path that avoids bad edges"""
        if not vehicle.garage_node:
            print(f"[AIModel] ERROR: No garage for {vehicle.id}!")
            return False
        
        if vehicle.current == vehicle.garage_node:
            vehicle.state = "idle"
            return True
        
        # Use optimal path that avoids bad edges
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
        print(f"[AIModel] 🏠 Routing {vehicle.id} to garage (distance: {path_distance:.0f}m)")
        return True

    def _route_to_location(self, vehicle, target_node, new_state):
        """Route vehicle to any location using optimal path that avoids bad edges"""
        if target_node == vehicle.current:
            vehicle.state = new_state
            return True
        
        # Use optimal path that avoids bad edges
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
        
        # Check if path contains any bad edges
        bad_edges_in_path = self._find_bad_edges_in_path(vehicle, path)
        if bad_edges_in_path:
            print(f"[AIModel] ⚠️ Routing {vehicle.id} to {target_node} (distance: {path_distance:.0f}m) - WARNING: path contains {len(bad_edges_in_path)} slow edges (unavoidable)")
        else:
            print(f"[AIModel] ✓ Routing {vehicle.id} to {target_node} (distance: {path_distance:.0f}m)")
        
        return True

    def _assign_task(self, vehicle, task):
        """Assign task to vehicle"""
        self.assigned_tasks[vehicle.id] = task

        if task.get("type") == "collect":
            tps_id = task.get("tps_id")
            if tps_id:
                self.tps_assignments[tps_id].append(vehicle.id)

        self.knowledge.assign_task(vehicle.id, task)

    # -------------------------
    # Utilities
    # -------------------------
    def get_statistics(self):
        """Get AI statistics"""
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
        """Reset daily statistics (called at start of new day)"""
        self.dispatch_done = False
        self.current_phase = "IDLE"
        self.assigned_tasks.clear()
        self.tps_assignments.clear()
        self.historical_bad_edges.clear()
        self.vehicle_last_reroute_time.clear()
        print(f"[AIModel] Daily reset complete for Day {self.shared.sim_day}")