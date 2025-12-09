# Simulasi Agen Koordinator Truk Sampah Menggunakan Matheuristic Rollout dalam Kondisi Uncertain (Stochastic) Kota Balikpapan

---

<img width="1257" height="1053" alt="image" src="https://github.com/user-attachments/assets/2449c5cf-73ec-4114-bd37-168bc84d65a5" />


## Kelompok 10

| Nama              | NIM      |
| ----------------- | -------- |
| Muhammad Zaini    | 11241064 |
| Ahmad Rafif Rafi  | 11241006 |
| Mayoga Finanda    | 11241044 |
| Ferdianta Tarigan | 11241030 |

---

# A. Abstract
Nanti abstract belakangan

---

# B. Methods

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

## 2. Objective Function

Komponen fungsi objektif mencakup:

* minimisasi waktu tempuh
* minimisasi total perjalanan
* reduksi tingkat penumpukan TPS
* optimasi energi atau biaya operasional

Sertakan formulasi matematika dalam bentuk persamaan.

## 3. Knowledge Model

Struktur model pengetahuan dapat mencakup:

* representasi TPS
* kapasitas truk
* kondisi lalu lintas
* aturan pengambilan keputusan agen
* mekanisme pembaruan informasi secara real-time

---

# C. Implementation

### 1. Environment Setup
Pada sistem yang telah kami buat, kami menggunakan library pygame untuk melakukan visualisasi dan simulasi untuk environment. Dengan data ```.graphml``` yang diambil langsung dari ```openstreetmap.org``` melalui library osmnx yang tersedia di python.

Untuk menambahkan data TPA, TPS, Garasi, Mobil, dan Kemacetan, kami menyediakan map editor sehingga pengeditan dapat dilakukan dengan lebih leluasa dan mudah yang datanya akan disimpan dalam file ```.json```. Meskipun begitu, data yang cukup jarang diubah seperti kecepatan kendaraan, waktu shift, serta warna warna node dan edges, kami letakkan di ```src/environment.py```.


### 2. Data Modeling

##### a) Nodes data model

```
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

##### b) Edges data model

```
    edge_id: {
    "slowdown": float,
    "slowdown_start": int,
    "slowdown_end": int
    },
```

##### c) Truck data model

```
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

### 3. Rollout Algorithm Integration

Tunjukkan langkah demi langkah implementasi, mulai dari base policy, proses look ahead, hingga evaluasi state.

### 4. Simulation Engine

Cara menjalankan skenario dynamic routing, logging hasil, visualisasi, dan debugging.

Tambahkan potongan kode dengan syntax highlighting agar tampak profesional.

---

# D. Demo

## 1. Cara Menjalankan Simulasi
Cek apakah pip sudah terpasang:

```bash
python -m pip --version
```

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

Setelah environment aktif, jalankan kode berikut untuk menginstall library yang dibutuhkan: 

```bash
pip install numpy pandas scikit-learn matplotlib pygame osmnx
```

Kemudian ketik ini di terminal untuk menjalankan simulasi:
```bash
python -m src.start
```

---

# E. Summary

Tuliskan ringkasan yang berfokus pada:

* efektivitas Rollout dalam kondisi uncertain
* perbandingan dengan pendekatan deterministik
* implikasi kebijakan bagi manajemen sampah kota
* potensi pengembangan lanjutan

---

# F. References

* Anuar, W.K.; Lee, L.S.; Seow, H.-V.; Pickl, S. A Multi-Depot Vehicle Routing Problem with Stochastic Road Capacity and Reduced Two-Stage Stochastic Integer Linear Programming Models for Rollout Algorithm. Mathematics 2021, 9, 1572. https://doi.org/10.3390/math9131572.


---

