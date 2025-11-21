## 📁 Struktur Folder Proyek

```
AI Pemberantas/
├── data/                         # Dataset AI
├── notebooks/
│   └── tumbal.ipynb              # Notebook untuk tumbal & eksperimen
├── src/
│   ├── preprocessing.py          # Script preprocessing data
│   ├── model.py                  # Script model AI
│   └── utils.py                  # Fungsi utilitas tambahan
└── README.md                     # Dokumentasi utama proyek
```

---

## ⚙️ Cara Setup Lingkungan

Proyek ini dapat dijalankan meskipun Python terinstall **tanpa pip**. Berikut panduan lengkap untuk **memastikan pip tersedia** sebelum lanjut.

---

## 🛠️ Instalasi atau Pengecekan pip

### **Windows**

1. Cek apakah pip sudah terpasang:

```
python -m pip --version
```

2. Jika pip belum ada, jalankan:

```
python -m ensurepip --default-pip
```

3. Lalu update pip:

```
pip install --upgrade pip
```

Jika perintah `pip` tidak dikenali, coba pakai:

```
python -m pip install --upgrade pip
```

### **Linux (Ubuntu/Debian/Mint)**

Cek pip:

```
python3 -m pip --version
```

Jika belum ada, instal via APT:

```
sudo apt update
sudo apt install python3-pip
```

Atau gunakan ensurepip:

```
python3 -m ensurepip --default-pip
```

---

## 🐍 Membuat Virtual Environment

### **Windows (PowerShell)**

```
python -m venv venv
venv\Scripts\activate
```

### **Linux (bash)**

```
python3 -m venv venv
source venv/bin/activate
```

Setelah aktif, prompt terminal akan berubah menandakan environment sedang aktif.

---

## 📦 Instalasi Library Dasar

Setelah environment aktif, jalankan:

```
pip install numpy pandas scikit-learn matplotlib pygame osmnx
```

---

## ▶️ Menjalankan Notebook

### **Windows:**

```
jupyter notebook
```

### **Linux:**

```
jupyter notebook
```

Lalu buka file `notebooks/eksplorasi.ipynb`.

---
