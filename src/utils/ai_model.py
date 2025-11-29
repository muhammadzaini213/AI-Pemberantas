import random
import networkx as nx
from collections import defaultdict

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
        
        # ===== Shift Configuration =====
        self.SHIFT_START = 6  # 06:00
        self.SHIFT_END = 22   # 22:00
        self.OVERTIME_BUFFER = 1  # 1 hour buffer sebelum overtime
        
        # ===== AI Decision Settings =====
        self.decision_interval = 2.0  # seconds
        self.last_decision_time = 0
        
        # ===== Phase Tracking =====
        self.current_phase = "IDLE"  # IDLE, DISPATCH, GATHERING, RESCHEDULE, ENDING
        self.dispatch_done = False
        
        # ===== Task Management =====
        self.assigned_tasks = {}  # vehicle_id -> task_info
        self.tps_assignments = defaultdict(list)  # tps_id -> [vehicle_ids]
        
        # ===== Statistics =====
        self.total_trips = 0
        self.total_garbage_collected = 0
        self.reschedule_count = 0
        
        print("[AIModel] Initialized with Matheuristic Rollout Controller")
    
    # =====================================================================
    #                    MAIN AI LOOP
    # =====================================================================
    
    def update(self, dt, vehicles):
        """Main AI update loop - dipanggil setiap frame"""
        if self.shared.paused:
            return
        
        # Update decision timer
        self.last_decision_time += dt
        
        # AI makes decisions every interval
        if self.last_decision_time >= self.decision_interval:
            self.last_decision_time = 0
            self.make_decisions(vehicles)
    
    def make_decisions(self, vehicles):
        """Core decision making logic"""
        current_hour = self.shared.sim_hour
        
        # ===== Phase 1: DISPATCH =====
        if current_hour >= self.SHIFT_START and not self.dispatch_done:
            self.phase_dispatch(vehicles)
            self.current_phase = "GATHERING"
            self.dispatch_done = True
            return
        
        # ===== Phase 4: ENDING (Priority) =====
        if current_hour >= (self.SHIFT_END - self.OVERTIME_BUFFER):
            if self.current_phase != "ENDING":
                self.phase_ending(vehicles)
                self.current_phase = "ENDING"
            return
        
        # ===== Phase 2 & 3: GATHERING + RESCHEDULE =====
        if self.current_phase == "GATHERING":
            self.phase_gathering(vehicles)
            self.phase_reschedule(vehicles)
    
    # =====================================================================
    #                    PHASE 1: DISPATCH
    # =====================================================================
    
    def phase_dispatch(self, vehicles):
        """Dispatch semua truk dari garasi ke TPS optimal"""
        print(f"\n{'='*50}")
        print(f"[AIModel] PHASE: DISPATCH - Shift Start at {self.shared.sim_hour:02d}:00")
        print(f"{'='*50}")
        
        idle_vehicles = [v for v in vehicles if v.state == "idle"]
        
        if not idle_vehicles:
            print("[AIModel] No idle vehicles to dispatch")
            return
        
        # Get all TPS with priority scores
        tps_priorities = self._calculate_tps_priorities()
        
        # Sort TPS by priority (highest first)
        sorted_tps = sorted(tps_priorities.items(), key=lambda x: x[1], reverse=True)
        
        dispatched_count = 0
        for vehicle in idle_vehicles:
            if not sorted_tps:
                break
            
            # Assign vehicle to highest priority TPS
            tps_id, priority = sorted_tps.pop(0)
            
            # Create task
            task = {
                "type": "collect",
                "tps_id": tps_id,
                "priority": priority,
                "assigned_at": f"Day {self.shared.sim_day} {self.shared.sim_hour:02d}:{self.shared.sim_min:02d}"
            }
            
            # Assign task
            self._assign_task(vehicle, task)
            
            # Execute: Go to specific TPS
            try:
                path = nx.shortest_path(vehicle.G, vehicle.current, tps_id, weight="length")
                vehicle.set_path(path)
                vehicle.state = "to_tps"
                dispatched_count += 1
                print(f"[AIModel] ✓ Dispatched {vehicle.id} to TPS {tps_id} (priority: {priority:.2f})")
            except:
                print(f"[AIModel] ✗ Failed to dispatch {vehicle.id} to TPS {tps_id}")
        
        print(f"[AIModel] Dispatch complete: {dispatched_count}/{len(idle_vehicles)} vehicles")
    
    def _calculate_tps_priorities(self):
        """Calculate priority score untuk setiap TPS"""
        priorities = {}
        
        for tps_id in self.knowledge.TPS_nodes:
            # Get TPS info
            tps_info = self.knowledge.known_tps.get(tps_id, {})
            sampah_per_hari = tps_info.get("sampah_per_hari", 0)
            
            # Get discovered garbage (if any)
            discovered_garbage = self.knowledge.get_discovered_garbage(tps_id)
            current_garbage = discovered_garbage if discovered_garbage is not None else sampah_per_hari
            
            # Priority factors:
            # 1. Amount of garbage (higher = higher priority)
            # 2. Already assigned vehicles (lower = higher priority)
            garbage_factor = current_garbage / 1000.0  # Normalize
            assignment_factor = 1.0 / (1 + len(self.tps_assignments[tps_id]))
            
            priority = garbage_factor * assignment_factor
            priorities[tps_id] = priority
        
        return priorities
    
    # =====================================================================
    #                    PHASE 2: GATHERING
    # =====================================================================
    
    def phase_gathering(self, vehicles):
        """Manage gathering operations - TPS collection and TPA disposal"""
        
        for vehicle in vehicles:
            # Check if vehicle needs new task
            if vehicle.state == "at_tps":
                self._handle_at_tps(vehicle)
            elif vehicle.state == "at_tpa":
                self._handle_at_tpa(vehicle)
            elif vehicle.state == "idle" and vehicle.current != vehicle.garage_node:
                # Vehicle idle but not at garage - reassign
                self._reassign_vehicle(vehicle)
    
    def _handle_at_tps(self, vehicle):
        """Handle vehicle yang tiba di TPS"""
        # Check if already full - skip loading
        if vehicle.actuator_is_full():
            print(f"[AIModel] Vehicle {vehicle.id} already full ({vehicle.load:.2f} kg) - routing to TPA")
            vehicle.actuator_go_to_tpa()
            return
        
        # Load garbage
        loaded = vehicle.actuator_load_from_tps()
        
        if loaded > 0:
            print(f"[AIModel] Vehicle {vehicle.id} loaded {loaded:.2f} kg at TPS {vehicle.current}")
            self.total_garbage_collected += loaded
        
        # Decide next action after loading
        if vehicle.actuator_is_full():
            # Now full after loading - go to TPA
            print(f"[AIModel] Vehicle {vehicle.id} is full ({vehicle.load:.2f} kg) - routing to TPA")
            vehicle.actuator_go_to_tpa()
        else:
            # Not full - check if more garbage available at this TPS
            tps_data = self.shared.node_type[vehicle.current].get("tps_data", {})
            remaining = tps_data.get("sampah_kg", 0)
            
            if remaining > 10:  # At least 10 kg worth staying
                # More garbage here - stay and load again next cycle
                print(f"[AIModel] Vehicle {vehicle.id} staying at TPS {vehicle.current} (remaining: {remaining:.2f} kg)")
                vehicle.state = "at_tps"
            else:
                # TPS almost empty - find next TPS
                next_tps = self._find_next_tps(vehicle)
                if next_tps:
                    print(f"[AIModel] Vehicle {vehicle.id} moving to next TPS {next_tps}")
                    vehicle.actuator_go_to_location(next_tps)
                    vehicle.state = "to_tps"
                else:
                    # No more TPS available
                    if vehicle.load > 0:
                        # Has load - MUST go to TPA first
                        print(f"[AIModel] Vehicle {vehicle.id} has load ({vehicle.load:.2f} kg) - going to TPA")
                        vehicle.actuator_go_to_tpa()
                    else:
                        # Empty and no TPS - return to garage
                        print(f"[AIModel] Vehicle {vehicle.id} empty and no TPS - returning to garage")
                        vehicle.actuator_go_to_garage()
    
    def _handle_at_tpa(self, vehicle):
        """Handle vehicle yang tiba di TPA"""
        # Unload garbage
        unloaded = vehicle.actuator_unload_to_tpa()
        
        if unloaded > 0:
            print(f"[AIModel] Vehicle {vehicle.id} unloaded {unloaded:.2f} kg at TPA")
            self.total_trips += 1
        
        # Go to next TPS or garage
        next_tps = self._find_next_tps(vehicle)
        if next_tps:
            print(f"[AIModel] Vehicle {vehicle.id} going to next TPS {next_tps}")
            vehicle.actuator_go_to_location(next_tps)
            vehicle.state = "to_tps"
        else:
            print(f"[AIModel] Vehicle {vehicle.id} returning to garage")
            vehicle.actuator_go_to_garage()
    
    def _find_next_tps(self, vehicle):
        """Find next TPS dengan sampah paling banyak yang belum diassign terlalu banyak"""
        best_tps = None
        best_score = 0
        
        for tps_id in self.knowledge.TPS_nodes:
            # Get discovered garbage
            discovered = self.knowledge.get_discovered_garbage(tps_id)
            if discovered is None:
                # Not discovered yet - check sampah_per_hari
                tps_info = self.knowledge.known_tps.get(tps_id, {})
                garbage = tps_info.get("sampah_per_hari", 0)
            else:
                # discovered is a number (sampah_kg)
                garbage = discovered
            
            # Skip if no garbage
            if garbage <= 0:
                continue
            
            # Calculate distance
            path = self.knowledge.get_shortest_path(vehicle.current, tps_id)
            distance = self.knowledge.get_route_distance(path) if path else float('inf')
            
            # Skip if too far
            if distance > 10000:  # 10 km max
                continue
            
            # Score: garbage / distance (higher = better)
            score = garbage / (distance + 1)
            
            # Penalty for already assigned vehicles
            assignments = len(self.tps_assignments[tps_id])
            score = score / (1 + assignments)
            
            if score > best_score:
                best_score = score
                best_tps = tps_id
        
        return best_tps
    
    # =====================================================================
    #                    PHASE 3: RESCHEDULE
    # =====================================================================
    
    def phase_reschedule(self, vehicles):
        """Handle rescheduling karena masalah (slowdown, stuck, dll)"""
        
        for vehicle in vehicles:
            # Check if vehicle stuck (not moving for long time)
            if self._is_vehicle_stuck(vehicle):
                print(f"[AIModel] 🚨 Vehicle {vehicle.id} is stuck - rescheduling")
                self._reschedule_vehicle(vehicle)
                self.reschedule_count += 1
            
            # Check if vehicle on slow edge
            elif vehicle.target_node:
                edge_id = f"{vehicle.current}-{vehicle.target_node}"
                slowdown_value = self.knowledge.get_slowdown(edge_id)
                
                # Check if slowdown exists and is very slow
                if slowdown_value is not None and slowdown_value < 10:  # Very slow (< 10 km/h)
                    print(f"[AIModel] ⚠️ Vehicle {vehicle.id} on slow edge {edge_id} ({slowdown_value} km/h) - considering reroute")
                    self._consider_reroute(vehicle)
    
    def _is_vehicle_stuck(self, vehicle):
        """Check if vehicle stuck (simplified - can be enhanced)"""
        # Vehicle stuck if:
        # - Has path but progress very slow
        # - Or in state "random" (shouldn't happen in normal operation)
        return vehicle.state == "random"
    
    def _reschedule_vehicle(self, vehicle):
        """Reschedule stuck vehicle"""
        # Clear current task
        if vehicle.id in self.assigned_tasks:
            old_task = self.assigned_tasks[vehicle.id]
            del self.assigned_tasks[vehicle.id]
            print(f"[AIModel] Cleared task for {vehicle.id}: {old_task}")
        
        # Reset to idle and reassign
        vehicle.actuator_idle()
        self._reassign_vehicle(vehicle)
    
    def _consider_reroute(self, vehicle):
        """Consider rerouting vehicle to avoid slow edge"""
        # For now, just log - can implement A* with slowdown weights later
        print(f"[AIModel] Reroute consideration for {vehicle.id} logged")
    
    def _reassign_vehicle(self, vehicle):
        """Reassign idle vehicle to new task"""
        # CRITICAL: If vehicle has load, must go to TPA first!
        if vehicle.load > 0:
            print(f"[AIModel] Vehicle {vehicle.id} has load ({vehicle.load:.2f} kg) - sending to TPA before new task")
            vehicle.actuator_go_to_tpa()
            return
        
        # Vehicle is empty - find best TPS
        next_tps = self._find_next_tps(vehicle)
        
        if next_tps:
            task = {
                "type": "collect",
                "tps_id": next_tps,
                "assigned_at": f"Day {self.shared.sim_day} {self.shared.sim_hour:02d}:{self.shared.sim_min:02d}"
            }
            self._assign_task(vehicle, task)
            vehicle.actuator_go_to_location(next_tps)
            vehicle.state = "to_tps"
            print(f"[AIModel] Reassigned {vehicle.id} to TPS {next_tps}")
        else:
            # No TPS available - go to garage
            print(f"[AIModel] No TPS for {vehicle.id} - returning to garage")
            vehicle.actuator_go_to_garage()
    
    # =====================================================================
    #                    PHASE 4: ENDING
    # =====================================================================
    
    def phase_ending(self, vehicles):
        """Return all vehicles to garage before overtime"""
        print(f"\n{'='*50}")
        print(f"[AIModel] PHASE: ENDING - Shift End Approaching at {self.shared.sim_hour:02d}:00")
        print(f"{'='*50}")
        
        for vehicle in vehicles:
            # If not already going to garage or idle
            if vehicle.state != "to_garage" and vehicle.state != "idle":
                
                # CRITICAL: If vehicle has load, must go to TPA first!
                if vehicle.load > 0 and vehicle.state != "to_tpa" and vehicle.state != "at_tpa":
                    print(f"[AIModel] Vehicle {vehicle.id} has load ({vehicle.load:.2f} kg) - routing to TPA before garage")
                    vehicle.actuator_go_to_tpa()
                    continue
                
                # If at TPA, unload first
                if vehicle.state == "at_tpa":
                    vehicle.actuator_unload_to_tpa()
                    print(f"[AIModel] Vehicle {vehicle.id} unloading before return")
                
                # Send to garage only if empty
                if vehicle.load == 0:
                    print(f"[AIModel] Recalling vehicle {vehicle.id} to garage")
                    vehicle.actuator_go_to_garage()
            
            # Clear task
            if vehicle.id in self.assigned_tasks:
                del self.assigned_tasks[vehicle.id]
    
    # =====================================================================
    #                    TASK MANAGEMENT
    # =====================================================================
    
    def _assign_task(self, vehicle, task):
        """Assign task to vehicle"""
        self.assigned_tasks[vehicle.id] = task
        
        # Track TPS assignments
        if task.get("type") == "collect":
            tps_id = task.get("tps_id")
            if tps_id:
                self.tps_assignments[tps_id].append(vehicle.id)
        
        # Register in knowledge model
        self.knowledge.assign_task(vehicle.id, task)
    
    def get_statistics(self):
        """Get AI statistics"""
        return {
            "current_phase": self.current_phase,
            "total_trips": self.total_trips,
            "total_garbage_collected": self.total_garbage_collected,
            "reschedule_count": self.reschedule_count,
            "assigned_tasks": len(self.assigned_tasks),
            "dispatch_done": self.dispatch_done
        }
    
    # =====================================================================
    #                    RESET
    # =====================================================================
    
    def reset_daily(self):
        """Reset daily statistics (called at start of new day)"""
        self.dispatch_done = False
        self.current_phase = "IDLE"
        self.assigned_tasks.clear()
        self.tps_assignments.clear()
        print(f"[AIModel] Daily reset complete for Day {self.shared.sim_day}")