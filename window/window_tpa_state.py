import tkinter as tk

# ================ UI ================ 
root = tk.Tk()
root.title("TPA State - Sistem Sampah Balikpapan")
root.geometry("350x250") # Ukuran lebih kecil karena inputnya sedikit

# Judul
header = tk.Label(root, text="TPA STATE EDITOR", font=("Arial", 12, "bold"))
header.grid(row=0, column=0, columnspan=2, pady=15)

# --- Form Input ---

# 1. Nama TPA (Input Text)
tk.Label(root, text="Nama TPA:").grid(row=1, column=0, sticky="w", padx=15, pady=5)
entry_nama_tpa = tk.Entry(root, width=25)
entry_nama_tpa.insert(0, "TPA Manggar") # Default value agar praktis
entry_nama_tpa.grid(row=1, column=1, padx=10, pady=5)

# 2. Jumlah Sampah Terkumpul (Input Angka)
tk.Label(root, text="Sampah Terkumpul (kg):").grid(row=2, column=0, sticky="w", padx=15, pady=5)
entry_total_sampah = tk.Entry(root, width=25)
entry_total_sampah.insert(0, "0") # Default 0 kg
entry_total_sampah.grid(row=2, column=1, padx=10, pady=5)

# --- Output & Tombol ---

# Output Label (Status Bar)
output_label = tk.Label(root, text="Ready...", fg="blue")
output_label.grid(row=4, column=0, columnspan=2, pady=15)

# Button Save
button = tk.Button(root, text="Update Status TPA", bg="#dddddd")
button.grid(row=3, column=0, columnspan=2, pady=10, sticky="ew", padx=15)


# ================ GETTER ==============
def get_tpa_data():
    """
    Mengambil data TPA dari form input.
    Data ini nanti digunakan untuk mengecek kapasitas TPA (jika ada batasan).
    """
    data = {
        "nama": entry_nama_tpa.get(),
        "total_sampah": entry_total_sampah.get()
    }
    return data


# ================ SETTER ==============
def set_output(text, is_error=False):
    """
    Mengupdate status label di bagian bawah window
    """
    color = "red" if is_error else "green"
    output_label.config(text=text, fg=color)


# ================ LOGIC / EVENTS ==============
def on_save_click():
    data = get_tpa_data()
    
    # Validasi 1: Nama TPA tidak boleh kosong
    if data["nama"].strip() == "":
        set_output("Error: Nama TPA wajib diisi!", is_error=True)
        return

    # Validasi 2: Jumlah sampah harus berupa angka
    if not data["total_sampah"].isdigit():
        set_output("Error: Jumlah sampah harus angka!", is_error=True)
        return

    # Simulasi Logika:
    # Di sistem Multiagent nanti, angka ini akan bertambah otomatis
    # setiap kali Truk melakukan aksi 'DUMP' (buang muatan).
    
    print(f"--- Update TPA Manggar ---")
    print(f"Lokasi: {data['nama']}")
    print(f"Total Timbunan: {data['total_sampah']} kg")
    
    set_output(f"Sukses! Status {data['nama']} diperbarui.")

# Hubungkan tombol dengan fungsi logic
button.config(command=on_save_click)


# ================ RUN APP ==============
root.mainloop()
