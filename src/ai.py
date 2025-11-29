"""
AI Controller - DECISION MAKER
Membuat keputusan berdasarkan KnowledgeModel dan mengirim command ke Vehicle.
"""

import networkx as nx


class AIController:
    """
    AI CONTROLLER - Pengambil keputusan.
    
    Menggunakan KnowledgeModel untuk membuat keputusan dan mengirim command ke Vehicle.
    
    Strategy:
    1. Shift management: Truk keluar dari garage saat shift start, kembali saat shift end
    2. Task assignment: Assign truk idle ke TPS berdasarkan prioritas
    3. Load management: Truk penuh harus ke TPA
    4. Traffic handling: Hindari route macet (future enhancement)
    """
    
    def __init__(self, knowledge_model, vehicles, shift_start=6, shift_end=22):
        self.knowledge = knowledge_model
        self.vehicles = {v.id: v for v in vehicles}
        
        self.shift_start = shift_start
        self.shift_end = shift_end
        
        # Strategy parameters
        self.priority_threshold = 0.3  # Minimum priority untuk assign task
        self.full_threshold = 0.9  # 90% capacity = full
        
        # Statistics
        self.decisions_made = 0
        self.tasks_assigned = 0
    
    def make_decisions(self, current_time):
        """
        Buat keputusan untuk semua truk berdasarkan state saat ini.
        Dipanggil setiap interval waktu tertentu (misal: setiap 2 detik).
        
        Returns:
            List of (vehicle_id, command) tuples
        """
        commands = []
        
        hour = current_time % 24
        
        # ===== 1. CHECK SHIFT =====
        is_working_hours = self.shift_start <= hour < self.shift_end
        
        if not is_working_hours:
            # Di luar jam kerja, semua truk ke garasi
            commands.extend(self._send_all_to_garage())
            self.decisions_made += len(commands)
            return commands
        
        # ===== 2. DALAM JAM KERJA: MANAGE FLEET =====
        all_status = self.knowledge.get_all_vehicle_status()
        
        # 2a. Truk penuh harus ke TPA (highest priority)
        commands.extend(self._send_full_vehicles_to_tpa(all_status))
        
        # 2b. Truk kosong idle -> assign ke TPS
        commands.extend(self._assign_empty_vehicles_to_tps(all_status, current_time))
        
        # 2c. Handle stuck vehicles (future: rerouting)
        # commands.extend(self._handle_stuck_vehicles(all_status))
        
        self.decisions_made += len(commands)
        return commands
    
    def _send_all_to_garage(self):
        """Kirim semua truk idle ke garasi"""
        commands = []
        all_status = self.knowledge.get_all_vehicle_status()
        
        for vehicle_id, status in all_status.items():
            if status["state"] == "Idle" and status["current_node"] != self.knowledge.garage_node:
                command = {
                    "action": "move_to",
                    "target": self.knowledge.garage_node
                }
                commands.append((vehicle_id, command))
        
        return commands
    
    def _send_full_vehicles_to_tpa(self, all_status):
        """Kirim truk yang penuh ke TPA"""
        commands = []
        
        for vehicle_id, status in all_status.items():
            # Cek: Idle, penuh, dan belum di TPA
            is_full = status["current_load"] >= status["capacity"] * self.full_threshold
            is_idle = status["state"] == "Idle"
            not_at_tpa = status["current_node"] != self.knowledge.TPA_node
            
            if is_full and is_idle and not_at_tpa:
                command = {
                    "action": "move_to",
                    "target": self.knowledge.TPA_node
                }
                commands.append((vehicle_id, command))
        
        return commands
    
    def _assign_empty_vehicles_to_tps(self, all_status, current_time):
        """Assign truk kosong idle ke TPS berdasarkan prioritas"""
        commands = []
        
        # 1. Identifikasi truk yang available
        available_vehicles = []
        for vehicle_id, status in all_status.items():
            is_idle = status["state"] == "Idle"
            is_empty = status["current_load"] < 10.0  # hampir kosong
            not_assigned = status["assigned_tps"] is None
            at_garage_or_finished = (
                status["current_node"] == self.knowledge.garage_node or
                status["current_node"] not in self.knowledge.TPS_nodes
            )
            
            if is_idle and is_empty and not_assigned and at_garage_or_finished:
                available_vehicles.append((vehicle_id, status))
        
        if not available_vehicles:
            return commands
        
        # 2. Dapatkan prioritas TPS
        tps_priorities = self.knowledge.get_tps_priorities(current_time)
        
        # 3. Filter: hanya TPS yang belum ada truk assigned
        assigned_tps = set()
        for vehicle_id, status in all_status.items():
            if status["assigned_tps"]:
                assigned_tps.add(status["assigned_tps"])
        
        available_tps = [
            (tps, priority) 
            for tps, priority in tps_priorities 
            if tps not in assigned_tps and priority >= self.priority_threshold
        ]
        
        # 4. Match vehicles to TPS
        # Strategy: Greedy - assign closest vehicle to highest priority TPS
        for tps, priority in available_tps:
            if not available_vehicles:
                break
            
            # Find closest available vehicle to this TPS
            closest_vehicle = None
            closest_distance = float('inf')
            
            for vehicle_id, status in available_vehicles:
                try:
                    path_length = nx.shortest_path_length(
                        self.knowledge.G, 
                        status["current_node"], 
                        tps, 
                        weight="length"
                    )
                    if path_length < closest_distance:
                        closest_distance = path_length
                        closest_vehicle = (vehicle_id, status)
                except nx.NetworkXNoPath:
                    continue
            
            if closest_vehicle:
                vehicle_id, status = closest_vehicle
                available_vehicles.remove(closest_vehicle)
                
                command = {
                    "action": "move_to",
                    "target": tps
                }
                commands.append((vehicle_id, command))
                self.tasks_assigned += 1
        
        return commands
    
    def handle_arrival_at_tps(self, vehicle_id, tps_node, actual_waste):
        """
        Dipanggil ketika truk tiba di TPS.
        AI 'melihat' jumlah sampah dan memutuskan apakah loading.
        """
        # Update knowledge dengan observasi
        self.knowledge.observe_tps_waste(tps_node, actual_waste)
        
        # Putuskan: apakah loading?
        vehicle = self.vehicles[vehicle_id]
        
        if actual_waste >= 10.0:  # Ada cukup sampah untuk diambil
            # Hitung durasi loading (lebih banyak sampah = lebih lama)
            duration = min(actual_waste / 20.0, 10.0)  # max 10 detik
            
            command = {
                "action": "load",
                "duration": duration,
                "tps_node": tps_node
            }
            vehicle.execute_command(command)
        else:
            # Sampah terlalu sedikit, skip
            print(f"[AI] Vehicle {vehicle_id} skipping TPS {tps_node} - insufficient waste ({actual_waste:.1f} ton)")
    
    def handle_arrival_at_tpa(self, vehicle_id):
        """Dipanggil ketika truk tiba di TPA"""
        vehicle = self.vehicles[vehicle_id]
        
        if vehicle.current_load > 0:
            command = {
                "action": "unload",
                "duration": 3.0
            }
            vehicle.execute_command(command)
    
    def handle_stuck_vehicle(self, vehicle_id):
        """
        Handle truk yang застрял dalam kemacetan.
        
        Future enhancement:
        - Reroute ke path alternatif
        - Assign truk lain untuk TPS yang dituju
        """
        # Untuk sekarang: wait until traffic clears
        pass
    
    def execute_commands(self, commands):
        """Eksekusi semua command ke vehicles"""
        for vehicle_id, command in commands:
            if vehicle_id in self.vehicles:
                success = self.vehicles[vehicle_id].execute_command(command)
                if not success:
                    print(f"[AI] Failed to execute command for vehicle {vehicle_id}: {command}")
    
    def get_statistics(self):
        """Dapatkan statistik untuk monitoring"""
        return {
            "decisions_made": self.decisions_made,
            "tasks_assigned": self.tasks_assigned,
            "active_vehicles": sum(
                1 for v in self.vehicles.values() 
                if v.state not in ["Idle", "Standby"]
            ),
            "vehicles_at_garage": sum(
                1 for v in self.vehicles.values() 
                if v.current == self.knowledge.garage_node
            )
        }


class AdvancedAIController(AIController):
    """
    Advanced AI Controller dengan fitur tambahan:
    - Dynamic rerouting saat ada kemacetan
    - Predictive task assignment
    - Multi-objective optimization
    
    Bisa digunakan untuk eksperimen algoritma AI yang lebih kompleks.
    """
    
    def __init__(self, knowledge_model, vehicles, shift_start=6, shift_end=22):
        super().__init__(knowledge_model, vehicles, shift_start, shift_end)
        
        # Advanced parameters
        self.enable_rerouting = True
        self.enable_prediction = True
    
    def _assign_empty_vehicles_to_tps(self, all_status, current_time):
        """
        Advanced assignment dengan pertimbangan:
        - Traffic prediction
        - Multi-step planning
        - Load balancing
        """
        # TODO: Implementasi algoritma advanced
        # Untuk sekarang, gunakan base implementation
        return super()._assign_empty_vehicles_to_tps(all_status, current_time)
    
    def handle_stuck_vehicle(self, vehicle_id):
        """Advanced: Reroute vehicle jika застрял"""
        if not self.enable_rerouting:
            return super().handle_stuck_vehicle(vehicle_id)
        
        vehicle = self.vehicles[vehicle_id]
        
        # Get current destination
        if not vehicle.path or len(vehicle.path) < 2:
            return
        
        destination = vehicle.path[-1]
        
        # Find alternative route avoiding congested edges
        try:
            # Create weight function yang avoid congested edges
            def weight_function(u, v, d):
                base_length = d[0].get('length', 1.0)
                traffic_factor = self.knowledge.get_traffic_factor((u, v))
                
                # Penalize congested edges
                penalty = 1.0 / max(traffic_factor, 0.1)
                return base_length * penalty
            
            # Find new path
            new_path = nx.shortest_path(
                self.knowledge.G,
                vehicle.current,
                destination,
                weight=weight_function
            )
            
            # Update vehicle path
            vehicle._set_path(new_path)
            vehicle.state = "Moving"
            
            print(f"[AI] Rerouted vehicle {vehicle_id} due to congestion")
            
        except nx.NetworkXNoPath:
            print(f"[AI] Cannot find alternative route for vehicle {vehicle_id}")