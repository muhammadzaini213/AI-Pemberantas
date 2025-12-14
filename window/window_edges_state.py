import tkinter as tk
from tkinter import ttk

class EdgeStateWindow:
    def __init__(self, master=None):
        if master is None:
            self.root = tk.Tk()
        else:
            self.root = tk.Toplevel(master)

        self.root.title("Edges State Configuration")
        self.root.geometry("420x480")
        self.root.configure(bg="#ECF0F1")
        self.shared = None  # akan diattach nanti

        main_frame = tk.Frame(self.root, bg="#E8E8E8", padx=25, pady=25)
        main_frame.pack(fill="both", expand=True)

        title_label = tk.Label(main_frame, text="Edges State Settings",
                               font=("Arial", 13, "bold"),
                               bg="#F5F5F5", fg="#2C3E50")
        title_label.pack(anchor="w", pady=(0, 20))

        self.content_frame = tk.Frame(main_frame, bg="#FFFFFF", relief="flat", bd=1)
        self.content_frame.pack(fill="both", expand=True)

        # Edge ID
        tk.Label(self.content_frame, text="Edges ID:", font=("Arial", 10),
                 bg="#FFFFFF", anchor="w", width=20).grid(row=0, column=0, padx=20, pady=15, sticky="w")
        self.edge_id_var = tk.StringVar()
        tk.Entry(self.content_frame, textvariable=self.edge_id_var, width=15).grid(row=0, column=1, padx=20, pady=15, sticky="w")

        # Slowdown effect
        def create_input_row(parent, label_text, default_value, unit, from_val, to_val, row):
            tk.Label(parent, text=label_text, font=("Arial", 10),
                     bg="#FFFFFF", anchor="w", width=20).grid(row=row, column=0, padx=20, pady=15, sticky="w")

            input_frame = tk.Frame(parent, bg="#FFFFFF")
            input_frame.grid(row=row, column=1, padx=20, pady=15, sticky="w")

            var = tk.StringVar(value=default_value)
            spinbox = ttk.Spinbox(
                input_frame,
                from_=from_val,
                to=to_val,
                width=8,
                textvariable=var,
                format="%02.0f",
                font=("Arial", 9)
            )
            spinbox.pack(side="left")

            unit_label = tk.Label(input_frame, text=unit, font=("Arial", 9),
                                  bg="#FFFFFF", fg="#666666")
            unit_label.pack(side="left", padx=(8, 0))

            return var, spinbox

        self.slowdown_var, self.slowdown_spinbox = create_input_row(
            self.content_frame, "Efek perlambatan:", "0", "km/j", 0, 200, 1
        )

        # Time interval section
        ttk.Separator(self.content_frame, orient="horizontal") \
            .grid(row=2, column=0, columnspan=2, sticky="we", padx=20, pady=10)

        tk.Label(self.content_frame, text="⏰ Interval Kemacetan",
                 font=("Arial", 10, "bold"),
                 bg="#FFFFFF", fg="#2980B9").grid(row=3, column=0, columnspan=2, padx=20, pady=(10, 5))

        # Start hour
        tk.Label(self.content_frame, text="Jam mulai:", font=("Arial", 10),
                 bg="#FFFFFF", anchor="w", width=20).grid(row=4, column=0, padx=20, pady=8, sticky="w")
        
        start_frame = tk.Frame(self.content_frame, bg="#FFFFFF")
        start_frame.grid(row=4, column=1, padx=20, pady=8, sticky="w")
        
        self.start_hour_var = tk.StringVar(value="0")
        self.start_hour_spinbox = ttk.Spinbox(
            start_frame,
            from_=0,
            to=23,
            width=8,
            textvariable=self.start_hour_var,
            format="%02.0f",
            font=("Arial", 9)
        )
        self.start_hour_spinbox.pack(side="left")
        
        tk.Label(start_frame, text="(0-23)", font=("Arial", 9),
                bg="#FFFFFF", fg="#666666").pack(side="left", padx=(8, 0))

        # End hour
        tk.Label(self.content_frame, text="Jam selesai:", font=("Arial", 10),
                 bg="#FFFFFF", anchor="w", width=20).grid(row=5, column=0, padx=20, pady=8, sticky="w")
        
        end_frame = tk.Frame(self.content_frame, bg="#FFFFFF")
        end_frame.grid(row=5, column=1, padx=20, pady=8, sticky="w")
        
        self.end_hour_var = tk.StringVar(value="23")
        self.end_hour_spinbox = ttk.Spinbox(
            end_frame,
            from_=0,
            to=23,
            width=8,
            textvariable=self.end_hour_var,
            format="%02.0f",
            font=("Arial", 9)
        )
        self.end_hour_spinbox.pack(side="left")
        
        tk.Label(end_frame, text="(0-23)", font=("Arial", 9),
                bg="#FFFFFF", fg="#666666").pack(side="left", padx=(8, 0))

        # Info label
        self.info_label = tk.Label(self.content_frame, text="",
                                   font=("Arial", 8, "italic"),
                                   bg="#FFFFFF", fg="#7F8C8D", wraplength=300)
        self.info_label.grid(row=6, column=0, columnspan=2, padx=20, pady=(5, 10))

        ttk.Separator(self.content_frame, orient="horizontal") \
            .grid(row=7, column=0, columnspan=2, sticky="we", padx=20, pady=10)

        # Button
        button_frame = tk.Frame(self.content_frame, bg="#FFFFFF")
        button_frame.grid(row=8, column=0, columnspan=2, pady=15)

        self.apply_btn = ttk.Button(button_frame, text="Apply Settings", command=self.apply_settings, width=15)
        self.apply_btn.pack()

        # Bind events
        self.slowdown_spinbox.bind('<FocusOut>', lambda e: self.validate_inputs())
        self.start_hour_spinbox.bind('<<Increment>>', lambda e: self.update_info_label())
        self.start_hour_spinbox.bind('<<Decrement>>', lambda e: self.update_info_label())
        self.end_hour_spinbox.bind('<<Increment>>', lambda e: self.update_info_label())
        self.end_hour_spinbox.bind('<<Decrement>>', lambda e: self.update_info_label())
        self.start_hour_var.trace_add('write', lambda *args: self.update_info_label())
        self.end_hour_var.trace_add('write', lambda *args: self.update_info_label())

        self.update_info_label()

    # ============== SHARED ==============
    def attach_shared(self, shared):
        self.shared = shared
        shared.edge_state_window = self

    # ============== GETTERS ==============
    def get_edge_id(self):
        return self.edge_id_var.get().strip()

    def get_edges_state(self):
        return {
            "edge_id": self.get_edge_id(),
            "efek_perlambatan": int(self.slowdown_var.get() or 0),
            "start_hour": int(self.start_hour_var.get() or 0),
            "end_hour": int(self.end_hour_var.get() or 23)
        }

    # ============== SETTERS ==============
    def set_edge(self, edge_id, data=None):
        self.edge_id_var.set(edge_id)
        
        if data is None and self.shared is not None:
            data = self.shared.edge_type.get(edge_id, {})
        
        self.set_slowdown(data.get("slowdown", 0))
        self.set_start_hour(data.get("start_hour", 0))
        self.set_end_hour(data.get("end_hour", 23))
    
    def set_edge_id(self, value):
        self.edge_id_var.set(value)

    def set_slowdown(self, value):
        self.slowdown_var.set(str(value))

    def set_start_hour(self, value):
        self.start_hour_var.set(str(value))

    def set_end_hour(self, value):
        self.end_hour_var.set(str(value))

    # ============== LOGIC ==============
    def validate_inputs(self):
        try:
            slowdown = int(self.slowdown_var.get())
            if slowdown < 0 or slowdown > 200:
                self.slowdown_var.set("0")
        except:
            self.slowdown_var.set("0")

        try:
            start = int(self.start_hour_var.get())
            if start < 0 or start > 23:
                self.start_hour_var.set("0")
        except:
            self.start_hour_var.set("0")

        try:
            end = int(self.end_hour_var.get())
            if end < 0 or end > 23:
                self.end_hour_var.set("23")
        except:
            self.end_hour_var.set("23")

    def update_info_label(self):
        try:
            start = int(self.start_hour_var.get())
            end = int(self.end_hour_var.get())
            
            if start == end:
                self.info_label.config(text=f"Macet hanya di jam {start}:00", fg="#E67E22")
            elif start < end:
                duration = end - start + 1
                self.info_label.config(text=f"Macet dari {start}:00 - {end}:00 ({duration} jam)", fg="#27AE60")
            else:
                duration = (24 - start) + end + 1
                self.info_label.config(text=f"Macet dari {start}:00 melewati tengah malam sampai {end}:00 ({duration} jam)", fg="#E74C3C")
        except:
            self.info_label.config(text="", fg="#7F8C8D")

    def apply_settings(self):
        self.validate_inputs()
        settings = self.get_edges_state()
        
        print("=== Settings Applied ===")
        print(f"Edge ID: {settings['edge_id']}")
        print(f"Efek Perlambatan: {settings['efek_perlambatan']} km/j")
        print(f"Interval Kemacetan: {settings['start_hour']}:00 - {settings['end_hour']}:00")

        if self.shared is not None:
            edge_id = settings["edge_id"]
            self.shared.edge_type[edge_id] = {
                "slowdown": settings["efek_perlambatan"],
                "start_hour": settings["start_hour"],
                "end_hour": settings["end_hour"]
            }
            print(f" Edge {edge_id} configuration saved to shared.edge_type")

    # =======================
    # MAIN LOOP
    # =======================
    def run(self):
        self.root.mainloop()

