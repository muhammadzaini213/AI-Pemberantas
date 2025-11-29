"""
Vehicle Module - ACTUATOR
Truk sebagai pelaksana perintah tanpa logika pengambilan keputusan.
"""

import random
import networkx as nx
from .environment import VEHICLE_SPEED


class Vehicle:
    """
    ACTUATOR - Truk sebagai pelaksana perintah.
    
    Tidak memiliki logika pengambilan keputusan, hanya menjalankan perintah
    dari AI Controller.
    
    States:
    - Idle: Menunggu perintah
    - Moving: Bergerak ke tujuan
    - Loading: Mengambil sampah di TPS
    - Unloading: Membuang sampah di TPA
    - Stuck: Terjebak kemacetan
    - Standby: Standby (tidak aktif)
    """
    
    def __init__(self, vehicle_id, graph, garage_node, speed=VEHICLE_SPEED):
        # Identitas (sesuai struktur viewer)
        self.id = vehicle_id
        self.car_id = vehicle_id  # alias untuk viewer
        
        self.G = graph
        self.garage_node = garage_node
        
        # Posisi dan pergerakan
        self.current = garage_node
        self.path = []
        self.route = []  # alias untuk viewer
        self.progress = 0.0
        self.target_node = None
        
        # State truk
        self.state = "Idle"
        
        # Kapasitas (dalam kg untuk kompatibilitas dengan viewer)
        self.speed = speed
        self.capacity = 100.0  # ton
        self.max_load = 100000  # kg (untuk viewer)
        self.current_load = 0.0  # ton
        self.load = 0  # kg (untuk viewer)
        
        # Tracking jarak
        self.daily_dist = 0.0
        self.total_dist = 0.0
        
        # Timer untuk aksi
        self.action_timer = 0.0
        self.action_duration = 0.0
        
        # Task yang sedang dijalankan
        self.assigned_tps = None
    
    def execute_command(self, command):
        """
        Eksekusi perintah dari AI Controller.
        
        Args:
            command: Dictionary dengan format:
                {
                    "action": "move_to" | "load" | "unload" | "standby",
                    "target": node_id (optional),
                    "duration": float (optional, untuk load/unload),
                    "tps_node": node_id (optional, untuk load)
                }
        
        Returns:
            bool: True jika command berhasil dieksekusi
        """
        action = command.get("action")
        
        if action == "move_to":
            target = command.get("target")
            if target:
                return self._move_to(target)
        
        elif action == "load":
            duration = command.get("duration", 5.0)
            self.assigned_tps = command.get("tps_node")
            return self._start_loading(duration)
        
        elif action == "unload":
            duration = command.get("duration", 3.0)
            return self._start_unloading(duration)
        
        elif action == "standby":
            self.state = "Standby"
            return True
        
        return False
    
    def _move_to(self, target_node):
        """Internal: set path ke target"""
        if target_node not in self.G.nodes():
            return False
        
        # Jika sudah di target, tidak perlu move
        if self.current == target_node:
            return True
        
        try:
            path = nx.shortest_path(self.G, self.current, target_node, weight="length")
            self._set_path(path)
            return True
        except nx.NetworkXNoPath:
            return False
    
    def _set_path(self, path):
        """Internal: set path untuk pergerakan"""
        self.path = path
        self.route = path  # sync dengan viewer
        if len(path) > 1:
            self.current = path[0]
            self.target_node = path[1]
            self.progress = 0.0
            self.state = "Moving"
        else:
            self.state = "Idle"
    
    def _start_loading(self, duration):
        """Internal: mulai loading"""
        self.state = "Loading"
        self.action_timer = 0.0
        self.action_duration = duration
        return True
    
    def _start_unloading(self, duration):
        """Internal: mulai unloading"""
        self.state = "Unloading"
        self.action_timer = 0.0
        self.action_duration = duration
        return True
    
    def _sync_load_units(self):
        """Sync antara ton dan kg untuk kompatibilitas viewer"""
        self.load = int(self.current_load * 1000)  # ton -> kg
    
    def get_status(self):
        """
        Dapatkan status lengkap truk untuk sensor.
        
        Returns:
            dict: Status truk
        """
        return {
            "id": self.id,
            "state": self.state,
            "current_node": self.current,
            "target_node": self.target_node,
            "current_load": self.current_load,
            "capacity": self.capacity,
            "assigned_tps": self.assigned_tps,
            "progress": self.progress,
            "path": self.path.copy() if self.path else []
        }
    
    def update(self, dt, shared, traffic_factor=1.0):
        """
        Update state truk setiap frame.
        
        Args:
            dt: Delta time (seconds)
            shared: Shared state object
            traffic_factor: Traffic congestion factor (1.0 = clear, <1.0 = congested)
        
        Returns:
            list: Events yang terjadi pada update ini
        """
        if shared.paused:
            return []
        
        events = []
        real_speed = self.speed * shared.speed
        
        # ===== STATE: LOADING =====
        if self.state == "Loading":
            self.action_timer += dt
            if self.action_timer >= self.action_duration:
                # Loading selesai
                self.current_load = self.capacity
                self._sync_load_units()
                self.state = "Idle"
                
                events.append({
                    "type": "loading_complete",
                    "vehicle_id": self.id,
                    "node": self.current,
                    "tps": self.assigned_tps
                })
                self.assigned_tps = None
            return events
        
        # ===== STATE: UNLOADING =====
        if self.state == "Unloading":
            self.action_timer += dt
            if self.action_timer >= self.action_duration:
                # Unloading selesai
                unloaded_amount = self.current_load
                self.current_load = 0.0
                self._sync_load_units()
                self.state = "Idle"
                
                events.append({
                    "type": "unloading_complete",
                    "vehicle_id": self.id,
                    "node": self.current,
                    "amount": unloaded_amount
                })
            return events
        
        # ===== STATE: STUCK =====
        if self.state == "Stuck":
            # Truk застрял, perlu command eksternal untuk melanjutkan
            # Cek apakah traffic sudah clear
            if traffic_factor > 0.5:
                self.state = "Moving"
                events.append({
                    "type": "unstuck",
                    "vehicle_id": self.id,
                    "edge": (self.current, self.target_node)
                })
            return events
        
        # ===== STATE: STANDBY / IDLE =====
        if self.state in ["Standby", "Idle"]:
            return events
        
        # ===== STATE: MOVING =====
        if self.state == "Moving":
            if not self.path or self.target_node is None:
                self.state = "Idle"
                return events
            
            # Get edge data
            edge_data = self.G.get_edge_data(self.current, self.target_node)
            if not edge_data:
                self.state = "Idle"
                return events
            
            length = edge_data[0]['length']
            
            # Deteksi kemacetan parah
            if traffic_factor <= 0.3:
                self.state = "Stuck"
                events.append({
                    "type": "stuck",
                    "vehicle_id": self.id,
                    "edge": (self.current, self.target_node),
                    "traffic_factor": traffic_factor
                })
                return events
            
            # Update posisi dengan kecepatan disesuaikan traffic
            adjusted_speed = real_speed * traffic_factor
            distance = adjusted_speed * dt
            self.progress += distance / length
            
            # Track jarak tempuh
            self.daily_dist += distance
            self.total_dist += distance
            
            # Cek apakah sampai di node berikutnya
            if self.progress >= 1.0:
                idx = self.path.index(self.target_node)
                
                if idx + 1 < len(self.path):
                    # Masih ada node berikutnya
                    self.current = self.target_node
                    self.target_node = self.path[idx + 1]
                    self.progress = 0.0
                else:
                    # Sampai di tujuan akhir
                    destination = self.target_node
                    self.current = self.target_node
                    self.target_node = None
                    self.path = []
                    self.state = "Idle"
                    
                    events.append({
                        "type": "arrived",
                        "vehicle_id": self.id,
                        "node": destination
                    })
        
        return events
    
    def get_pos(self, pos_dict):
        """
        Dapatkan posisi visual truk untuk rendering.
        
        Args:
            pos_dict: Dictionary mapping node_id -> (x, y)
        
        Returns:
            tuple: (x, y) position
        """
        if self.target_node is None:
            return pos_dict[self.current]
        
        # Interpolasi antara current dan target
        x1, y1 = pos_dict[self.current]
        x2, y2 = pos_dict[self.target_node]
        x = x1 + (x2 - x1) * self.progress
        y = y1 + (y2 - y1) * self.progress
        return (x, y)
    
    def get_load_percentage(self):
        """Dapatkan persentase muatan"""
        return (self.current_load / self.capacity) * 100.0
    
    def is_full(self):
        """Cek apakah truk penuh"""
        return self.current_load >= self.capacity * 0.95
    
    def is_empty(self):
        """Cek apakah truk kosong"""
        return self.current_load < 10.0