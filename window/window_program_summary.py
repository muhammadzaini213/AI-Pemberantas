import tkinter as tk
from tkinter import ttk

def window_program_summary():
    content = tk.Frame(window, bg="#E8E8E8")
    content.pack(pady=10, fill="both")
    
    def row(label, widget, r):
        tk.Label(content, text=label, bg="#E8E8E8", anchor="w").grid(row=r, column=0, padx=10, pady=5, sticky="w")
        widget.grid(row=r, column=1, padx=10, pady=5, sticky="w")

    # FPS
    fps_entry = ttk.Entry(content, width=12)
    fps_entry.insert(0, "0")
    row("FPS:", fps_entry, 0)

    # Jam simulasi - Frame untuk input jam dan tanggal
    time_frame = ttk.Frame(content)
    
    # Input jam KU limit sampe 23 aja
    hour_var = tk.StringVar(value="08")
    hour_spinbox = ttk.Spinbox(
        time_frame, 
        from_=0, 
        to=23, 
        width=3, 
        textvariable=hour_var, 
        format="%02.0f",
        wrap=True
    )
    
    # Input menit ampe 59
    minute_var = tk.StringVar(value="00")
    minute_spinbox = ttk.Spinbox(
        time_frame, 
        from_=0, 
        to=59, 
        width=3, 
        textvariable=minute_var, 
        format="%02.0f",
        wrap=True
    )
    
    # hari cuman 365
    day_var = tk.StringVar(value="1")
    day_spinbox = ttk.Spinbox(
        time_frame, 
        from_=1, 
        to=365, 
        width=5, 
        textvariable=day_var
    )
    
    # Pack widgets dalam frame
    hour_spinbox.pack(side="left")
    ttk.Label(time_frame, text=":").pack(side="left", padx=2)
    minute_spinbox.pack(side="left")
    ttk.Label(time_frame, text="| Hari ke-").pack(side="left", padx=(10,0))
    day_spinbox.pack(side="left")
    
    row("Jam simulasi:", time_frame, 1)

    # Simulation speed
    speed_var = tk.StringVar(value="1x")
    speed_box = ttk.Combobox(
        content, 
        textvariable=speed_var,
        values=["0.25x", "0.5x", "1x", "2x", "4x"], 
        width=10, 
        state="readonly"
    )
    row("Simulation speed:", speed_box, 2)

    # Pause checkbox
    pause_var = tk.BooleanVar()
    pause_check = ttk.Checkbutton(content, text="Pause Simulasi", variable=pause_var)
    pause_check.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="w")

    # Informasi statistik dengan input angka
    stats_frame = ttk.Frame(content)
    stats_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky="w")
    
    # Dictionary untuk menyimpan variabel dan entry widgets
    stats_entries = {}
    stats_data = [
        ("Jumlah Node:", "node", "0"),
        ("Jumlah Edge:", "edge", "0"), 
        ("Jumlah TPA:", "tpa", "0"),
        ("Jumlah TPS:", "tps", "0"),
        ("Jumlah Truk:", "truk", "0")
    ]
    
    # Fungsi validasi angka saja
    def validate_numeric_input(P):
        if P == "" or P.isdigit():
            return True
        return False
    
    vcmd = (content.register(validate_numeric_input), '%P')
    
    for i, (label_text, key, default_value) in enumerate(stats_data):
        # Label
        ttk.Label(stats_frame, text=label_text).grid(row=i, column=0, sticky="w", padx=(0, 10))
        
        # Entry untuk input angka
        var = tk.StringVar(value=default_value)
        entry = ttk.Entry(
            stats_frame, 
            width=8, 
            textvariable=var,
            validate="key",
            validatecommand=vcmd
        )
        entry.grid(row=i, column=1, sticky="w")
        
        stats_entries[key] = {"var": var, "entry": entry}

    # Refresh button
    refresh_btn = ttk.Button(content, text="Refresh Simulasi")
    refresh_btn.grid(row=5, column=0, columnspan=2, padx=10, pady=10)

    # Fungsi untuk validasi manual
    def validate_time():
        try:
            hour = int(hour_var.get())
            if hour < 0 or hour > 23:
                hour_var.set("08")
        except:
            hour_var.set("08")
        
        try:
            minute = int(minute_var.get())
            if minute < 0 or minute > 59:
                minute_var.set("00")
        except:
            minute_var.set("00")
        
        try:
            day = int(day_var.get())
            if day < 1 or day > 365:
                day_var.set("1")
        except:
            day_var.set("1")

    # Bind validation events
    hour_spinbox.bind('<FocusOut>', lambda e: validate_time())
    minute_spinbox.bind('<FocusOut>', lambda e: validate_time())
    day_spinbox.bind('<FocusOut>', lambda e: validate_time())

    # Fungsi untuk mendapatkan nilai statistik
    def get_stats_values():
        return {
            "node": int(stats_entries["node"]["var"].get() or 0),
            "edge": int(stats_entries["edge"]["var"].get() or 0),
            "tpa": int(stats_entries["tpa"]["var"].get() or 0),
            "tps": int(stats_entries["tps"]["var"].get() or 0),
            "truk": int(stats_entries["truk"]["var"].get() or 0)
        }

    # Fungsi untuk mendapatkan waktu simulasi
    def get_simulation_time():
        return f"{hour_var.get()}:{minute_var.get()}", day_var.get()

    # Kembalikan kedua fungsi agar bisa diakses dari luar
    return get_simulation_time, get_stats_values

# Contoh penggunaan
if __name__ == "__main__":
    window = tk.Tk()
    window.title("Program Summary")
    
    # Panggil fungsi dan dapatkan kedua fungsi yang dikembalikan
    get_simulation_time, get_stats_values = window_program_summary()
    
    # Contoh cara menggunakan nilai
    def print_values():
        jam, hari = get_simulation_time()
        stats = get_stats_values()
        print(f"Jam: {jam}, Hari ke-{hari}")
        print(f"Statistik: {stats}")
    
    print_btn = ttk.Button(window, text="Print Values", command=print_values)
    print_btn.pack(pady=10)
    
    window.mainloop()