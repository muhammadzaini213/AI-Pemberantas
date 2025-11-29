# 🗑️ Waste Management AI System

Sistem simulasi manajemen sampah dengan AI, kendaraan otonom, traffic control, dan real-time visualization menggunakan Pygame.

---

# 📂 Project Structure

```
src/
├── utils/
│   ├── controls.py            # Input & UI control handler
│   ├── helper.py              # Integration helpers
│   ├── shared.py              # Shared simulation state
│   ├── timesync.py            # Simulation clock utilities
│   ├── viewer.py              # Graph rendering & UI windows
│   └── __init__.py
│
├── ai.py                      # AI Controller (decision-making)
├── environment.py             # Constants & simulation configuration
├── sensor.py                  # Knowledge model (sensors)
├── simulation.py              # Main simulation loop
├── start.py                   # Entry point
└── vehicle.py                 # Vehicle actuator logic
```

---

# 🚦 Traffic System

Traffic **hanya diset manual via UI**, bukan otomatis.

### Kenapa?

* ❌ Auto-random congestion → glitching & flickering
* ✔ Manual control via edge-state window → stabil & predictable

### Cara Set Traffic:

1. Pause simulation
2. Klik edge yang ingin diubah
3. Set `delay` (parah) atau `slowdown` (menengah)
4. Unpause

### Alur Traffic:

```
User (UI)
   ↓
shared.edge_type
   ↓
Vehicle membaca → memperlambat
   ↓
Jika kendaraan stuck → AI mengobservasi
```

> **AI hanya mengamati traffic, tidak mengubahnya.**

---

# 🧠 Sistem AI & Knowledge Model

Sistem AI terdiri dari:

* **sensor.py** → Knowledge Model (mengumpulkan & memproses data dari simulasi)
* **ai.py** → AI Controller yang mengambil keputusan
* **helper.py** → Sinkronisasi data (TPS, TPA, traffic, garage, statistik)

### Data Node (shared.node_type):

```python
{
    node_id: {
        "tps": bool,
        "tpa": bool,
        "garage": bool,
        "tps_data": {...},
        "tpa_data": {...},
        "garage_data": {...}
    }
}
```

### Data Edge (shared.edge_type):

```python
{
    "node1-node2": {
        "delay": int,
        "slowdown": int
    }
}
```

---

# 🔄 Integration Flow

```
Simulation Loop
    ↓
Environment Update (sampah, traffic)
    ↓
Vehicle Update (posisi, event)
    ↓
Knowledge Model Update
    ↓
Integration Layer (loading, unloading, stuck)
    ↓
AI Decision Making (tiap 2 detik)
    ↓
Viewer Rendering (graph + UI)
```

---

# 🔧 Helper Functions

### TPS Waste

```python
get_tps_waste(shared, node)
sync_tps_waste(shared, node, value)
```

### Traffic

```python
get_traffic_factor(shared, edge)
sync_traffic(shared, edge, factor)
```

### Statistik

```python
update_garage_stats(...)
mark_tps_serviced(...)
add_tpa_waste(...)
add_tps_daily_waste(...)
```

---

# 🚚 Vehicle System

Vehicle memiliki:

* `id`, `car_id`
* `state` (Idle, Moving, Loading, Unloading, ReturnToGarage, dll)
* `current_load` dan `capacity`
* `route` & `path`
* `daily_dist`, `total_dist`

Semua kompatibel dengan **viewer.py**.

---

# 🤖 AI Decision Making

AI berjalan setiap `AI_DECISION_INTERVAL` detik, membaca:

* Prioritas TPS
* Traffic factor
* Status kendaraan
* Jam kerja

Lalu AI memilih:

* Kendaraan mana yang idle
* TPS mana yang harus dilayani
* Kapan kendaraan kembali ke garage

---

# ⚙ Editing AI

### Modifikasi parameter (environment.py):

```python
AI_DECISION_INTERVAL = 5.0
AI_PRIORITY_THRESHOLD = 0.5
SHIFT_START = 7
```

### Modifikasi algoritma (ai.py):

```python
def _assign_empty_vehicles_to_tps(...):
    pass
```

### Buat AI baru:

```python
class MyAI(AIController):
    ...
```

---

# 🧪 Testing Checklist

* [ ] Vehicles keluar dari garage saat shift start
* [ ] AI memilih TPS dengan prioritas tertinggi
* [ ] Loading/unloading berjalan
* [ ] Sampah TPS ↓ setelah loading
* [ ] Sampah TPA ↑ setelah unloading
* [ ] Traffic merah mempengaruhi kecepatan
* [ ] Vehicles stuck → AI detect
* [ ] Stats garage update
* [ ] Viewer menampilkan TPS/TPA/garage/traffic dengan benar
* [ ] AI berjalan tiap 2 detik

---

# 🛠 Troubleshooting

### Kendaraan tidak bergerak

```python
print(TPS_nodes)
print(shared.sim_hour)
print(shared.paused)
print(commands)
```

### Sampah tidak update

```python
print(get_tps_waste(shared, tps))
print(shared.node_type[tps]["tps_data"])
```

### AI tidak assign task

```python
print(knowledge.get_tps_priorities(time))
print([v for v in vehicles if v.state == "Idle"])
```

---