import random
import networkx as nx
from collections import defaultdict

class AIModel:
    """
    AI Controller dengan Matheuristic Rollout untuk dispatch dan scheduling truk sampah.
    
    Matheuristic Rollout Phases:
    ============================================
    1. DISPATCH     - Keluarkan semua truk dari garasi saat shift start
    2. GATHERING    - Kumpulkan sampah dari TPS ke TPA secara optimal
    3. RESCHEDULE   - Handle masalah (slowdown, stuck, full vehicle)
    4. ENDING       - Kembalikan semua truk ke garasi sebelum overtime
    ============================================
    """
    
    def __init__(self, knowledge_model, shared):
        self.knowledge = knowledge_model
        self.shared = shared
        
        # ===== Shift Configuration =====
        self.SHIFT_START = 6   # 06:00 - Shift mulai
        self.SHIFT_END = 22    # 22:00 - Shift selesai
        self.OVERTIME_BUFFER = 2  # 2 jam buffer sebelum overtime
        
        # ===== AI Decision Settings =====
        self.decision_interval = 3.0  # 3 detik per decision cycle
        self.last_decision_time = 0
        
        # ===== Phase Tracking =====
        self.current_phase = "IDLE"  # IDLE, DISPATCH, GATHERING, RESCHEDULE, ENDING
        self.dispatch_done = False
        self.ending_initiated = False
        
        # ===== Task Management =====
        self.assigned_tasks = {}  # vehicle_id -> task_info
        self.tps_assignments = defaultdict(list)  # tps_id -> [vehicle_ids]
        self.tps_priority_scores = {}  # tps_id -> priority_score
        
        # ===== Statistics & Metrics =====
        self.total_trips = 0
        self.total_garbage_collected = 0
        self.reschedule_count = 0
        self.dispatch_count = 0
        self.recall_count = 0
        
        # ===== Rollout History =====
        self.decision_history = []  # Log semua decisions untuk analysis
        
        print("[AIModel] ========================================")
        print("[AIModel] Matheuristic Rollout Controller")
        print("[AIModel] ========================================")
        print(f"[AIModel] Shift: {self.SHIFT_START:02d}:00 - {self.SHIFT_END:02d}:00")
        print(f"[AIModel] Overtime Buffer: {self.OVERTIME_BUFFER}h")
        print(f"[AIModel] Decision Interval: {self.decision_interval}s")
        print("[AIModel] ========================================")
    
    # =====================================================================
    #                    MAIN AI LOOP
    # =====================================================================
    
    def update(self, dt, vehicles):
        """Main AI update loop - dipanggil setiap frame"""
        if self.shared.paused:
            return
        
        # Update decision timer
        self.last_decision_time += dt
        
        # AI makes decisions every interval (untuk efisiensi)
        if self.last_decision_time >= self.decision_interval:
            self.last_decision_time = 0
            self.make_decisions(vehicles)
    
    def make_decisions(self, vehicles):
        """
        Core Matheuristic Rollout Decision Making
        
        Priority order:
        1. ENDING (highest priority - must return before overtime)
        2. DISPATCH (shift start)
        3. GATHERING + RESCHEDULE (continuous operations)
        """
        current_hour = self.shared.sim_hour
        current_time = f"{self.shared.sim_hour:02d}:{self.shared.sim_min:02d}"
        
        # ========== PHASE 4: ENDING (HIGHEST PRIORITY) ==========
        # Jika mendekati shift end, recall semua truk
        if current_hour >= (self.SHIFT_END - self.OVERTIME_BUFFER):
            if not self.ending_initiated:
                self.phase_ending(vehicles)
                self.current_phase = "ENDING"
                self.ending_initiated = True
            else:
                # Continue monitoring ending phase
                self._monitor_ending(vehicles)
            return
        
        # ========== PHASE 1: DISPATCH ==========
        # Dispatch di awal shift
        if current_hour >= self.SHIFT_START and not self.dispatch_done:
            self.phase_dispatch(vehicles)
            self.current_phase = "GATHERING"
            self.dispatch_done = True
            return
        
        # ========== PHASE 2 & 3: GATHERING + RESCHEDULE ==========
        # Operations selama shift berlangsung
        if self.current_phase == "GATHERING":
            self.phase_gathering(vehicles)
            self.phase_reschedule(vehicles)
        
        # Log decision
        self._log_decision(current_time, vehicles)
    
    # =====================================================================
    #                    PHASE 1: DISPATCH
    # =====================================================================
    
    def phase_dispatch(self, vehicles):
        """
        ============= DISPATCH PHASE =============
        Keluarkan semua truk dari garasi secara optimal
        
        Algorithm:
        1. Calculate priority untuk setiap TPS
        2. Sort TPS berdasarkan priority (highest first)
        3. Assign vehicle ke TPS dengan round-robin
        """
        print(f"\n{'='*60}")
        print(f"[AIModel] 🚀 PHASE: DISPATCH")
        print(f"[AIModel] Time: Day {self.shared.sim_day} {self.shared.sim_hour:02d}:{self.shared.sim_min:02d}")
        print(f"{'='*60}")
        
        idle_vehicles = [v for v in vehicles if v.state == "idle" and v.current == v.garage_node]
        
        if not idle_vehicles:
            print("[AIModel] ⚠️ No idle vehicles in garage to dispatch")
            return
        
        print(f"[AIModel] Available vehicles: {len(idle_vehicles)}")
        
        # Calculate TPS priorities menggunakan Rollout Heuristic
        tps_priorities = self._calculate_tps_priorities()
        self.tps_priority_scores = tps_priorities.copy()
        
        # Sort TPS by priority (highest first)
        sorted_tps = sorted(tps_priorities.items(), key=lambda x: x[1], reverse=True)
        
        if not sorted_tps:
            print("[AIModel] ⚠️ No TPS available for dispatch")
            return
        
        print(f"[AIModel] TPS with priority scores:")
        for tps_id, score in sorted_tps[:5]:  # Show top 5
            print(f"[AIModel]   TPS {tps_id}: priority={score:.2f}")
        
        # Dispatch vehicles ke TPS
        dispatched_count = 0
        tps_index = 0
        
        for vehicle in idle_vehicles:
            if tps_index >= len(sorted_tps):
                # Jika lebih banyak vehicle daripada TPS, cycle kembali
                tps_index = 0
            
            tps_id, priority = sorted_tps[tps_index]
            tps_index += 1
            
            # Create collection task
            task = {
                "type": "collect",
                "tps_id": tps_id,
                "priority": priority,
                "assigned_at": f"Day {self.shared.sim_day} {self.shared.sim_hour:02d}:{self.shared.sim_min:02d}",
                "status": "dispatched"
            }
            
            # Assign task
            success = self._dispatch_vehicle_to_tps(vehicle, tps_id, task)
            
            if success:
                dispatched_count += 1
        
        print(f"[AIModel] ✓ Dispatch complete: {dispatched_count}/{len(idle_vehicles)} vehicles")
        print(f"{'='*60}\n")
        
        self.dispatch_count = dispatched_count
    
    def _dispatch_vehicle_to_tps(self, vehicle, tps_id, task):
        """Dispatch single vehicle to TPS"""
        try:
            # Calculate route
            path = nx.shortest_path(vehicle.G, vehicle.current, tps_id, weight="length")
            distance = self.knowledge.get_route_distance(path)
            
            # Set path and state
            vehicle.set_path(path)
            vehicle.state = "to_tps"
            
            # Assign task
            self._assign_task(vehicle, task)
            
            print(f"[AIModel]   ✓ {vehicle.id} → TPS {tps_id} (dist: {distance/1000:.2f}km, priority: {task['priority']:.2f})")
            return True
            
        except Exception as e:
            print(f"[AIModel]   ✗ Failed to dispatch {vehicle.id} to TPS {tps_id}: {e}")
            return False
    
    def _calculate_tps_priorities(self):
        """
        Calculate priority score untuk setiap TPS
        
        Matheuristic Rollout Scoring:
        - Garbage amount (higher = better)
        - Current assignments (lower = better)
        - Discovery status (discovered = more accurate)
        """
        priorities = {}
        
        for tps_id in self.knowledge.TPS_nodes:
            # Get TPS static info
            tps_info = self.knowledge.known_tps.get(tps_id, {})
            sampah_per_hari = tps_info.get("sampah_per_hari", 0)
            
            # Get discovered garbage (lebih akurat)
            discovered_garbage = self.knowledge.get_discovered_garbage(tps_id)
            estimated_garbage = discovered_garbage if discovered_garbage is not None else sampah_per_hari
            
            if estimated_garbage <= 0:
                continue  # Skip TPS tanpa sampah
            
            # Factor 1: Garbage amount (normalized)
            garbage_factor = estimated_garbage / 1000.0  # Normalize to 0-1 scale
            
            # Factor 2: Assignment penalty (hindari over-assignment)
            current_assignments = len(self.tps_assignments[tps_id])
            assignment_factor = 1.0 / (1 + current_assignments * 0.5)
            
            # Factor 3: Discovery bonus (jika sudah discovered, lebih dipercaya)
            discovery_bonus = 1.2 if discovered_garbage is not None else 1.0
            
            # Final priority score
            priority = garbage_factor * assignment_factor * discovery_bonus
            priorities[tps_id] = priority
        
        return priorities
    
    # =====================================================================
    #                    PHASE 2: GATHERING
    # =====================================================================
    
    def phase_gathering(self, vehicles):
        """
        ============= GATHERING PHASE =============
        Manage pengumpulan sampah dari TPS ke TPA
        
        Actions:
        - Vehicle at TPS: Load garbage
        - Vehicle at TPA: Unload garbage
        - Idle vehicle: Find next TPS
        """
        
        for vehicle in vehicles:
            # Skip vehicles in ending phase
            if self.current_phase == "ENDING":
                continue
            
            # Handle berbagai states
            if vehicle.state == "at_tps":
                self._handle_at_tps(vehicle)
            
            elif vehicle.state == "at_tpa":
                self._handle_at_tpa(vehicle)
            
            elif vehicle.state == "idle" and vehicle.current != vehicle.garage_node:
                # Vehicle idle di luar garage - reassign
                self._reassign_vehicle(vehicle)
    
    def _handle_at_tps(self, vehicle):
        """
        Handle vehicle yang tiba di TPS
        
        Decision Tree:
        1. If full -> Go to TPA
        2. Load garbage
        3. If full after load -> Go to TPA
        4. If TPS still has garbage -> Stay
        5. If TPS empty -> Find next TPS or go to TPA/garage
        """
        
        # Check 1: Already full before loading
        if vehicle.actuator_is_full():
            print(f"[AIModel] 🚛 {vehicle.id} already full ({vehicle.load:.0f}kg) - routing to TPA")
            vehicle.actuator_go_to_tpa()
            return
        
        # Action: Load garbage from TPS
        loaded = vehicle.actuator_load_from_tps()
        
        if loaded > 0:
            self.total_garbage_collected += loaded
            print(f"[AIModel] 📦 {vehicle.id} loaded {loaded:.0f}kg at TPS {vehicle.current} (total: {vehicle.load:.0f}kg)")
        
        # Check 2: Full after loading
        if vehicle.actuator_is_full():
            print(f"[AIModel] 🚛 {vehicle.id} is full ({vehicle.load:.0f}kg) - routing to TPA")
            vehicle.actuator_go_to_tpa()
            return
        
        # Check 3: TPS still has significant garbage
        tps_data = self.shared.node_type[vehicle.current].get("tps_data", {})
        remaining = tps_data.get("sampah_kg", 0)
        
        if remaining > 20:  # At least 20kg worth staying
            print(f"[AIModel] 📍 {vehicle.id} staying at TPS {vehicle.current} (remaining: {remaining:.0f}kg)")
            vehicle.state = "at_tps"
            return
        
        # Check 4: Find next optimal TPS
        next_tps = self._find_next_tps(vehicle)
        
        if next_tps:
            print(f"[AIModel] 🗺️ {vehicle.id} moving to next TPS {next_tps}")
            self._goto_tps(vehicle, next_tps)
            return
        
        # No more TPS available
        if vehicle.load > 0:
            # Has load - MUST go to TPA first
            print(f"[AIModel] 🚛 {vehicle.id} has load ({vehicle.load:.0f}kg) - going to TPA")
            vehicle.actuator_go_to_tpa()
        else:
            # Empty and no TPS - return to garage
            print(f"[AIModel] 🏠 {vehicle.id} empty and no TPS - returning to garage")
            vehicle.actuator_go_to_garage()
    
    def _handle_at_tpa(self, vehicle):
        """
        Handle vehicle yang tiba di TPA
        
        Actions:
        1. Unload garbage
        2. Find next TPS or return to garage
        """
        
        # Unload all garbage
        unloaded = vehicle.actuator_unload_to_tpa()
        
        if unloaded > 0:
            self.total_trips += 1
            print(f"[AIModel] 🗑️ {vehicle.id} unloaded {unloaded:.0f}kg at TPA (trips: {self.total_trips})")
        
        # Decide next action
        next_tps = self._find_next_tps(vehicle)
        
        if next_tps and self.current_phase != "ENDING":
            print(f"[AIModel] 🗺️ {vehicle.id} going to next TPS {next_tps}")
            self._goto_tps(vehicle, next_tps)
        else:
            print(f"[AIModel] 🏠 {vehicle.id} returning to garage")
            vehicle.actuator_go_to_garage()
    
    def _find_next_tps(self, vehicle):
        """
        Find next optimal TPS untuk vehicle
        
        Matheuristic Rollout Heuristic:
        - Prioritize TPS dengan sampah banyak
        - Consider distance (closer = better)
        - Avoid over-assigned TPS
        """
        best_tps = None
        best_score = 0
        
        for tps_id in self.knowledge.TPS_nodes:
            # Get garbage estimate
            discovered = self.knowledge.get_discovered_garbage(tps_id)
            if discovered is None:
                tps_info = self.knowledge.known_tps.get(tps_id, {})
                garbage = tps_info.get("sampah_per_hari", 0)
            else:
                garbage = discovered
            
            # Skip if no garbage
            if garbage <= 10:  # Minimum threshold 10kg
                continue
            
            # Calculate distance
            try:
                path = nx.shortest_path(vehicle.G, vehicle.current, tps_id, weight="length")
                distance = self.knowledge.get_route_distance(path)
            except:
                continue
            
            # Skip if too far (max 15km)
            if distance > 15000:
                continue
            
            # Score calculation: garbage / distance ratio
            distance_km = max(distance / 1000.0, 0.1)  # Avoid division by zero
            score = garbage / distance_km
            
            # Penalty for already assigned vehicles
            assignments = len(self.tps_assignments[tps_id])
            score = score / (1 + assignments * 0.3)
            
            if score > best_score:
                best_score = score
                best_tps = tps_id
        
        return best_tps
    
    def _goto_tps(self, vehicle, tps_id):
        """Send vehicle to specific TPS"""
        try:
            path = nx.shortest_path(vehicle.G, vehicle.current, tps_id, weight="length")
            vehicle.set_path(path)
            vehicle.state = "to_tps"
            
            # Update task
            task = {
                "type": "collect",
                "tps_id": tps_id,
                "assigned_at": f"Day {self.shared.sim_day} {self.shared.sim_hour:02d}:{self.shared.sim_min:02d}"
            }
            self._assign_task(vehicle, task)
            return True
        except:
            return False
    
    # =====================================================================
    #                    PHASE 3: RESCHEDULE
    # =====================================================================
    
    def phase_reschedule(self, vehicles):
        """
        ============= RESCHEDULE PHASE =============
        Handle masalah di rute (macet, stuck, dll)
        
        Conditions:
        - Vehicle stuck (state = "random")
        - Vehicle on very slow edge
        - Vehicle taking too long
        """
        
        for vehicle in vehicles:
            # Check 1: Vehicle stuck
            if self._is_vehicle_stuck(vehicle):
                print(f"[AIModel] 🚨 Vehicle {vehicle.id} is STUCK - rescheduling")
                self._reschedule_vehicle(vehicle)
                self.reschedule_count += 1
                continue
            
            # Check 2: Vehicle on slow edge
            if vehicle.target_node:
                edge_id = f"{vehicle.current}-{vehicle.target_node}"
                slowdown = self.knowledge.get_slowdown(edge_id)
                
                if slowdown is not None and slowdown < 5:  # Very slow (< 5 km/h)
                    print(f"[AIModel] ⚠️ Vehicle {vehicle.id} on SLOW edge {edge_id} ({slowdown:.1f}km/h)")
                    self._consider_reroute(vehicle, edge_id, slowdown)
    
    def _is_vehicle_stuck(self, vehicle):
        """Check if vehicle stuck"""
        # Vehicle stuck if in "random" state (shouldn't happen in normal ops)
        return vehicle.state == "random"
    
    def _reschedule_vehicle(self, vehicle):
        """Reschedule stuck vehicle"""
        # Clear current task
        if vehicle.id in self.assigned_tasks:
            old_task = self.assigned_tasks[vehicle.id]
            del self.assigned_tasks[vehicle.id]
            print(f"[AIModel] Cleared stuck task: {old_task}")
        
        # Reset to idle
        vehicle.actuator_idle()
        
        # Reassign
        self._reassign_vehicle(vehicle)
    
    def _consider_reroute(self, vehicle, edge_id, slowdown):
        """Consider rerouting vehicle yang kena macet"""
        # Log untuk analysis
        print(f"[AIModel] 📊 Slowdown logged: {edge_id} = {slowdown:.1f}km/h")
        
        # TODO: Implement A* dengan weight slowdown untuk future enhancement
        # For now, just log and continue
    
    def _reassign_vehicle(self, vehicle):
        """Reassign idle vehicle to new task"""
        
        # CRITICAL: If vehicle has load, MUST go to TPA first!
        if vehicle.load > 0:
            print(f"[AIModel] 🚛 {vehicle.id} has load ({vehicle.load:.0f}kg) - routing to TPA first")
            vehicle.actuator_go_to_tpa()
            return
        
        # Vehicle empty - find best TPS
        next_tps = self._find_next_tps(vehicle)
        
        if next_tps:
            print(f"[AIModel] ♻️ Reassigned {vehicle.id} to TPS {next_tps}")
            self._goto_tps(vehicle, next_tps)
        else:
            # No TPS available - return to garage
            print(f"[AIModel] 🏠 No TPS for {vehicle.id} - returning to garage")
            vehicle.actuator_go_to_garage()
    
    # =====================================================================
    #                    PHASE 4: ENDING
    # =====================================================================
    
    def phase_ending(self, vehicles):
        """
        ============= ENDING PHASE =============
        Recall semua truk ke garasi sebelum overtime
        
        Rules:
        1. Truk dengan load MUST go to TPA first
        2. Truk kosong langsung ke garage
        3. Clear all tasks
        """
        print(f"\n{'='*60}")
        print(f"[AIModel] 🏁 PHASE: ENDING")
        print(f"[AIModel] Time: Day {self.shared.sim_day} {self.shared.sim_hour:02d}:{self.shared.sim_min:02d}")
        print(f"[AIModel] Shift ends at {self.SHIFT_END:02d}:00")
        print(f"{'='*60}")
        
        recalled_count = 0
        
        for vehicle in vehicles:
            # Skip if already going to garage or idle at garage
            if vehicle.state == "to_garage":
                continue
            if vehicle.state == "idle" and vehicle.current == vehicle.garage_node:
                continue
            
            # CRITICAL: Vehicle with load MUST go to TPA first
            if vehicle.load > 0:
                if vehicle.state not in ["to_tpa", "at_tpa"]:
                    print(f"[AIModel] 🚛 {vehicle.id} has load ({vehicle.load:.0f}kg) - routing to TPA")
                    vehicle.actuator_go_to_tpa()
                    recalled_count += 1
                    continue
                
                # If at TPA, unload first
                if vehicle.state == "at_tpa":
                    unloaded = vehicle.actuator_unload_to_tpa()
                    if unloaded > 0:
                        print(f"[AIModel] 🗑️ {vehicle.id} unloaded {unloaded:.0f}kg before return")
            
            # Send to garage (only if empty)
            if vehicle.load == 0 and vehicle.state != "to_garage":
                print(f"[AIModel] 🏠 Recalling {vehicle.id} to garage")
                vehicle.actuator_go_to_garage()
                recalled_count += 1
            
            # Clear task
            if vehicle.id in self.assigned_tasks:
                del self.assigned_tasks[vehicle.id]
        
        print(f"[AIModel] ✓ Ending initiated: {recalled_count} vehicles recalled")
        print(f"{'='*60}\n")
        
        self.recall_count = recalled_count
    
    def _monitor_ending(self, vehicles):
        """Monitor ending phase untuk ensure semua truk kembali"""
        vehicles_at_garage = sum(1 for v in vehicles if v.current == v.garage_node and v.state == "idle")
        vehicles_returning = sum(1 for v in vehicles if v.state == "to_garage")
        vehicles_with_load = sum(1 for v in vehicles if v.load > 0)
        
        if vehicles_with_load > 0:
            # Masih ada truk dengan load - ensure mereka ke TPA dulu
            for vehicle in vehicles:
                if vehicle.load > 0 and vehicle.state not in ["to_tpa", "at_tpa", "to_garage"]:
                    print(f"[AIModel] ⚠️ {vehicle.id} still has load ({vehicle.load:.0f}kg) - forcing to TPA")
                    vehicle.actuator_go_to_tpa()
    
    # =====================================================================
    #                    TASK MANAGEMENT
    # =====================================================================
    
    def _assign_task(self, vehicle, task):
        """Assign task to vehicle dan register di knowledge model"""
        self.assigned_tasks[vehicle.id] = task
        
        # Track TPS assignments
        if task.get("type") == "collect":
            tps_id = task.get("tps_id")
            if tps_id and vehicle.id not in self.tps_assignments[tps_id]:
                self.tps_assignments[tps_id].append(vehicle.id)
        
        # Register in knowledge model
        self.knowledge.assign_task(vehicle.id, task)
    
    def _log_decision(self, current_time, vehicles):
        """Log decision untuk analysis"""
        decision_log = {
            "time": current_time,
            "phase": self.current_phase,
            "active_vehicles": len([v for v in vehicles if v.state != "idle"]),
            "idle_vehicles": len([v for v in vehicles if v.state == "idle"]),
            "total_load": sum(v.load for v in vehicles)
        }
        self.decision_history.append(decision_log)
        
        # Keep only last 100 decisions
        if len(self.decision_history) > 100:
            self.decision_history.pop(0)
    
    # =====================================================================
    #                    STATISTICS & REPORTING
    # =====================================================================
    
    def get_statistics(self):
        """Get comprehensive AI statistics"""
        return {
            "current_phase": self.current_phase,
            "dispatch_done": self.dispatch_done,
            "ending_initiated": self.ending_initiated,
            "total_trips": self.total_trips,
            "total_garbage_collected": self.total_garbage_collected,
            "reschedule_count": self.reschedule_count,
            "dispatch_count": self.dispatch_count,
            "recall_count": self.recall_count,
            "assigned_tasks": len(self.assigned_tasks),
            "tps_with_assignments": len([k for k, v in self.tps_assignments.items() if v])
        }
    
    def print_status_report(self):
        """Print status report untuk monitoring"""
        stats = self.get_statistics()
        print(f"\n{'='*60}")
        print(f"[AIModel] STATUS REPORT - Day {self.shared.sim_day} {self.shared.sim_hour:02d}:{self.shared.sim_min:02d}")
        print(f"{'='*60}")
        print(f"Phase: {stats['current_phase']}")
        print(f"Trips Completed: {stats['total_trips']}")
        print(f"Garbage Collected: {stats['total_garbage_collected']:.0f} kg")
        print(f"Active Tasks: {stats['assigned_tasks']}")
        print(f"Reschedules: {stats['reschedule_count']}")
        print(f"{'='*60}\n")
    
    # =====================================================================
    #                    RESET & MAINTENANCE
    # =====================================================================
    
    def reset_daily(self):
        """Reset daily statistics (called at start of new day)"""
        print(f"\n{'='*60}")
        print(f"[AIModel] 📅 DAILY RESET - Day {self.shared.sim_day}")
        print(f"{'='*60}")
        print(f"Previous day stats:")
        print(f"  Trips: {self.total_trips}")
        print(f"  Garbage: {self.total_garbage_collected:.0f} kg")
        print(f"  Reschedules: {self.reschedule_count}")
        print(f"{'='*60}\n")
        
        # Reset flags
        self.dispatch_done = False
        self.ending_initiated = False
        self.current_phase = "IDLE"
        
        # Clear tasks
        self.assigned_tasks.clear()
        self.tps_assignments.clear()
        self.tps_priority_scores.clear()
        
        # Reset daily counters (keep cumulative for reporting)
        # Note: total_trips dan total_garbage_collected tetap untuk tracking overall