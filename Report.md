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

<br> 

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

Cara menjalankan skenario dynamic routing, logging hasil, visualisasi, dan debugging.

Tambahkan potongan kode dengan syntax highlighting agar tampak profesional.

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
Pada simulasi dan benchmark yang kami buat, meskipun lokasi serta data hanya mendekati dan tidak 100% sama dengan kondisi 

---

<br> 


# G. References

* Anuar, W. K., Lee, L. S., Seow, H.-V., & Pickl, S. (2021). A Multi-Depot Vehicle Routing Problem with Stochastic Road Capacity and Reduced Two-Stage Stochastic Integer Linear Programming Models for Rollout Algorithm. Mathematics, 9(13), 1572. https://doi.org/10.3390/math9131572.
* Pemerintah Kota Balikpapan Dinas Lingkungan Hidup. (2022). Kajian pool kendaraan pengangkutan sampah di Kota Balikpapan, Tahun 2022 (Laporan Akhir). Pemerintah Kota Balikpapan Dinas Lingkungan Hidup.,
* RRI. (2024, Januari 31). DLH Balikpapan atur ulang jadwal angkut sampah. rri.co.id. Diakses 13 Desember 2025, dari https://rri.co.id/lain-lain/537534/dlh-balikpapan-atur-ulang-jadwal-angkut-sampah
* Kementerian Pekerjaan Umum dan Perumahan Rakyat. (2019, Desember 19). Diresmikan Presiden, pembangunan TPA Sampah Manggar di Balikpapan terbaik di Indonesia. pu.go.id. Diakses 13 Desember 2025, dari https://pu.go.id/berita/diresmikan-presiden-pembangunan-tpa-sampah-manggar-di-balikpapan-terbaik-di-indonesia

---

