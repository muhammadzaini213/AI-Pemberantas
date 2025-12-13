# Simulasi Agen Koordinator Truk Sampah Menggunakan Matheuristic Rollout dalam Kondisi Uncertain (Stochastic) Kota Balikpapan

---

<img width="1600" height="1005" alt="image" src="https://github.com/user-attachments/assets/0c2b3193-f3db-42ff-bab2-ceab704daffb" />


## Kelompok 10

| Nama              | NIM      |
| ----------------- | -------- |
| Muhammad Zaini    | 11241064 |
| Ahmad Rafif Rafi  | 11241006 |
| Mayoga Finanda    | 11241044 |
| Ferdianta Tarigan | 11241030 |

---

<br> 

# A. Abstract
Nanti abstract belakangan

---

<br> 

# B. Data Used
## 1. Total TPS, sebaran, dan jumlah sampah per hari
Data diambil dari KAJIAN POOL KENDARAAN PENGANGKUTAN SAMPAH DI KOTA BALIKPAPAN TAHUN 2022
<img width="407" height="875" alt="image" src="https://github.com/user-attachments/assets/97fa218e-26c6-4d06-a2e5-dc350d684d47" />
<img width="890" height="686" alt="image" src="https://github.com/user-attachments/assets/26705395-f821-454d-80bf-c1e1bfbd3592" />

NOTE: Dikarenakan terdapat 417 TPS, kami menghomogenkan seluruh data dengan mengambil rata-rata dari seluruh TPS dan memberikannya interval ±30% randomisasi agar dapat lebih fokus ke proses pengembangan AI.

<br>

## 2. Jadwal pengambilan sampah
<a href="https://rri.co.id/lain-lain/537534/dlh-balikpapan-atur-ulang-jadwal-angkut-sampah">Jadwal Angkut Sampah Balikpapan</a>
<br>
<img width="517" height="115" alt="image" src="https://github.com/user-attachments/assets/7054b0d8-2f7e-4643-9320-ea5a8adad782" />

<br>

## 3. Lokasi TPA
<a href="https://pu.go.id/berita/diresmikan-presiden-pembangunan-tpa-sampah-manggar-di-balikpapan-terbaik-di-indonesia">Peresmian TPA Manggar</a>
<br>
<img width="667" height="519" alt="image" src="https://github.com/user-attachments/assets/f9892404-0a4d-471c-a436-ab89a1f076ac" />

<br>

# C. Methods

## 1. Matheuristic Rollout
Metode Rollout merupakan teknik matheuristic yang  tujuannya meningkatkan kualitas keputusan dalam masalah sequential decision-making pada lingkungan stochastic. Rollout bekerja dengan memanfaatkan base policy (keputusan cepat) sebagai kebijakan awal, kemudian melakukan evaluasi ke depan (look-ahead) untuk memilih tindakan yang lebih baik daripada keputusan dasar.

Konsep dasar Rollout adalah menilai beberapa aksi kandidat melalui simulasi pendek menggunakan base policy. Setiap aksi dihitung nilai biayanya sesuai objective function yang telah dibuat, kemudian aksi dengan hasil terbaik akan dipilih untuk dieksekusi

Peningkatan keputusan terjadi karena Rollout tidak hanya berusaha melihat kondisi saat ini, tetapi juga memprediksi dampak tindakan pada beberapa langkah ke depan terutama pada kondisi yang berubah-ubah mulai dari kemacetan jalan dan fluktuasi volume sampah yang tidak selalu diketahui

Algoritma look-ahead dilakukan dengan:

* memilih aksi kandidat,

* menjalankan simulasi singkat berbasis base policy,

* mengevaluasi total biaya, dan

* memilih aksi dengan nilai optimal.

Pada tahap eksekusi rute, sistem menggunakan ```shortest path``` dari ```OSMnx``` untuk menentukan jalur perjalanan truk pada jaringan jalan yang dapat diberikan pengecualian. Namun, aspek ini tidak menjadi fokus utama penelitian karena pathfinding hanya berfungsi sebagai komponen teknis pendukung. Fokus utama simulasi adalah pada multi-target, multi-instance decision-making, yaitu bagaimana agen truk mengambil keputusan rute dan prioritas TPS secara adaptif melalui mekanisme Rollout.

<br> 

## 2. Objective Function

Komponen fungsi objektif mencakup:

* minimisasi waktu tempuh
* minimisasi total perjalanan
* reduksi tingkat penumpukan TPS
* optimasi energi atau biaya operasional

Sertakan formulasi matematika dalam bentuk persamaan.

<br> 

## 3. Knowledge model

<br> 

#### a) Peta dan Lokasi TPS/TPA Diketahui

Representasi peta kota:

```
G = (V, E)
```

**Makna variabel:**

| Variabel     | Penjelasan                                           |
| ------------ | ---------------------------------------------------- |
| `G`          | Graph atau peta kota                                 |
| `V`          | Himpunan semua node (simpul jalan, TPS, TPA, garasi) |
| `E`          | Himpunan semua edge (ruas jalan)                     |
| `(x_v, y_v)` | Koordinat geografis dari node `v`                    |
| `V_TPS`      | Subset node yang merupakan TPS                       |
| `V_TPA`      | Subset node yang merupakan TPA                       |
| `V_GARAGE`   | Subset node yang merupakan GARAGE                    |

**Formulasi:**

```
∀ v ∈ V : lokasi (x_v, y_v) diketahui
v ∈ V_TPS (lokasi TPS diketahui)
v ∈ V_TPA (lokasi TPA diketahui)
v ∈ V_GARAGE (lokasi Garasi diketahui)

```
Artinya model sudah mengetahui semua rute serta lokasi TPS, TPA, dan Garasi secara lengkap.

<br> 

#### b) Delay & Kemacetan Tidak Diketahui Sebelum Dialami

Model waktu tempuh:

```
T_e = T_e_base × S_e
```

**Makna variabel:**

| Variabel   | Penjelasan                                         |
| ---------- | -------------------------------------------------- |
| `T_e`      | Waktu tempuh aktual pada edge `e`                  |
| `T_e_base` | Waktu tempuh tanpa hambatan (baseline)             |
| `S_e`      | Faktor slowdown (kemacetan, hambatan, delay)       |
| `f_e(t)`   | Distribusi probabilitas untuk slowdown di edge `e` |

Sifat pengetahuan:

```
S_e = unknown        jika truk belum melewati edge e
S_e = observed value jika truk telah melewati edge e
```

Artinya model hanya mengetahui kondisi kemacetan setelah truk mengalaminya.

<br> 

#### c) Volume Sampah TPS Tidak Diketahui Sebelum Truk Tiba

Model volume sampah:

```
W_i ~ g_i(t)
```

**Makna variabel:**

| Variabel | Penjelasan                                         Ŵ_i(t)  |
| -------- | ---------------------------------------------------- |
| `W_i`    | Volume sampah aktual di TPS `i`                      |
| `g_i(t)` | Distribusi probabilitas volume sampah TPS `i`        |
| `A_i(t)` | Indikator apakah sudah ada truk yang tiba di TPS `i` |
| `Ŵ_i(t)` | Informasi volume sampah yang diketahui sistem        |

Indikator kunjungan:

```
A_i(t) = 0 (belum ada truk yang tiba)
A_i(t) = 1 (sudah ada truk yang tiba)
```

Pengetahuan sistem:

```
Ŵ_i(t) = W_i(t)     jika A_i(t) = 1
Ŵ_i(t) = unknown    jika A_i(t) = 0
```

Artinya model tidak mengetahui berapa volume sampah sebelum setidaknya satu truk benar-benar tiba di TPS tersebut.

---

<br> 

# D. Implementation

### 1. Environment Setup
Pada sistem yang telah kami buat, kami menggunakan library pygame untuk melakukan visualisasi dan simulasi untuk environment. Dengan data ```.graphml``` yang diambil langsung dari ```openstreetmap.org``` melalui library osmnx yang tersedia di python.

Untuk menambahkan data TPA, TPS, Garasi, Mobil, dan Kemacetan, kami menyediakan map editor sehingga pengeditan dapat dilakukan dengan lebih leluasa dan mudah yang datanya akan disimpan dalam file ```.json```. Meskipun begitu, data yang cukup jarang diubah seperti kecepatan kendaraan, waktu shift, serta warna warna node dan edges, kami letakkan di ```src/environment.py```.

<br> 

### 2. Data Modeling

##### a) Nodes data model

```json
node_id: {
    "tps": boolean,
    "tpa": boolean,
    "garage": boolean,

    "tps_data": {
        "nama": String, 
        "sampah_kg": float, 
        "sampah_per_hari": float, # Interval ±30%
    },

    "tpa_data": {
        "nama": String, 
        "total_sampah": float
    },

    "garage_data": {
        "nama": "Garage", 
        "total_armada": int, 
        "armada_bertugas": int, 
        "armada_standby": int
    }
}
```

<br> 

##### b) Edges data model

```json
    edge_id: {
    "slowdown": float,
    "slowdown_start": int,
    "slowdown_end": int
    },
```

##### c) Truck data model

```json
    truck_id: {
        "garage_node": node_id,
        "state": enum CarState, # Idle, Moving, Loading, Unloading, Stuck, Standby
        "speed": float,
        "daily_dist": float,
        "total_dist": float,
        "load": float,
        "max_load": float,
        "route": list[node_id]
    }
```

##### d) Environment
```python
# ================== WINDOW ==================
APP_NAME = "Simulasi Truk Sampah Balikpapan"
WIDTH = 800
HEIGHT = 600
CAM_SPEED = 10
MAX_FPS = 60

# ================== TEST SETUP ==================
GRAPH_FILE = "./data/simpl_balikpapan_drive.graphml"


# ================== VEHICLE ==================
VEHICLE_SPEED = 48 
VEHICLE_CAP = 20000


# ================== SHIFT SETTINGS (00:00 WITH INTEGER 0) ==================
SHIFT_START = 6
SHIFT_END = 22

# ================== SPRITES ==================
NODE_COL = (255,120,120) # Node kuning
LINE_COL = (150,150,150) # Jalanan putih

AGENT_COL = (0,255,0) # Mobil Hijau
TPS_COL = (255,220,0) # TPS kuning
TPA_COL = (0,150,255) # TPA biru
GARAGE_COL = (139, 69, 19) # Garasi coklat
```

<br> 

### 3. Rollout Algorithm Integration
#### a) Dispatch
Pada awal jam kerja, truk yang tersedia akan dikeluarkan dari garasi dan pergi menuju TPS yang tersedia, pada proses ini dilakukan base policy untuk menentukan rute tercepat secara deterministik, kemudian dilakukan proses look ahead berdasarkan pengalaman dari truk sebelumnya (kemacetan, jumlah sampah terakhir).

#### b) Gathering
Setelah truk mencapai TPS, sampah akan diambil berdasarkan kapasitas maksimal truk, kemudian diantarkan ke TPA, proses ini akan dilakukan selama jam kerja dan akan diakhiri jika jam kerja selesai ataupun semua sampah harian di TPS telah dikosongkan.

#### c) Reschedule/Rerouting
Jika truk mendapat pengetahuan baru seperti jalan macet serta jumlah sampah di TPS, modal akan melakukan reschedule ulang untuk memastikan apakah rute sekarang masih efektif atau tidak dan menyesuaikan dengan meminimalkan perubahan rute pada truk lain yang tidak relevan dengan kondisi yang terjadi.

#### d) Ending
Jika sampah sudah habis atau jam kerja sudah selesai, semua truk akan kembali dan model akan melakukan evaluasi untuk menentukan mekanisme saat dispatch di jam kerja selanjutnya agar lebih efektif.

<br> 

### 4. Simulation Engine

##### a) Memulai simulasi
Pada ```src/simulation.py```, simulasi akan langsung menginisialisasi graph, nodes, serta vehicle

```python

    # ======================== VIEWER ========================
    viewer = GraphViewer(pos, shared)
    range_x = viewer.max_x - viewer.min_x
    range_y = viewer.max_y - viewer.min_y

    viewer.scale = min(viewer.WIDTH / range_x, viewer.HEIGHT / range_y) * 0.95
    viewer.offset_x = viewer.WIDTH/2 - ((viewer.min_x+viewer.max_x)/2 - viewer.min_x)*viewer.scale
    viewer.offset_y = viewer.HEIGHT/2 - ((viewer.max_y+viewer.min_y)/2 - viewer.min_y)*viewer.scale

    TPS_nodes, TPA_nodes, GARAGE_nodes = initNodes(GRAPH, shared)
    
    vehicles = []
    generate_car_in_garage(GARAGE_nodes, shared, vehicles, GRAPH, TPS_nodes, TPA_nodes)

    last_garbage_generation_day = shared.sim_day
```

Kemudian KnowledgeModel dan AIModel akan diinisialisasi, program juga dimulai dengan kondisi pause dan bisa diaktifkan melalui map editor

```python
    # ======================== MODEL INITIALIZATION ========================
    knowledge_model = KnowledgeModel(GRAPH, shared, TPS_nodes, TPA_nodes, GARAGE_nodes)
    shared.knowledge_model = knowledge_model
    
    print(f"[Simulation] KnowledgeModel initialized")
    print(f"[Simulation] Agent knowledge: {knowledge_model.get_knowledge_summary()}")

    ai_model = AIModel(knowledge_model, shared)
    shared.ai_model = ai_model
    
    print(f"[Simulation] AIModel initialized with Matheuristic Rollout")
    
    running = True
    shared.paused = True
    
    print(f"\n[Simulation] Entering main loop...")
    print(f"[Simulation] simulation_running flag: {shared.simulation_running}")
```

<br>

##### b) Actuator dan Sensor di Vehicle
Pada ```src/classes/vehicle.py``` diberikan actuators atau cara AI berinteraksi dengan environment, namun ini hanya sebatas logic control dan pengambilan informasi sederhana.

```python
import random
import networkx as nx
from ..environment import VEHICLE_SPEED, VEHICLE_CAP
import uuid

class Vehicle:
    def __init__(self, graph, tps_nodes=None, tpa_node=None, garage_nodes=None, shared=None):
        self.id = str(uuid.uuid4())[:8]
        
        self.G = graph
        self.TPS_nodes = tps_nodes
        self.TPA_node = tpa_node
        self.garage_nodes = garage_nodes or []
        self.shared = shared
        self.garage_node = None 
        self.current = None
        
        # ===== Vehicle tracking data =====
        self.path = []
        self.progress = 0.0
        self.target_node = None
        self.state = "idle"
        self.speed = VEHICLE_SPEED  # Speed in meters/second or km/hour
        
        # ===== Tracking metrics (in meters) =====
        self.daily_dist = 0.0
        self.total_dist = 0.0
        self.load = 0
        self.max_load = VEHICLE_CAP
        self.route = []
        
        print(f"[Vehicle] Created ID: {self.id}")

    def _update_garage_stats(self):
        if not self.garage_node or not self.shared:
            return
        
        if self.garage_node in self.shared.node_type:
            garage_data = self.shared.node_type[self.garage_node].get("garage_data", {})
            
            if self.state == "idle":
                garage_data["armada_standby"] = garage_data.get("armada_standby", 0) + 1
            else:
                garage_data["armada_bertugas"] = garage_data.get("armada_bertugas", 0) + 1
            
            print(f"[Vehicle {self.id}] Updated garage {self.garage_node} stats: standby={garage_data.get('armada_standby', 0)}, bertugas={garage_data.get('armada_bertugas', 0)}")

    def _update_state_in_garage_stats(self, old_state):
        if not self.garage_node or not self.shared:
            return
        
        if self.garage_node in self.shared.node_type:
            garage_data = self.shared.node_type[self.garage_node].get("garage_data", {})
            
            if old_state == "idle":
                garage_data["armada_standby"] = max(0, garage_data.get("armada_standby", 0) - 1)
            else:
                garage_data["armada_bertugas"] = max(0, garage_data.get("armada_bertugas", 0) - 1)
            
            if self.state == "idle":
                garage_data["armada_standby"] = garage_data.get("armada_standby", 0) + 1
            else:
                garage_data["armada_bertugas"] = garage_data.get("armada_bertugas", 0) + 1

    def _decrement_garage_stats(self, garage_node):
        if not garage_node or not self.shared:
            return
        
        if garage_node in self.shared.node_type:
            garage_data = self.shared.node_type[garage_node].get("garage_data", {})
            
            if self.state == "idle":
                garage_data["armada_standby"] = max(0, garage_data.get("armada_standby", 0) - 1)
            else:
                garage_data["armada_bertugas"] = max(0, garage_data.get("armada_bertugas", 0) - 1)

    def update_garage_assignment(self, new_garage_node):
        if not self.shared or not self.garage_node:
            return
        
        self._decrement_garage_stats(self.garage_node)
        
        self.garage_node = new_garage_node
        self._update_garage_stats()
        print(f"[Vehicle {self.id}] Reassigned to garage {new_garage_node}")




    # ============== ACTUATOR (NO BRAIN LOGIC) ==============    
    def actuator_set_path(self, path):
        self.set_path(path)

    def actuator_go_to_location(self, target_node):
        if target_node == self.current:
            return False
        try:
            path = nx.shortest_path(self.G, self.current, target_node, weight="length")
            self.set_path(path)
            return True
        except:
            return False

    def actuator_go_to_tps(self):
        if not self.TPS_nodes:
            return False
        old_state = self.state
        goal = random.choice(list(self.TPS_nodes))
        try:
            path = nx.shortest_path(self.G, self.current, goal, weight="length")
            self.set_path(path)
            self.state = "to_tps"
            if old_state == "idle":
                self._update_state_in_garage_stats(old_state)
            return True
        except:
            return False

    def actuator_go_to_tpa(self):
        if not self.TPA_node:
            print(f"[Vehicle {self.id}] ERROR: No TPA_node configured!")
            return False
        
        if isinstance(self.TPA_node, (set, list)):
            if len(self.TPA_node) == 0:
                print(f"[Vehicle {self.id}] ERROR: TPA_node is empty set/list!")
                return False
            tpa_target = list(self.TPA_node)[0]
        else:
            tpa_target = self.TPA_node
        
        if self.current == tpa_target:
            print(f"[Vehicle {self.id}] Already at TPA {tpa_target}")
            self.state = "at_tpa"
            return True
        
        old_state = self.state
        try:
            path = nx.shortest_path(self.G, self.current, tpa_target, weight="length")
            
            if not path or len(path) < 2:
                print(f"[Vehicle {self.id}] ERROR: Invalid path to TPA!")
                return False
            
            self.set_path(path)
            self.state = "to_tpa"
            
            if old_state == "idle":
                self._update_state_in_garage_stats(old_state)
            
            path_distance = sum(
            self.G[path[i]][path[i+1]][0]['length'] 
            for i in range(len(path)-1)
            )
            print(f"[Vehicle] {self.id} Routing to TPA {tpa_target} (distance: {path_distance:.0f}m / {path_distance/1000:.2f}km)")  # ✅ meter & km
            return True
        except Exception as e:
            print(f"[Vehicle {self.id}] ERROR: Failed to route to TPA: {e}")
            return False

    def actuator_go_to_garage(self):
        if not self.garage_node:
            return False
        try:
            path = nx.shortest_path(self.G, self.current, self.garage_node, weight="length")
            self.set_path(path)
            self.state = "to_garage"
            return True
        except:
            return False

    def actuator_load_garbage(self, amount):
        can_load = min(amount, self.max_load - self.load)
        self.load += can_load
        return can_load

    def actuator_unload_garbage(self):
        old_load = self.load
        self.load = 0
        return old_load

    def actuator_get_load_percentage(self):
        return (self.load / self.max_load) * 100 if self.max_load > 0 else 0

    def actuator_is_full(self):
        return self.load >= self.max_load

    def actuator_is_empty(self):
        return self.load <= 0

    def actuator_get_status(self):
        return {
            "id": self.id,
            "state": self.state,
            "current_node": self.current,
            "target_node": self.target_node,
            "load": self.load,
            "max_load": self.max_load,
            "load_percentage": self.actuator_get_load_percentage(),
            "is_full": self.actuator_is_full(),
            "is_empty": self.actuator_is_empty(),
            "daily_dist": self.daily_dist / 10_000_000,
            "total_dist": self.total_dist / 10_000_000,
            "garage_node": self.garage_node,
            "route": self.route
        }

    def actuator_idle(self):
        old_state = self.state
        self.state = "idle"
        if old_state != "idle":
            self._update_state_in_garage_stats(old_state)
        return True

    # ============== ACTUATORS + SENSORS LOGIC==============
    def actuator_arrive_at_tps(self):
        if self.current in self.TPS_nodes and self.shared:
            tps_data = self.shared.node_type[self.current].get("tps_data", {})
            current_garbage = tps_data.get("sampah_kg", 0)
            
            if hasattr(self.shared, 'knowledge_model'):
                self.shared.knowledge_model.discover_garbage(self.current, current_garbage)
            
            self.state = "at_tps"
            print(f"[Vehicle {self.id}] Arrived at TPS {self.current}, found {current_garbage:.2f} kg")
            return True
        return False

    def actuator_load_from_tps(self, amount=None):
        if self.state != "at_tps" or self.current not in self.TPS_nodes:
            return 0
        
        tps_data = self.shared.node_type[self.current].get("tps_data", {})
        available = tps_data.get("sampah_kg", 0)
        
        if amount is None:
            amount = available
        
        loaded = self.actuator_load_garbage(amount)
        tps_data["sampah_kg"] = max(0, available - loaded)
        
        print(f"[Vehicle {self.id}] Loaded {loaded:.2f} kg from TPS {self.current} (remaining: {tps_data['sampah_kg']:.2f} kg)")
        return loaded

    def actuator_arrive_at_tpa(self):
        if isinstance(self.TPA_node, (set, list)):
            is_at_tpa = self.current in self.TPA_node
        else:
            is_at_tpa = self.current == self.TPA_node
        
        if is_at_tpa:
            self.state = "at_tpa"
            print(f"[Vehicle {self.id}] Arrived at TPA {self.current}")
            return True
        return False

    def actuator_unload_to_tpa(self):
        if self.state != "at_tpa":
            print(f"[Vehicle {self.id}] ERROR: Not at TPA (state: {self.state})")
            return 0
        
        if isinstance(self.TPA_node, (set, list)):
            is_at_tpa = self.current in self.TPA_node
        else:
            is_at_tpa = self.current == self.TPA_node
        
        if not is_at_tpa:
            print(f"[Vehicle {self.id}] ERROR: Current node {self.current} is not a TPA!")
            return 0
        
        unloaded = self.actuator_unload_garbage()
        
        if unloaded > 0:
            if self.current in self.shared.node_type:
                tpa_data = self.shared.node_type[self.current].get("tpa_data", {})
                tpa_data["total_sampah"] = tpa_data.get("total_sampah", 0) + unloaded
            
            print(f"[Vehicle {self.id}] ✓ Unloaded {unloaded:.0f}kg to TPA {self.current}")
        
        return unloaded

    def actuator_arrive_at_garage(self):
        if self.current == self.garage_node:
            self.state = "idle"
            print(f"[Vehicle {self.id}] Arrived at garage {self.garage_node}")
            return True
        return False

    def actuator_discover_slowdown(self):
        if not self.target_node or not self.shared:
            return None
        
        edge_id = f"{self.current}-{self.target_node}"
        
        if hasattr(self.shared, 'edge_type') and edge_id in self.shared.edge_type:
            slowdown = self.shared.edge_type[edge_id].get("slowdown", 0)
            
            if slowdown > 0 and hasattr(self.shared, 'knowledge_model'):
                self.shared.knowledge_model.discover_slowdown(edge_id, slowdown)
            
            return slowdown
        
        return None

    def actuator_get_current_location(self):
        return self.current

    def actuator_at_target(self):
        return self.target_node is None or self.progress >= 1.0

    # ============== IF THIS WORKS IT WORKS ==============
    def set_path(self, path):
        if not path or len(path) == 0:
            print(f"[Vehicle {self.id}] Warning: Empty path provided")
            self.path = []
            self.route = []
            self.target_node = None
            self.progress = 0.0
            return
        
        self.path = path
        self.route = path.copy()
        
        if len(path) > 1:
            self.current = path[0]
            self.target_node = path[1]
            self.progress = 0.0
        else:
            self.current = path[0]
            self.target_node = None
            self.progress = 0.0

    def return_to_idle(self):
        old_state = self.state
        self.state = "idle"
        self._update_state_in_garage_stats(old_state)
        print(f"[Vehicle {self.id}] Returned to idle at garage {self.garage_node}")

    def update(self, dt, shared):
        if shared.paused:
            return

        real_speed = self.speed * shared.speed

        if not self.path or self.target_node is None:
            if self.state in ["idle", "at_tps", "at_tpa"]:
                return
            
            neighbors = list(self.G.neighbors(self.current))
            if not neighbors:
                return
            try:
                self.state = "random"
            except:
                pass
            return
        
        if self.target_node not in self.path:
            print(f"[Vehicle {self.id}] ERROR: target_node {self.target_node} not in path! Resetting path.")
            self.path = []
            self.target_node = None
            self.progress = 0.0
            return
        
        edge_data = self.G.get_edge_data(self.current, self.target_node)
        if not edge_data:
            print(f"[Vehicle {self.id}] ERROR: No edge between {self.current} and {self.target_node}! Resetting path.")
            self.path = []
            self.target_node = None
            self.progress = 0.0
            return
        
        length = edge_data[0]['length']

        edge_id = f"{self.current}-{self.target_node}"
        actual_speed = real_speed  # m/s
        
        if shared and hasattr(shared, 'edge_type') and edge_id in shared.edge_type:
            slowdown_value = shared.edge_type[edge_id].get("slowdown", 0)
            if slowdown_value > 0:
                actual_speed = slowdown_value * shared.speed
                
                if hasattr(shared, 'knowledge_model'):
                    shared.knowledge_model.discover_slowdown(edge_id, slowdown_value)
        
        distance = actual_speed * dt
        
        self.progress += distance / length
        
        self.daily_dist += distance / 1000
        self.total_dist += distance / 1000

        if self.progress >= 1.0:
            try:
                idx = self.path.index(self.target_node)
            except ValueError:
                print(f"[Vehicle {self.id}] ERROR: target_node {self.target_node} disappeared from path! Resetting.")
                self.current = self.target_node if self.target_node else self.current
                self.path = []
                self.target_node = None
                self.progress = 0.0
                return
            
            if idx + 1 < len(self.path):
                self.current = self.target_node
                self.target_node = self.path[idx + 1]
                self.progress = 0.0
            else:
                self.current = self.target_node
                self.target_node = None
                self.path = []
                self.progress = 0.0
                
                # ===== Handle arrival at destination =====
                if self.state == "to_garage" and self.current == self.garage_node:
                    self.return_to_idle()
                
                elif self.state == "to_tps" and self.current in self.TPS_nodes:
                    old_state = self.state
                    self.state = "at_tps"
                    if old_state != "at_tps":
                        self._update_state_in_garage_stats(old_state)
                    
                    if hasattr(shared, 'knowledge_model'):
                        tps_data = shared.node_type[self.current].get("tps_data", {})
                        current_garbage = tps_data.get("sampah_kg", 0)
                        shared.knowledge_model.discover_garbage(self.current, current_garbage)
                    
                    print(f"[Vehicle {self.id}] Arrived at TPS {self.current}")
                
                elif self.state == "to_tpa":
                    if isinstance(self.TPA_node, (set, list)):
                        is_at_tpa = self.current in self.TPA_node
                    else:
                        is_at_tpa = self.current == self.TPA_node
                    
                    if is_at_tpa:
                        old_state = self.state
                        self.state = "at_tpa"
                        if old_state != "at_tpa":
                            self._update_state_in_garage_stats(old_state)
                        print(f"[Vehicle {self.id}] Arrived at TPA {self.current}")
                
                else:
                    print(f"[Vehicle {self.id}] Arrived at node {self.current} (state: {self.state})")

    def get_pos(self, pos_dict):
        if self.target_node is None:
            return pos_dict[self.current]
        x1, y1 = pos_dict[self.current]
        x2, y2 = pos_dict[self.target_node]
        x = x1 + (x2 - x1) * self.progress
        y = y1 + (y2 - y1) * self.progress
        return (x, y)
```

##### c) KnowledgeModel menyimpan data dari sensor
Di ```src/classes/knowledge.py``` akan disimpan semua informasi yang tersedia untuk dipakai oleh AIModel nantinya
```python
import networkx as nx

class KnowledgeModel:
    
    def __init__(self, graph, shared, tps_nodes, tpa_nodes, garage_nodes):
        self.graph = graph
        self.shared = shared
        self.TPS_nodes = tps_nodes
        self.TPA_nodes = tpa_nodes
        self.GARAGE_nodes = garage_nodes
        
        # ===== Known information (statis) =====
        self.known_garages = {node_id: self._get_garage_info(node_id) for node_id in garage_nodes}
        self.known_tps = {node_id: self._get_tps_static_info(node_id) for node_id in tps_nodes}
        self.known_tpa = {node_id: self._get_tpa_info(node_id) for node_id in tpa_nodes}
        

        # ===== Discovered information (dinamis) =====
        self.discovered_slowdowns = {}
        self.discovered_garbage = {}

        
        # ===== Vehicle tracking =====
        self.vehicle_statuses = {}
        self.vehicle_assignments = {}
        self.all_vehicle_ids = set()
        


    # ============== STATIC KNOWLEDGE ==============
    def _get_garage_info(self, garage_id):
        if garage_id in self.shared.node_type:
            garage_data = self.shared.node_type[garage_id].get("garage_data", {})
            return {
                "node_id": garage_id,
                "nama": garage_data.get("nama", "Garage"),
                "total_armada": garage_data.get("total_armada", 0),
                "position": garage_id
            }
        return {}
    
    def _get_tps_static_info(self, tps_id):
        if tps_id in self.shared.node_type:
            tps_data = self.shared.node_type[tps_id].get("tps_data", {})
            return {
                "node_id": tps_id,
                "nama": tps_data.get("nama", ""),
                "sampah_per_hari": tps_data.get("sampah_per_hari", 0),
                "position": tps_id,
                "dilayanin": tps_data.get("dilayanin", False)
            }
        return {}
    
    def _get_tpa_info(self, tpa_id):
        if tpa_id in self.shared.node_type:
            tpa_data = self.shared.node_type[tpa_id].get("tpa_data", {})
            return {
                "node_id": tpa_id,
                "nama": tpa_data.get("nama", "TPA"),
                "position": tpa_id
            }
        return {}
    
    def get_all_garages(self):
        return self.known_garages
    
    def get_all_tps(self):
        return self.known_tps
    
    def get_all_tpa(self):
        return self.known_tpa
    
    def get_shortest_path(self, start, end):
        try:
            return nx.shortest_path(self.graph, start, end, weight="length")
        except:
            return None
    
    def get_route_distance(self, path):
        if not path or len(path) < 2:
            return 0
        
        total_dist = 0
        for i in range(len(path) - 1):
            edge_data = self.graph.get_edge_data(path[i], path[i+1])
            if edge_data:
                total_dist += edge_data[0].get('length', 0)
        return total_dist
    





    # ============== DISCOVERED/DYNAMIC KNOWLEDGE ==============
    def discover_slowdown(self, edge_id, slowdown_value):
        if edge_id not in self.discovered_slowdowns:
            self.discovered_slowdowns[edge_id] = {
                "slowdown": slowdown_value,
                "discovered_at": f"Day {self.shared.sim_day} {self.shared.sim_hour:02d}:{self.shared.sim_min:02d}",
                "times_encountered": 1
            }
            print(f"[KnowledgeModel] 🚨 DISCOVERED slowdown at {edge_id}: {slowdown_value} km/jam")
        else:
            self.discovered_slowdowns[edge_id]["times_encountered"] += 1
            
            if self.discovered_slowdowns[edge_id]["slowdown"] != slowdown_value:
                old_value = self.discovered_slowdowns[edge_id]["slowdown"]
                self.discovered_slowdowns[edge_id]["slowdown"] = slowdown_value
                self.discovered_slowdowns[edge_id]["updated_at"] = f"Day {self.shared.sim_day} {self.shared.sim_hour:02d}:{self.shared.sim_min:02d}"
                print(f"[KnowledgeModel] ⚠️ UPDATED slowdown at {edge_id}: {old_value} → {slowdown_value} km/jam")
    
    def get_slowdown(self, edge_id):
        if edge_id in self.discovered_slowdowns:
            return self.discovered_slowdowns[edge_id]["slowdown"]
        return None
    
    def get_all_slowdowns(self):
        return self.discovered_slowdowns
    
    def get_slowdown_count(self):
        return len(self.discovered_slowdowns)
    
    def discover_garbage(self, tps_id, sampah_kg, sim_time=None):
        current_time = f"Day {self.shared.sim_day} {self.shared.sim_hour:02d}:{self.shared.sim_min:02d}" if sim_time is None else sim_time
        
        if tps_id not in self.discovered_garbage:
            self.discovered_garbage[tps_id] = {
                "sampah_kg": sampah_kg,
                "last_check_time": current_time,
                "history": [sampah_kg]
            }
            print(f"[KnowledgeModel] DISCOVERED garbage at TPS {tps_id}: {sampah_kg:.2f} kg (at {current_time})")
        else:
            old_amount = self.discovered_garbage[tps_id]["sampah_kg"]
            self.discovered_garbage[tps_id]["sampah_kg"] = sampah_kg
            self.discovered_garbage[tps_id]["last_check_time"] = current_time
            self.discovered_garbage[tps_id]["history"].append(sampah_kg)
            print(f"[KnowledgeModel] UPDATED garbage at TPS {tps_id}: {sampah_kg:.2f} kg (was {old_amount:.2f} at {current_time})")
    
    def get_discovered_garbage(self, tps_id):
        if tps_id in self.discovered_garbage:
            return self.discovered_garbage[tps_id]["sampah_kg"]
        return None
    
    def get_garbage_history(self, tps_id):
        if tps_id in self.discovered_garbage:
            return self.discovered_garbage[tps_id]["history"]
        return []
    




    # ============== VEHICLE TRACKER ==============
    def update_vehicle_status(self, vehicle_id, status):
        self.all_vehicle_ids.add(vehicle_id)
        self.vehicle_statuses[vehicle_id] = {
            "status": status,
            "location": status.get("current_node"),
            "load": status.get("load", 0),
            "load_percentage": status.get("load_percentage", 0),
            "state": status.get("state"),
            "timestamp": f"Day {self.shared.sim_day} {self.shared.sim_hour:02d}:{self.shared.sim_min:02d}"
        }
    
    def get_vehicle_status(self, vehicle_id):
        return self.vehicle_statuses.get(vehicle_id, None)
    
    def assign_task(self, vehicle_id, task):
        self.vehicle_assignments[vehicle_id] = task
        print(f"[KnowledgeModel] ASSIGNED task to vehicle {vehicle_id}: {task}")
    
    def get_task(self, vehicle_id):
        return self.vehicle_assignments.get(vehicle_id, None)
    
    def clear_task(self, vehicle_id):
        if vehicle_id in self.vehicle_assignments:
            del self.vehicle_assignments[vehicle_id]
    


    # ============== AGENT QUERIES (SENSOR) ==============    
    def get_optimal_tps(self, current_pos, prefer_known=False):
        best_tps = None
        best_distance = float('inf')
        
        if prefer_known and self.discovered_garbage:
            for tps_id in self.discovered_garbage.keys():
                if tps_id in self.known_tps:
                    dist = self.get_route_distance(
                        self.get_shortest_path(current_pos, tps_id)
                    )
                    if dist < best_distance:
                        best_distance = dist
                        best_tps = tps_id
        
        if best_tps is None:
            for tps_id in self.TPS_nodes:
                dist = self.get_route_distance(
                    self.get_shortest_path(current_pos, tps_id)
                )
                if dist < best_distance:
                    best_distance = dist
                    best_tps = tps_id
        
        return best_tps

    def get_vehicles_by_state(self, state):
        return [
            vid for vid, status in self.vehicle_statuses.items()
            if status.get("state") == state
        ]

    def get_knowledge_summary(self):
        total_encounters = sum(
            data["times_encountered"] 
            for data in self.discovered_slowdowns.values()
        )
        
        return {
            "known_garages": len(self.known_garages),
            "known_tps": len(self.known_tps),
            "known_tpa": len(self.known_tpa),
            "discovered_slowdowns": len(self.discovered_slowdowns),
            "total_slowdown_encounters": total_encounters,
            "discovered_garbage": len(self.discovered_garbage),
            "active_vehicles": len(self.all_vehicle_ids),
            "vehicles_with_task": len(self.vehicle_assignments),
            "idle_vehicles": len(self.get_vehicles_by_state("idle")),
            "busy_vehicles": len(self.all_vehicle_ids) - len(self.get_vehicles_by_state("idle"))
        }
```
---

<br> 

# E. Demo

## 1. Cara Menjalankan Simulasi
a) Cek apakah pip sudah terpasang:

```bash
python -m pip --version
```

<br> 

b) Masuk ke virtual environment:
### Windows (PowerShell)

```bash
python -m venv venv
venv\Scripts\activate
```
### Linux (bash)

```bash
python3 -m venv venv
source venv/bin/activate
```

<br> 

c) Setelah environment aktif, jalankan kode berikut untuk menginstall library yang dibutuhkan: 

```bash
pip install numpy pandas scikit-learn matplotlib pygame osmnx
```

NOTE: Untuk Linux ubuntu, gunakan pygame-ce

<br> 

d) Kemudian ketik ini di terminal untuk menjalankan simulasi:

```bash
python -m src.start
```

---

<br> 


# F. Summary
Pada simulasi dan benchmark yang kami buat, meskipun lokasi serta data hanya mendekati dan tidak 100% sama dengan kondisi nyata. Program ini dapat mempermudah menentukan apakah sebuah rute pengambilan sampah sudah efisien atau tidak dengan cepat dan mudah jikalau ada perubahan kondisi karena simulasi menyiapkan cara yang mudah untuk mengedit environment jika dibutuhkan. Selain itu, simulasi ini juga dapat dilakukan tidak hanya di balikpapan, namun juga dapat menggunakan rute kota lain jika dibutuhkan dikarenakan adanya scrapper map yang dapat dengan mudah digunakan.

---

<br> 


# G. References

* Anuar, W. K., Lee, L. S., Seow, H.-V., & Pickl, S. (2021). A Multi-Depot Vehicle Routing Problem with Stochastic Road Capacity and Reduced Two-Stage Stochastic Integer Linear Programming Models for Rollout Algorithm. Mathematics, 9(13), 1572. https://doi.org/10.3390/math9131572.
* Pemerintah Kota Balikpapan Dinas Lingkungan Hidup. (2022). Kajian pool kendaraan pengangkutan sampah di Kota Balikpapan, Tahun 2022 (Laporan Akhir). Pemerintah Kota Balikpapan Dinas Lingkungan Hidup.,
* RRI. (2024, Januari 31). DLH Balikpapan atur ulang jadwal angkut sampah. rri.co.id. Diakses 13 Desember 2025, dari https://rri.co.id/lain-lain/537534/dlh-balikpapan-atur-ulang-jadwal-angkut-sampah
* Kementerian Pekerjaan Umum dan Perumahan Rakyat. (2019, Desember 19). Diresmikan Presiden, pembangunan TPA Sampah Manggar di Balikpapan terbaik di Indonesia. pu.go.id. Diakses 13 Desember 2025, dari https://pu.go.id/berita/diresmikan-presiden-pembangunan-tpa-sampah-manggar-di-balikpapan-terbaik-di-indonesia

---

