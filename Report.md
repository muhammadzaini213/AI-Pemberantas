# Simulasi Agen Koordinator Truk Sampah Menggunakan Matheuristic Rollout dalam Kondisi Uncertain (Stochastic) Kota Balikpapan

---

<img width="561" height="594" alt="image" src="https://github.com/user-attachments/assets/10cf8615-dd3a-4a1e-b4dc-1877612061b0" />


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
<img width="356" height="339" alt="image" src="https://github.com/user-attachments/assets/c7a2211f-970c-46d1-80cf-3a46c234951c" />
<img width="757" height="922" alt="image" src="https://github.com/user-attachments/assets/5cac2fc1-c741-4c3c-a53c-f5077c973d3c" />

NOTE: Dikarenakan terdapat 73 TPS, kami menghomogenkan seluruh data dengan mengambil rata-rata dari seluruh TPS dan memberikannya interval ±30% randomisasi agar dapat lebih fokus ke proses pengembangan AI.

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
Metode rollout dengan teknik matheuristic yang bertujuan untuk meningkatkan kualitas keputusan dalam masalah sequential decision-making di lingkungan yang stochastic. Rollout ini bekerja dengan memanfaatkan base policy atau keputusan cepat dan sederhana sebagai kebijakan awal, lalu melakukan evaluasi ke depan (look-ahead) untuk memilih tindakan yang lebih baik daripada keputusan dasar sebelumnya. Setiap aksi yang dihitung nilai minimum berdasarkan objective function yang ada kemudian aksi dengan nilai minimum tersebut akan di eksekusi langsung.

Peningkatan keputusan terjadi karena Rollout tidak hanya berusaha melihat kondisi saat ini, tetapi juga memprediksi dampak tindakan pada beberapa langkah ke depan terutama pada kondisi yang berubah-ubah dari fluktuasi volume sampah yang tidak selalu diketahui

Kemudian di tahap eksekusi rute, sistem menggunakan ```shortest path``` dari ```OSMnx``` untuk menentukan jalur perjalanan truk pada jaringan jalan yang dapat diberikan pengecualian. Namun, aspek ini tidak menjadi fokus utama penelitian karena pathfinding hanya berfungsi sebagai komponen teknis pendukung. Fokus utama simulasi adalah pada multi-target, multi-instance decision-making, yaitu bagaimana agen truk mengambil keputusan rute dan prioritas TPS secara adaptif melalui mekanisme Rollout dan tidak melakukan tabrakan tugas kecuali dibutuhkan.

<br> 

## 2. Objective Function
Untuk setiap TPS \( t \), skor dihitung sebagai:

Skor(t) = W_d * (1 / (d(t) + 100)) + W_g * (g(t) / 1000)

- \( d(t) \): jarak kendaraan ke TPS  
- \( g(t) \): jumlah sampah di TPS  
- \( W_d \): bobot jarak (`DISTANCE_WEIGHT`)  
- \( W_g \): bobot sampah (`GARBAGE_WEIGHT`)

- TPS dengan skor terbesar akan dipilih  
- TPS dengan sampah ≤ 10 kg tidak dipertimbangkan  
- TPS yang terlalu jauh atau tidak memiliki jalur aman diabaikan

Hal ini bertujuan untuk memaksimalkan jumlah pengambilan sampah dengan jarak tempuh sekecil mungkin

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

#### b) Volume Sampah TPS Tidak Diketahui Sebelum Truk Tiba

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

```text
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

##### b) Truck data model

```text
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
WIDTH = 1000
HEIGHT = 600
CAM_SPEED = 10
MAX_FPS = 60

# ================== TEST SETUP ==================
GRAPH_FILE = "./data/simpl_balikpapan_timur_drive.graphml"


# ================== VEHICLE ==================
VEHICLE_SPEED = 600
VEHICLE_CAP = 30000


# ================== SHIFT SETTINGS (00:00 WITH INTEGER 0) ==================
SIM_START = 1
SHIFT_START = 1
SHIFT_END = 13
TIME_OFFSET = 17

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

##### a). Folder Structure
```
root/
├── data/             # Dataset AI
├── scrapper/         # Script untuk mengambil dataset graphml
├── src/              # Program utama untuk simulasi (pygame)
    ├── classes/
        ├── ai_model.py           # AIModel dimana semua keputusan diambil
        ├── knowledge.py          # KnowledgeModel tempat menyimpan informasi yang dimiliki
        └── vehicle.py            # Actuator dan Sensor dari truk sampah
    ├── utils/
        ├── controls.py           # Controller kamera di simulation
        ├── nodes.py              # Node Generator berdasarkan data yang ada
        ├── shared.py             # Tempat menyimpan data runtime
        ├── timesync.py           # Time accelerator dan jam simulasi
        └── viewer.py             # Renderer simulation
    ├── environment.py        # Data data environment dasar seperti ukuran window, truk, jam aktif, dan warna node
    ├── simulation.py         # Simulation runner
    └── start.py              # Full Runner
  
├── window/               # Window Tkinter untuk map editor
├── Report.md             # Laporan ini
└── README.md             # Dokumentasi utama proyek
```

<br>

##### b). Implementation Flow
Sebelum simulasi dijalankan, akan dilakukan persiapan visual, nodes, vehicle(sensor & actuator), dan model yang digunakan 
```python
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

    knowledge_model = KnowledgeModel(GRAPH, shared, TPS_nodes, TPA_nodes, GARAGE_nodes)
    shared.knowledge_model = knowledge_model

    ai_model = AIModel(knowledge_model, shared)
    shared.ai_model = ai_model
        
    running = True
    shared.paused = True
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

<br>

## 2. Ilustration


https://github.com/user-attachments/assets/0b51bb76-1750-4d9b-bdc2-7cc09d0e203e


<br>

## 3. Result

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

