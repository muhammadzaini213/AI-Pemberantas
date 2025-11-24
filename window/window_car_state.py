import tkinter as tk
from tkinter import ttk  # Import ttk untuk Dropdown

# ================ UI ================ 
root = tk.Tk()
root.title("Car State - Truk Sampah Balikpapan")
root.geometry("350x450")

# Judul
header = tk.Label(root, text="CAR STATE EDITOR", font=("Arial", 12, "bold"))
header.grid(row=0, column=0, columnspan=2, pady=15)

# --- Form Input ---

# 1. ID Kendaraan
tk.Label(root, text="ID Kendaraan:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
entry_id = tk.Entry(root)
entry_id.grid(row=1, column=1, padx=10, pady=5)

# 2. State (Dropdown)
tk.Label(root, text="State:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
# Opsi dropdown sesuai logika truk sampah
state_options = ["Idle", "Moving", "Loading", "Unloading", "Maintenance"]
combo_state = ttk.Combobox(root, values=state_options, state="readonly")
combo_state.current(0) # Default pilih 'Idle'
combo_state.grid(row=2, column=1, padx=10, pady=5)

# 3. Speed (Input km/j)
tk.Label(root, text="Speed (km/j):").grid(row=3, column=0, sticky="w", padx=10, pady=5)
entry_speed = tk.Entry(root)
entry_speed.grid(row=3, column=1, padx=10, pady=5)

# 4. Total Perjalanan Hari Ini (Pengganti Bensin/Fitness Function)
tk.Label(root, text="Trip Hari Ini (km):").grid(row=4, column=0, sticky="w", padx=10, pady=5)
entry_daily = tk.Entry(root)
entry_daily.grid(row=4, column=1, padx=10, pady=5)

# 5. Total Perjalanan Semua (Odometer)
tk.Label(root, text="Total Odometer (km):").grid(row=5, column=0, sticky="w", padx=10, pady=5)
entry_total = tk.Entry(root)
entry_total.grid(row=5, column=1, padx=10, pady=5)

# 6. Angkutan Sekarang (Muatan kg)
tk.Label(root, text="Muatan (kg):").grid(row=6, column=0, sticky="w", padx=10, pady=5)
entry_load = tk.Entry(root)
entry_load.grid(row=6, column=1, padx=10, pady=5)

# 6. Angkutan Max (Muatan kg)
tk.Label(root, text="Muatan maksimum (kg):").grid(row=7, column=0, sticky="w", padx=10, pady=5)
entry_load = tk.Entry(root)
entry_load.grid(row=7, column=1, padx=10, pady=5)

# 8. Node Tujuan (String ID TPS/TPA)
tk.Label(root, text="Node Tujuan:").grid(row=8, column=0, sticky="w", padx=10, pady=5)
entry_target = tk.Entry(root)
entry_target.grid(row=8, column=1, padx=10, pady=5)

# --- Output & Tombol ---

# Output Label (Status Bar)
output_label = tk.Label(root, text="Ready...", fg="blue")
output_label.grid(row=10, column=0, columnspan=2, pady=15)

# Button Save
button = tk.Button(root, text="Simpan Data Truk", bg="#dddddd")
button.grid(row=9, column=0, columnspan=2, pady=10, sticky="ew", padx=10)


# ================ GETTER ==============
def get_car_data():
    """
    Mengambil semua data dari form input dan menjadikannya Dictionary.
    Dictionary ini nanti yang dikirim ke Multiagent System.
    """
    data = {
        "id": entry_id.get(),
        "state": combo_state.get(),
        "speed": entry_speed.get(),
        "daily_dist": entry_daily.get(), # Penting untuk Genetic Algorithm (Fitness)
        "total_dist": entry_total.get(),
        "load": entry_load.get(),
        "target": entry_target.get()
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
    data = get_car_data()
    
    # Validasi sederhana (ID tidak boleh kosong)
    if data["id"].strip() == "":
        set_output("Error: ID Kendaraan wajib diisi!", is_error=True)
        return

    # Simulasi penyimpanan data ke sistem Multiagent
    # Di sini nanti logika Genetic Algorithm membaca 'daily_dist'
    print(f"--- Data Disimpan ke Sistem ---")
    print(f"Agent ID: {data['id']}")
    print(f"Fitness Cost (Jarak): {data['daily_dist']} km")
    print(f"Target Next: {data['target']}")
    
    set_output(f"Sukses! Data {data['id']} berhasil disimpan.")

# Hubungkan tombol dengan fungsi logic
button.config(command=on_save_click)


# ================ RUN APP ==============
root.mainloop()
