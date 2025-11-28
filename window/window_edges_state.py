import tkinter as tk
from tkinter import ttk

class EdgeStateWindow:
    def __init__(self, master=None):
        if master is None:
            self.root = tk.Tk()
        else:
            self.root = tk.Toplevel(master)

        self.root.title("Edges State Configuration")
        self.root.geometry("420x380")
        self.root.configure(bg="#ECF0F1")
        self.shared = None  # akan diattach nanti

        # Main frame
        main_frame = tk.Frame(self.root, bg="#E8E8E8", padx=25, pady=25)
        main_frame.pack(fill="both", expand=True)

        # Title
        title_label = tk.Label(main_frame, text="Edges State Settings",
                               font=("Arial", 13, "bold"),
                               bg="#F5F5F5", fg="#2C3E50")
        title_label.pack(anchor="w", pady=(0, 20))

        # Content frame
        self.content_frame = tk.Frame(main_frame, bg="#FFFFFF", relief="flat", bd=1)
        self.content_frame.pack(fill="both", expand=True)

        # Edge ID
        tk.Label(self.content_frame, text="Edges ID:", font=("Arial", 10),
                 bg="#FFFFFF", anchor="w", width=20).grid(row=0, column=0, padx=20, pady=15, sticky="w")
        self.edge_id_var = tk.StringVar()
        tk.Entry(self.content_frame, textvariable=self.edge_id_var, width=15).grid(row=0, column=1, padx=20, pady=15, sticky="w")

        # Helper function for spinbox rows
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

        # Input fields
        self.delay_var, self.delay_spinbox = create_input_row(
            self.content_frame, "Potensi keterlambatan:", "0", "%", 0, 100, 1
        )
        self.slowdown_var, self.slowdown_spinbox = create_input_row(
            self.content_frame, "Efek perlambatan:", "0", "km/j", 0, 200, 2
        )

        # Separator
        ttk.Separator(self.content_frame, orient="horizontal") \
            .grid(row=3, column=0, columnspan=2, sticky="we", padx=20, pady=10)

        # Buttons
        button_frame = tk.Frame(self.content_frame, bg="#FFFFFF")
        button_frame.grid(row=4, column=0, columnspan=2, pady=15)

        self.apply_btn = ttk.Button(button_frame, text="Apply Settings", command=self.apply_settings, width=15)
        self.apply_btn.pack()

        # Bind validation
        self.delay_spinbox.bind('<FocusOut>', lambda e: self.validate_inputs())
        self.slowdown_spinbox.bind('<FocusOut>', lambda e: self.validate_inputs())

    # =======================
    # ATTACH SHARED
    # =======================
    def attach_shared(self, shared):
        self.shared = shared
        shared.edge_state_window = self

    # =======================
    # GETTERS
    # =======================
    def get_edge_id(self):
        return self.edge_id_var.get().strip()

    def get_edges_state(self):
        return {
            "edge_id": self.get_edge_id(),
            "potensi_keterlambatan": int(self.delay_var.get() or 0),
            "efek_perlambatan": int(self.slowdown_var.get() or 0)
        }

    # =======================
    # SETTERS
    # =======================
    def set_edge(self, edge_id, data=None):
        self.edge_id_var.set(edge_id)
        
        if data is None and self.shared is not None:
            data = self.shared.edge_type.get(edge_id, {"delay": 0, "slowdown": 0})
        
        self.set_delay(data.get("delay", 0))
        self.set_slowdown(data.get("slowdown", 0))
    
    def set_edge_id(self, value):
        self.edge_id_var.set(value)

    def set_delay(self, value):
        self.delay_var.set(str(value))

    def set_slowdown(self, value):
        self.slowdown_var.set(str(value))

    # =======================
    # VALIDATION & EVENTS
    # =======================
    def validate_inputs(self):
        try:
            delay = int(self.delay_var.get())
            if delay < 0 or delay > 100:
                self.delay_var.set("0")
        except:
            self.delay_var.set("0")

        try:
            slowdown = int(self.slowdown_var.get())
            if slowdown < 0 or slowdown > 200:
                self.slowdown_var.set("0")
        except:
            self.slowdown_var.set("0")

    def apply_settings(self):
        self.validate_inputs()
        settings = self.get_edges_state()
        print("=== Settings Applied ===")
        print(f"Edge ID: {settings['edge_id']}")
        print(f"Potensi Keterlambatan: {settings['potensi_keterlambatan']}%")
        print(f"Efek Perlambatan: {settings['efek_perlambatan']} km/j")

        if self.shared is not None:
            edge_id = settings["edge_id"]
            self.shared.edge_type[edge_id] = {
                "delay": settings["potensi_keterlambatan"],
                "slowdown": settings["efek_perlambatan"]
            }

    # =======================
    # MAIN LOOP
    # =======================
    def run(self):
        self.root.mainloop()
