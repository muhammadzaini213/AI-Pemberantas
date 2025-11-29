import tkinter as tk
from tkinter import ttk, messagebox


class ProgramSummaryWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Program Summary")
        self.root.geometry("450x420")
        self.root.configure(bg="#E8E8E8")
        
        self.on_refresh_callback = None

        content = tk.Frame(self.root, bg="#E8E8E8")
        content.pack(pady=10, fill="both")

        def row(label, widget, r):
            tk.Label(content, text=label, bg="#E8E8E8", anchor="w").grid(
                row=r, column=0, padx=10, pady=5, sticky="w"
            )
            widget.grid(row=r, column=1, padx=10, pady=5, sticky="w")

        self.fps_var = tk.StringVar(value="0")
        fps_entry = ttk.Entry(content, width=12, textvariable=self.fps_var, state="readonly")
        row("FPS:", fps_entry, 0)

        time_frame = ttk.Frame(content)

        self.hour_var = tk.StringVar(value="08")
        self.minute_var = tk.StringVar(value="00")
        self.day_var = tk.StringVar(value="1")

        hour_spinbox = ttk.Spinbox(
            time_frame, from_=0, to=23, width=3,
            textvariable=self.hour_var, format="%02.0f", wrap=True, state="readonly"
        )
        minute_spinbox = ttk.Spinbox(
            time_frame, from_=0, to=59, width=3,
            textvariable=self.minute_var, format="%02.0f", wrap=True, state="readonly"
        )
        day_spinbox = ttk.Spinbox(
            time_frame, from_=1, to=365, width=5,
            textvariable=self.day_var, state="readonly"
        )

        hour_spinbox.pack(side="left")
        ttk.Label(time_frame, text=":").pack(side="left", padx=2)
        minute_spinbox.pack(side="left")
        ttk.Label(time_frame, text="| Hari ke-").pack(side="left", padx=(10, 0))
        day_spinbox.pack(side="left")

        row("Jam simulasi:", time_frame, 1)

        self.speed_var = tk.StringVar(value="1x")
        speed_box = ttk.Combobox(
            content, textvariable=self.speed_var,
            values=["0.25x", "0.5x", "1x", "2x", "4x", "8x", "16x", "32x", "64x", "128x", "256x", "512x"],
            width=10, state="readonly"
        )

        speed_box.bind("<<ComboboxSelected>>", self.on_speed_change)

        row("Simulation speed:", speed_box, 2)

        self.pause_var = tk.BooleanVar()
        pause_check = ttk.Checkbutton(content, text="Pause Simulasi", variable=self.pause_var)
        pause_check.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        self.pause_var.trace_add("write", self.on_pause_change)

        stats_frame = ttk.Frame(content)
        stats_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        self.stats_entries = {}
        stats_data = [
            ("Jumlah Node:", "node", "0"),
            ("Jumlah Edge:", "edge", "0"),
            ("Jumlah TPA:", "tpa", "0"),
            ("Jumlah TPS:", "tps", "0"),
            ("Jumlah Truk:", "truk", "0"),
        ]

        def validate_numeric(P):
            return P.isdigit() or P == ""

        vcmd = (content.register(validate_numeric), "%P")

        for i, (label_text, key, default_value) in enumerate(stats_data):
            ttk.Label(stats_frame, text=label_text).grid(row=i, column=0, sticky="w", padx=(0, 10))

            var = tk.StringVar(value=default_value)
            entry = ttk.Entry(
                stats_frame, width=8, textvariable=var,
                validate="key", validatecommand=vcmd, state="readonly"
            )
            entry.grid(row=i, column=1, sticky="w")

            self.stats_entries[key] = var


        button_frame = ttk.Frame(content)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)

        refresh_btn = ttk.Button(button_frame, text="🔄 Refresh Simulasi", command=self.on_refresh)
        refresh_btn.pack(side="left", padx=5)

        save_btn = ttk.Button(button_frame, text="💾 Hard Save", command=self.on_hard_save)
        save_btn.pack(side="left", padx=5)

        hour_spinbox.bind("<FocusOut>", lambda e: self.validate_time())
        minute_spinbox.bind("<FocusOut>", lambda e: self.validate_time())
        day_spinbox.bind("<FocusOut>", lambda e: self.validate_time())


    # ============== GETTERS ==============
    def get_fps(self):
        return int(self.fps_var.get() or 0)

    def get_simulation_time(self):
        return f"{self.hour_var.get()}:{self.minute_var.get()}", int(self.day_var.get())

    def get_simulation_speed(self):
        return self.speed_var.get()

    def get_pause_state(self):
        return self.pause_var.get()

    def get_stats_values(self):
        return {
            key: int(var.get() or 0)
            for key, var in self.stats_entries.items()
        }

    # ============== SETTERS ==============
    def set_fps(self, value):
        self.fps_var.set(str(value))

    def set_simulation_time(self, hour, minute, day):
        self.hour_var.set(f"{int(hour):02d}")
        self.minute_var.set(f"{int(minute):02d}")
        self.day_var.set(str(day))

    def set_simulation_speed(self, value):
        self.speed_var.set(value)

    def set_pause_state(self, value: bool):
        self.pause_var.set(bool(value))

    def set_stat(self, key, value):
        if key in self.stats_entries:
            self.stats_entries[key].set(str(value))


    # ============== LOGIC ==============
    def validate_time(self):
        try:
            h = int(self.hour_var.get())
            if not 0 <= h <= 23:
                self.hour_var.set("08")
        except:
            self.hour_var.set("08")

        try:
            m = int(self.minute_var.get())
            if not 0 <= m <= 59:
                self.minute_var.set("00")
        except:
            self.minute_var.set("00")

        try:
            d = int(self.day_var.get())
            if not 1 <= d <= 365:
                self.day_var.set("1")
        except:
            self.day_var.set("1")

    def attach_state(self, shared):
        self.shared = shared
        self.root.after(200, self.update_from_shared)

    def set_refresh_callback(self, callback):
        self.on_refresh_callback = callback

    def update_from_shared(self):
        if not hasattr(self, "shared"): 
            return

        self.set_fps(self.shared.fps)

        self.set_simulation_time(
            self.shared.sim_hour,
            self.shared.sim_min,
            self.shared.sim_day
        )

        speed_map = {
            0.25: "0.25x",
            0.5: "0.5x",
            1.0: "1x",
            2.0: "2x",
            4.0: "4x",
        }
        if self.shared.speed in speed_map:
            self.set_simulation_speed(speed_map[self.shared.speed])

        self.set_pause_state(self.shared.paused)

        if hasattr(self.shared, "node_count"):
            self.set_stat("node", self.shared.node_count)
        if hasattr(self.shared, "edge_count"):
            self.set_stat("edge", self.shared.edge_count)
        if hasattr(self.shared, "num_tps"):
            self.set_stat("tps", self.shared.num_tps)
        if hasattr(self.shared, "num_tpa"):
            self.set_stat("tpa", self.shared.num_tpa)
        if hasattr(self.shared, "get_num_vehicle"):
            self.set_stat("truk", self.shared.total_vehicles)

        self.root.after(1, self.update_from_shared)


    def on_refresh(self):
        self.validate_time()
        
        import src.vehicle
        src.vehicle._vehicle_id_counter = 0
        
        if hasattr(self, "shared"):
            self.shared.node_type = {}
            self.shared.edge_type = {}
            self.shared.vehicles = []
            self.shared.sim_hour = int(self.hour_var.get())
            self.shared.sim_min = int(self.minute_var.get())
            self.shared.sim_day = int(self.day_var.get())
            
            speed_str = self.speed_var.get()
            self.shared.speed = float(speed_str.replace("x", ""))
            
            self.shared.paused = bool(self.pause_var.get())
        
        print("=== REFRESH SIMULASI ===")
        print("Waktu:", self.get_simulation_time())
        print("Speed:", self.get_simulation_speed())
        print("Pause:", self.get_pause_state())
        
        # Panggil callback refresh jika ada
        if self.on_refresh_callback:
            print("[ProgramSummaryWindow] Calling refresh callback...")
            self.on_refresh_callback()
        else:
            messagebox.showwarning("Warning", "Refresh callback belum ter-set!")

    def on_hard_save(self):
        if not hasattr(self, "shared"):
            messagebox.showwarning("Warning", "Shared state belum ter-attach!")
            return

        try:
            # Panggil save_all_data dari SharedState
            success = self.shared.save_all_data()
            
            if success:
                messagebox.showinfo(
                    "Save Successful", 
                    f"Data berhasil disimpan ke:\n\n"
                    f"📄 {self.shared.node_data_file}\n"
                    f"📄 {self.shared.edge_data_file}"
                )
            else:
                messagebox.showerror(
                    "Save Failed", 
                    "Gagal menyimpan data!\nCek console untuk detail error."
                )
        except Exception as e:
            messagebox.showerror("Error", f"Error saat menyimpan data:\n{str(e)}")

    def on_speed_change(self, event=None):
        text = self.speed_var.get()
        speed_value = float(text.replace("x", ""))
        if hasattr(self, "shared"):
            self.shared.speed = speed_value

    def on_pause_change(self, *args):
        if hasattr(self, "shared"):
            self.shared.paused = bool(self.pause_var.get())

    # ============================================================
    #                       MAIN LOOP
    # ============================================================
    def run(self):
        self.root.mainloop()