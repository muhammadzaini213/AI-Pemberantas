import tkinter as tk
from tkinter import ttk, messagebox

class TPSStateWindow:
    def __init__(self, master=None):
        # Root atau Toplevel
        if master is None:
            self.root = tk.Tk()
        else:
            self.root = tk.Toplevel(master)

        self.root.title("TPS State")
        self.root.geometry("400x350")
        self.shared = None  # akan diattach nanti
        self.current_node_id = None

        frm = ttk.Frame(self.root, padding=12)
        frm.pack(fill="both", expand=True)

        # -------------------------
        # Input: Node ID
        # -------------------------
        ttk.Label(frm, text="Node ID:").grid(row=0, column=0, sticky="w")
        self.node_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.node_var, width=30, state="readonly").grid(row=1, column=0, pady=(0, 10))

        # -------------------------
        # Input: Nama TPS
        # -------------------------
        ttk.Label(frm, text="Nama TPS:").grid(row=2, column=0, sticky="w")
        self.name_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.name_var, width=30).grid(row=3, column=0, pady=(0, 10))

        # -------------------------
        # Input: Sampah per hari (STATIS - untuk increment harian)
        # -------------------------
        ttk.Label(frm, text="Sampah per hari (kg) - Static:").grid(row=4, column=0, sticky="w")
        self.sampah_per_hari_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.sampah_per_hari_var, width=30).grid(row=5, column=0, pady=(0, 10))

        # -------------------------
        # Display: Sampah saat ini (INCREMENT - read-only, auto-increment)
        # -------------------------
        ttk.Label(frm, text="Sampah saat ini (kg) - Current:").grid(row=6, column=0, sticky="w")
        self.sampah_kg_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.sampah_kg_var, width=30, state="readonly").grid(row=7, column=0, pady=(0, 10))

        # -------------------------
        # Checkbox: Dilayanin hari ini
        # -------------------------
        self.served_var = tk.BooleanVar()
        ttk.Checkbutton(frm, text="Dilayanin hari ini", variable=self.served_var).grid(
            row=8, column=0, sticky="w", pady=(0, 12)
        )

        # -------------------------
        # Info Frame
        # -------------------------
        info_frame = ttk.LabelFrame(frm, text="Info", padding=8)
        info_frame.grid(row=9, column=0, sticky="ew", pady=10)
        
        info_text = ("• Sampah per hari: Jumlah yang ditambahkan setiap hari (statis)\n"
                     "• Sampah saat ini: Total sampah terakumulasi (auto increment)\n\n"
                     "Setiap hari, sampah saat ini akan bertambah\nsesuai nilai sampah per hari (±30%)")
        ttk.Label(info_frame, text=info_text, justify="left").pack(anchor="w")

        # -------------------------
        # Tombol Save
        # -------------------------
        self.save_btn = ttk.Button(frm, text="💾 Save", command=self.on_save)
        self.save_btn.grid(row=10, column=0, sticky="ew")

    # =======================
    # ATTACH SHARED
    # =======================
    def attach_shared(self, shared):
        self.shared = shared
        shared.tps_state_window = self
        for node_id, flags in shared.node_type.items():
            if "tps_data" not in flags:
                flags["tps_data"] = {
                    "nama": "",
                    "sampah_kg": 0,  # Current/accumulated garbage
                    "sampah_per_hari": 0,  # Daily increment (static)
                    "dilayanin": False
                }

    # =======================
    # SETTERS
    # =======================
    def set_node(self, node_id, data=None):
        self.current_node_id = node_id
        self.node_var.set(str(node_id))
        
        # ambil data dari node_type jika tidak diberikan
        if data is None and self.shared and node_id in self.shared.node_type:
            data = self.shared.node_type[node_id].get("tps_data", {
                "nama": "",
                "sampah_kg": 0,
                "sampah_per_hari": 0,
                "dilayanin": False
            })

        self.name_var.set(data.get("nama", ""))
        self.sampah_per_hari_var.set(str(data.get("sampah_per_hari", 0)))  # Static value
        self.sampah_kg_var.set(str(data.get("sampah_kg", 0)))  # Current accumulated
        self.served_var.set(data.get("dilayanin", False))

    # =======================
    # VALIDASI & SAVE
    # =======================
    def validate_inputs(self):
        try:
            per_hari_val = float(self.sampah_per_hari_var.get())
            if per_hari_val < 0:
                self.sampah_per_hari_var.set("0")
        except ValueError:
            self.sampah_per_hari_var.set("0")

    def on_save(self):
        self.validate_inputs()
        
        if not self.current_node_id:
            messagebox.showwarning("Validasi", "Node belum dipilih.")
            return

        node_id = self.current_node_id

        if not self.shared or node_id not in self.shared.node_type:
            messagebox.showerror("Error", "Node tidak ditemukan di shared state.")
            return

        data = {
            "nama": self.name_var.get().strip(),
            "sampah_per_hari": float(self.sampah_per_hari_var.get() or 0),  # Static daily increment
            "dilayanin": self.served_var.get()
        }

        self.shared.node_type[node_id]["tps_data"] = data

        print(f"\n--- Update TPS ---")
        print(f"Node ID: {node_id}")
        print(f"Nama: {data['nama']}")
        print(f"Sampah per hari (static): {data['sampah_per_hari']} kg")
        print(f"Dilayanin: {data['dilayanin']}")
        print("---\n")

        messagebox.showinfo(
            "Berhasil",
            f"TPS {node_id} berhasil diupdate:\n"
            f"• Nama: {data['nama']}\n"
            f"• Sampah per hari: {data['sampah_per_hari']} kg\n"
        )

    # =======================
    # RUN LOOP
    # =======================
    def run(self):
        self.root.mainloop()