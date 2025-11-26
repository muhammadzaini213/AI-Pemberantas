import tkinter as tk
from tkinter import ttk

# ============================================
#                     UI
# ============================================

root = tk.Tk()
root.title("Program Summary")
root.geometry("450x380")
root.configure(bg="#E8E8E8")

content = tk.Frame(root, bg="#E8E8E8")
content.pack(pady=10, fill="both")

def row(label, widget, r):
    tk.Label(content, text=label, bg="#E8E8E8", anchor="w").grid(row=r, column=0, padx=10, pady=5, sticky="w")
    widget.grid(row=r, column=1, padx=10, pady=5, sticky="w")


# ------------ FPS ------------
fps_var = tk.StringVar(value="0")
fps_entry = ttk.Entry(content, width=12, textvariable=fps_var)
row("FPS:", fps_entry, 0)


# ------------ Simulation Time ------------
time_frame = ttk.Frame(content)

hour_var = tk.StringVar(value="08")
hour_spinbox = ttk.Spinbox(
    time_frame, from_=0, to=23, width=3,
    textvariable=hour_var, format="%02.0f", wrap=True
)

minute_var = tk.StringVar(value="00")
minute_spinbox = ttk.Spinbox(
    time_frame, from_=0, to=59, width=3,
    textvariable=minute_var, format="%02.0f", wrap=True
)

day_var = tk.StringVar(value="1")
day_spinbox = ttk.Spinbox(
    time_frame, from_=1, to=365, width=5,
    textvariable=day_var
)

hour_spinbox.pack(side="left")
ttk.Label(time_frame, text=":").pack(side="left", padx=2)
minute_spinbox.pack(side="left")
ttk.Label(time_frame, text="| Hari ke-").pack(side="left", padx=(10,0))
day_spinbox.pack(side="left")

row("Jam simulasi:", time_frame, 1)


# ------------ Simulation Speed ------------
speed_var = tk.StringVar(value="1x")
speed_box = ttk.Combobox(
    content, textvariable=speed_var,
    values=["0.25x", "0.5x", "1x", "2x", "4x"],
    width=10, state="readonly"
)
row("Simulation speed:", speed_box, 2)


# ------------ Pause ------------
pause_var = tk.BooleanVar()
pause_check = ttk.Checkbutton(content, text="Pause Simulasi", variable=pause_var)
pause_check.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="w")


# ------------ Stats Input ------------
stats_frame = ttk.Frame(content)
stats_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky="w")

stats_entries = {}
stats_data = [
    ("Jumlah Node:", "node", "0"),
    ("Jumlah Edge:", "edge", "0"),
    ("Jumlah TPA:", "tpa", "0"),
    ("Jumlah TPS:", "tps", "0"),
    ("Jumlah Truk:", "truk", "0")
]

# Validasi angka
def validate_numeric_input(P):
    return P.isdigit() or P == ""

vcmd = (content.register(validate_numeric_input), '%P')

for i, (label_text, key, default_value) in enumerate(stats_data):
    ttk.Label(stats_frame, text=label_text).grid(row=i, column=0, sticky="w", padx=(0,10))

    var = tk.StringVar(value=default_value)
    entry = ttk.Entry(
        stats_frame, width=8,
        textvariable=var, validate="key",
        validatecommand=vcmd
    )
    entry.grid(row=i, column=1, sticky="w")

    stats_entries[key] = {"var": var, "entry": entry}


# ------------ Buttons ------------
refresh_btn = ttk.Button(content, text="Refresh Simulasi")
refresh_btn.grid(row=5, column=0, columnspan=2, pady=10)



# ============================================
#                   GETTERS
# ============================================

def get_fps():
    """Mengambil nilai FPS."""
    return int(fps_var.get() or 0)

def get_simulation_time():
    """Mengambil jam, menit, dan hari simulasi."""
    return f"{hour_var.get()}:{minute_var.get()}", int(day_var.get())

def get_simulation_speed():
    """Mengambil speed simulasi."""
    return speed_var.get()

def get_pause_state():
    """Mengambil status pause (True/False)."""
    return pause_var.get()

def get_stats_values():
    """Mengambil statistik jumlah objek."""
    return {
        "node": int(stats_entries["node"]["var"].get() or 0),
        "edge": int(stats_entries["edge"]["var"].get() or 0),
        "tpa": int(stats_entries["tpa"]["var"].get() or 0),
        "tps": int(stats_entries["tps"]["var"].get() or 0),
        "truk": int(stats_entries["truk"]["var"].get() or 0)
    }



# ============================================
#                   SETTERS
# ============================================

def set_fps(value):
    fps_var.set(str(value))

def set_simulation_time(hour, minute, day):
    hour_var.set(f"{int(hour):02d}")
    minute_var.set(f"{int(minute):02d}")
    day_var.set(str(day))

def set_simulation_speed(value):
    speed_var.set(value)

def set_pause_state(value: bool):
    pause_var.set(value)

def set_stat(key, value):
    if key in stats_entries:
        stats_entries[key]["var"].set(str(value))



# ============================================
#                  VALIDATION
# ============================================

def validate_time():
    """Validasi spinbox jam/menit/hari."""
    try:
        h = int(hour_var.get())
        if not 0 <= h <= 23:
            hour_var.set("08")
    except:
        hour_var.set("08")

    try:
        m = int(minute_var.get())
        if not 0 <= m <= 59:
            minute_var.set("00")
    except:
        minute_var.set("00")

    try:
        d = int(day_var.get())
        if not 1 <= d <= 365:
            day_var.set("1")
    except:
        day_var.set("1")


hour_spinbox.bind("<FocusOut>", lambda e: validate_time())
minute_spinbox.bind("<FocusOut>", lambda e: validate_time())
day_spinbox.bind("<FocusOut>", lambda e: validate_time())


# ============================================
#                EVENTS / LOGIC
# ============================================

def on_refresh_click():
    """Event tombol refresh."""
    validate_time()
    print("=== REFRESH SIMULASI ===")
    print("FPS:", get_fps())
    print("Waktu:", get_simulation_time())
    print("Speed:", get_simulation_speed())
    print("Pause:", get_pause_state())
    print("Stats:", get_stats_values())

refresh_btn.config(command=on_refresh_click)



# ============================================
#                  RUN APP
# ============================================

if __name__ == "__main__":
    root.mainloop()
