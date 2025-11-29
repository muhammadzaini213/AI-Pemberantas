# AI Developer Readme

Panduan lengkap untuk pengembang AI yang akan membangun logika *AI Controller* menggunakan modul **Vehicle (Actuator)** dan **KnowledgeModel (Sensor)** tanpa harus membuka kedua file berkali‑kali.

---

# 1. Architecture Overview

Simulasi menggunakan arsitektur **AI → Sensor → Actuator**:

* **AI Controller** = Otak yang mengambil keputusan.
* **KnowledgeModel (Sensor)** = Apa yang AI ketahui tentang dunia (pengetahuan terbatas).
* **Vehicle (Actuator)** = Truk pelaksana tanpa logika.
* **Environment** = Menghasilkan event (macet, peningkatan sampah) yang masuk ke sensor.

AI **tidak boleh** membaca keadaan sebenarnya secara langsung. Semua keputusan berbasis **pengetahuan sensor**.

---

# 2. What AI Can and Cannot Know

## ✔ AI Boleh Tahu (pengetahuan penuh)

* Struktur graf jalan (nodes, edges, panjang).
* Lokasi TPS, TPA, Garasi.
* Waktu simulasi.
* Status truk dari sensor (bukan dari vehicle langsung):

  * state, current_node, target_node, load, capacity, path, progress.
* Estimasi kemacetan berdasarkan riwayat truk.

## ❌ AI Tidak Boleh Tahu (hidden environment state)

* Sampah sebenarnya di TPS (kecuali setelah loading).
* Traffic real-time (kecuali saat truk stuck atau lewat).
* Waste rate asli TPS.

AI harus bekerja dengan **ketidakpastian**.

---

# 3. SENSOR MODEL — KnowledgeModel

## 3.1 Informasi TPS yang disimpan

Untuk setiap TPS:

```
{
  "waste_amount": None | ton (hanya diketahui setelah loading),
  "last_visit_time": float | None,
  "last_observed_waste": ton | None,
  "estimated_waste_rate": 10.0 ton/hour,
  "priority": 0.5,
  "visit_count": int,
  "total_waste_collected": float
}
```

### Fungsi penting:

* **estimate_tps_waste(tps, time)** → estimasi tonase sampah berdasarkan pengetahuan terbatas.
* **get_tps_priorities(time)** → mengembalikan list prioritas TPS.
* **process_event(event, time)** → sensor update ketika:

  * loading_complete
  * unloading_complete
  * stuck
  * arrived
* **update_vehicle_status(vehicle)** → sensor membaca keadaan truk.
* **get_all_vehicle_status()** → sumber data utama AI untuk memantau truk.
* **get_traffic_factor(edge)** → estimasi kemacetan (0–1).

---

# 4. ACTUATOR MODEL — Vehicle

## 4.1 State Mesin Truk

* `Idle`
* `Moving`
* `Loading`
* `Unloading`
* `Stuck`
* `Standby`

## 4.2 Perintah yang dapat diberikan AI

Semua command masuk lewat:

```
vehicle.execute_command({ ... })
```

Format command:

```
{
  "action": "move_to" | "load" | "unload" | "standby",
  "target": node_id (optional),
  "duration": float (optional),
  "tps_node": node_id (optional, load)
}
```

### Aksi dan efeknya:

* **move_to(target_node)** → truk membuat rute otomatis via shortest path.
* **load(duration, tps_node)** → mulai loading (AI harus menentukan durasi).
* **unload(duration)** → buang ke TPA.
* **standby** → truk berhenti total.

## 4.3 Informasi status yang diberikan sensor ke AI

Output dari `vehicle.get_status()`:

```
{
  "id": int,
  "state": "Idle" | "Moving" | ...,
  "current_node": node,
  "target_node": node | None,
  "current_load": ton,
  "capacity": ton,
  "assigned_tps": node | None,
  "progress": 0–1,
  "path": [nodes]
}
```

---

# 5. Event System

Vehicle menghasilkan event berikut:

* **arrived** → truk tiba di node.
* **loading_complete** → sensor mengetahui jumlah sampah TPS.
* **unloading_complete** → statistik TPA bertambah.
* **stuck** → sensor mengetahui ada kemacetan.
* **unstuck** → truk kembali bergerak.

Semua event masuk ke sensor melalui:

```
knowledge.process_event(event, current_time)
```

---

# 6. Alur Lengkap Kerja AI Controller

1. Sensor update status truk
2. AI membaca **knowledge_model.vehicle_status**
3. AI membaca **prioritas TPS**, **estimasi traffic**, dan **estimasi TPS**
4. AI memilih truk mana yang idle dan memberi command
5. Vehicle mengeksekusi command
6. Event muncul → masuk ke sensor → pengetahuan berubah
7. AI loop kembali ke langkah 1

AI hanya mengirim command, tidak boleh memaksa perubahan state internal truk.

---

# 7. Tabel Aksi & Observasi untuk AI

## 7.1 Aksi yang bisa dilakukan AI

| Aksi      | Parameter          | Efek                                                       |
| --------- | ------------------ | ---------------------------------------------------------- |
| `move_to` | target node        | Truk bergerak ke node tersebut                             |
| `load`    | duration, tps_node | Truk mengambil sampah; sensor dapat observasi waste aktual |
| `unload`  | duration           | Truk membuang sampah ke TPA                                |
| `standby` | –                  | Truk berhenti sementara                                    |

## 7.2 Observasi yang bisa diterima AI

| Observasi           | Sumber | Keterangan                           |
| ------------------- | ------ | ------------------------------------ |
| `vehicle_status`    | sensor | posisi, path, progress, state        |
| `tps_knowledge`     | sensor | estimasi & observasi terakhir TPS    |
| `traffic_knowledge` | sensor | apakah pernah macet di edge tertentu |
| `loading_complete`  | event  | AI dapat update sampah aktual        |
| `stuck`             | event  | AI tahu edge sedang macet            |

---

# 8. Best Practices untuk Membuat AI

## 8.1 Hindari logika omniscient (serba tahu)

Gunakan hanya data dari **sensor**, bukan internal engine.

## 8.2 Gunakan priority system

Gabungkan faktor:

* estimasi sampah
* waktu sejak kunjungan terakhir
* jarak truk idle
* traffic factor

## 8.3 Perhatikan ketidakpastian

TPS baru pertama kali didatangi = unknown → treat as high priority.

## 8.4 Buat objective function Anda sendiri

Misal:

* memaksimalkan sampah terangkut per jam
* meminimalkan jarak tempuh
* mengurangi truk idle
* mengurangi tps overflow

AI bebas mengimplementasikan strategi kompleks selama hanya menggunakan data sensor.

---

# 9. Contoh Cicilan Logika AI (pseudocode)

```
for truck in idle_trucks:
    priorities = sensor.get_tps_priorities(time)
    best = choose_tps_considering_distance_and_traffic(truck, priorities)
    send move_to TPS

if truck arrives TPS:
    send load(duration=5, tps_node)

if truck is full:
    send move_to TPA

if truck arrives TPA:
    send unload(duration=3)
```

---

# 10. Kesimpulan

Dokumen ini memberikan seluruh informasi yang dibutuhkan AI untuk:

* mengetahui apa yang IA bisa lihat
* mengetahui apa yang IA bisa lakukan
* mengontrol truk sepenuhnya tanpa membuka modul Vehicle/Sensor lagi
* membangun objective function sendiri

Jika membutuhkan contoh implementasi AI Controller, minta saja: **"buatkan template AIController"**.
