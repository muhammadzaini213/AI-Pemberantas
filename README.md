# 📁 Struktur Folder Proyek

```
AI Pemberantas/
├── data/                 # Dataset AI
├── scrapper/             # Script untuk mengambil dataset graphml
├── src/                  # Program utama untuk simulasi (pygame)
├── visualization/        # Program simulasi perhitungan (matplotlib)
├── window/               # Window Tkinter untuk editor
└── README.md             # Dokumentasi utama proyek
```

---

# ⚙️ Cara Setup Environment

Proyek ini dapat dijalankan meskipun Python terinstall **tanpa pip**. Berikut panduan lengkap untuk memastikan **pip tersedia** sebelum melanjutkan.

---

## 🛠️ Instalasi atau Pengecekan pip

### **Windows**

1. Cek apakah pip sudah terpasang:

```bash
python -m pip --version
```

2. Jika pip belum ada, jalankan:

```bash
python -m ensurepip --default-pip
```

3. Lalu update pip:

```bash
python -m pip install --upgrade pip
```

> Jika perintah `pip` tidak dikenali, pakai:
>
> ```bash
> python -m pip install --upgrade pip
> ```

---

### **Linux (Ubuntu/Debian/Mint)**

1. Cek pip:

```bash
python3 -m pip --version
```

2. Jika belum ada, instal via APT:

```bash
sudo apt update
sudo apt install python3-pip
```

Atau gunakan `ensurepip`:

```bash
python3 -m ensurepip --default-pip
```

---

## 🐍 Membuat Virtual Environment

### **Windows (PowerShell)**

```bash
python -m venv venv
venv\Scripts\activate
```

### **Linux (bash)**

```bash
python3 -m venv venv
source venv/bin/activate
```

> Setelah aktif, prompt terminal akan berubah menandakan environment sedang aktif.

---

## 📦 Instalasi Library Dasar

Setelah environment aktif, jalankan:

```bash
pip install numpy pandas scikit-learn matplotlib pygame osmnx
```

---

## ▶️ Menjalankan Simulasi Real Time

### **Windows**

```bash
python -m src.start
```

### **Linux**

```bash
python3.12 -m src.start
```

---