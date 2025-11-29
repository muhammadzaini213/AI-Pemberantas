"""
Knowledge Model - SENSOR
Menyimpan pengetahuan AI tentang lingkungan dengan informasi TERBATAS.
"""


class KnowledgeModel:
    """
    SENSOR - Model pengetahuan tentang lingkungan.
    Menerima data dari sensor (truk, environment) dan menyimpan pengetahuan.
    
    PENGETAHUAN LENGKAP:
    - Semua rute (graph)
    - Lokasi TPS, TPA, Garasi
    - Waktu simulasi
    
    PENGETAHUAN TERBATAS (perlu observasi):
    - Jumlah sampah di TPS (hanya tahu saat truk loading)
    - Kemacetan (hanya tahu saat truk застрял atau lewat)
    """
    
    def __init__(self, graph, tps_nodes, tpa_node, garage_node):
        self.G = graph
        self.TPS_nodes = tps_nodes
        self.TPA_node = tpa_node
        self.garage_node = garage_node
        
        # Pengetahuan tentang TPS - TERBATAS
        self.tps_knowledge = {
            tps: {
                "waste_amount": None,  # None = unknown
                "last_visit_time": None,
                "last_observed_waste": None,
                "estimated_waste_rate": 10.0,  # ton/hour (estimasi)
                "priority": 0.5,  # default priority
                "visit_count": 0,
                "total_waste_collected": 0.0
            }
            for tps in tps_nodes
        }
        
        # Pengetahuan tentang traffic - TERBATAS
        self.traffic_knowledge = {}  # {(node1, node2): {"factor": 0-1, "last_update": time}}
        
        # Pengetahuan tentang truk
        self.vehicle_status = {}  # {vehicle_id: status_dict}
        
        # History untuk learning
        self.event_history = []
        
        # Statistics
        self.total_waste_collected = 0.0
        self.total_trips = 0
    
    def update_vehicle_status(self, vehicle):
        """Update status truk dari sensor"""
        status = vehicle.get_status()
        self.vehicle_status[vehicle.id] = status
    
    def process_event(self, event, current_time):
        """
        Proses event dari truk dan update knowledge.
        Event dari Vehicle.update()
        """
        self.event_history.append({"event": event, "time": current_time})
        
        event_type = event.get("type")
        
        if event_type == "arrived":
            node = event.get("node")
            vehicle_id = event.get("vehicle_id")
            
            # Cek apakah tiba di TPS
            if node in self.TPS_nodes:
                # Truk tiba di TPS, siap untuk observasi
                pass
        
        elif event_type == "loading_complete":
            tps = event.get("tps")
            if tps and tps in self.tps_knowledge:
                # NOW AI KNOWS: sampah yang diambil
                vehicle_status = self.vehicle_status.get(event.get("vehicle_id"))
                if vehicle_status:
                    waste_collected = vehicle_status["current_load"]
                    self.tps_knowledge[tps]["last_observed_waste"] = waste_collected
                    self.tps_knowledge[tps]["last_visit_time"] = current_time
                    self.tps_knowledge[tps]["visit_count"] += 1
                    self.tps_knowledge[tps]["total_waste_collected"] += waste_collected
                    
                    # Update estimasi waste rate berdasarkan observasi
                    if self.tps_knowledge[tps]["visit_count"] > 1:
                        # Learning: adjust waste rate based on actual observations
                        pass
        
        elif event_type == "stuck":
            edge = event.get("edge")
            traffic_factor = event.get("traffic_factor")
            
            # NOW AI KNOWS: ada kemacetan di edge ini
            self.traffic_knowledge[edge] = {
                "factor": traffic_factor,
                "last_update": current_time
            }
        
        elif event_type == "unloading_complete":
            # TPA received waste
            amount = event.get("amount", 0)
            self.total_waste_collected += amount
            self.total_trips += 1
    
    def observe_tps_waste(self, tps_node, actual_waste_amount):
        """
        Dipanggil ketika truk mulai loading di TPS.
        Ini adalah saat AI 'melihat' jumlah sampah sebenarnya.
        """
        if tps_node in self.tps_knowledge:
            self.tps_knowledge[tps_node]["waste_amount"] = actual_waste_amount
    
    def observe_traffic(self, edge, congestion_factor, current_time):
        """Observasi traffic dari environment atau truk yang lewat"""
        self.traffic_knowledge[edge] = {
            "factor": congestion_factor,
            "last_update": current_time
        }
    
    def estimate_tps_waste(self, tps_node, current_time):
        """
        Estimasi jumlah sampah di TPS berdasarkan pengetahuan terbatas.
        Menggunakan model sederhana: waste = rate * time_elapsed
        """
        info = self.tps_knowledge[tps_node]
        
        # Jika belum pernah dikunjungi, return estimasi default
        if info["last_visit_time"] is None:
            return 50.0  # estimasi awal (medium priority)
        
        # Jika pernah dikunjungi, estimasi berdasarkan rate dan waktu
        time_elapsed = current_time - info["last_visit_time"]
        
        # Gunakan observed waste rate jika ada
        if info["last_observed_waste"] is not None and info["last_visit_time"] is not None:
            estimated_waste = info["estimated_waste_rate"] * time_elapsed
        else:
            # Fallback ke default rate
            estimated_waste = 10.0 * time_elapsed
        
        return max(0.0, estimated_waste)
    
    def get_traffic_factor(self, edge):
        """Dapatkan traffic factor untuk edge (1.0 = lancar, <1.0 = macet)"""
        if edge in self.traffic_knowledge:
            return self.traffic_knowledge[edge]["factor"]
        
        # Reverse edge (undirected graph)
        reverse_edge = (edge[1], edge[0])
        if reverse_edge in self.traffic_knowledge:
            return self.traffic_knowledge[reverse_edge]["factor"]
        
        # Jika belum pernah diamati, asumsi lancar
        return 1.0
    
    def get_all_vehicle_status(self):
        """Dapatkan status semua truk"""
        return self.vehicle_status.copy()
    
    def get_tps_priorities(self, current_time):
        """
        Hitung prioritas semua TPS berdasarkan pengetahuan.
        
        Prioritas dihitung dari:
        - Estimasi jumlah sampah
        - Waktu sejak kunjungan terakhir
        - Historical data
        
        Return: [(tps_node, priority_score), ...]
        """
        priorities = []
        
        for tps in self.TPS_nodes:
            estimated_waste = self.estimate_tps_waste(tps, current_time)
            
            # Priority formula
            # Bisa dikembangkan lebih kompleks:
            # - Pertimbangkan jarak dari truk available
            # - Pertimbangkan historical pattern
            # - Pertimbangkan urgency (overflow risk)
            
            # Simple priority: normalized waste amount
            priority = min(estimated_waste / 100.0, 1.0)
            
            # Boost priority jika belum pernah dikunjungi
            if self.tps_knowledge[tps]["visit_count"] == 0:
                priority = max(priority, 0.6)
            
            priorities.append((tps, priority))
        
        return sorted(priorities, key=lambda x: x[1], reverse=True)
    
    def get_statistics(self):
        """Dapatkan statistik untuk monitoring"""
        return {
            "total_waste_collected": self.total_waste_collected,
            "total_trips": self.total_trips,
            "tps_visited": sum(1 for info in self.tps_knowledge.values() if info["visit_count"] > 0),
            "known_congestions": len(self.traffic_knowledge),
            "events_recorded": len(self.event_history)
        }