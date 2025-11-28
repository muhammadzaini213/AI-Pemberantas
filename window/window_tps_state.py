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
        self.root.geometry("400x320")
        self.shared = None  # akan diattach nanti

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
        # Input: Jumlah sampah per hari
        # -------------------------
        ttk.Label(frm, text="Jumlah sampah per hari (kg):").grid(row=4, column=0, sticky="w")
        self.amount_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.amount_var, width=30).grid(row=5, column=0, pady=(0, 10))

        # -------------------------
        # Input: Jumlah sampah hari ini
        # -------------------------
        ttk.Label(frm, text="Jumlah sampah hari ini (kg):").grid(row=6, column=0, sticky="w")
        self.today_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.today_var, width=30).grid(row=7, column=0, pady=(0, 10))

        # -------------------------
        # Checkbox: Dilayanin hari ini
        # -------------------------
        self.served_var = tk.BooleanVar()
        ttk.Checkbutton(frm, text="Dilayanin hari ini", variable=self.served_var).grid(
            row=8, column=0, sticky="w", pady=(0, 12)
        )

        # -------------------------
        # Tombol Save
        # -------------------------
        self.save_btn = ttk.Button(frm, text="Save", command=self.on_save)
        self.save_btn.grid(row=9, column=0, sticky="w")

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
                    "sampah_kg": 0,
                    "sampah_hari_ini": 0,
                    "dilayanin": False
                }



    # =======================
    # SETTERS
    # =======================
    def set_node(self, node_id, data=None):
        self.node_var.set(str(node_id))
        
        # ambil data dari node_type jika tidak diberikan
        if data is None and self.shared and node_id in self.shared.node_type:
            data = self.shared.node_type[node_id].get("tps_data", {
                "nama": "",
                "sampah_kg": 0,
                "sampah_hari_ini": 0,
                "dilayanin": False
            })

        self.name_var.set(data.get("nama", ""))
        self.amount_var.set(str(data.get("sampah_kg", 0)))
        self.today_var.set(str(data.get("sampah_hari_ini", 0)))
        self.served_var.set(data.get("dilayanin", False))


    # =======================
    # VALIDASI & SAVE
    # =======================
    def validate_inputs(self):
        try:
            amount_val = float(self.amount_var.get())
            if amount_val < 0:
                self.amount_var.set("0")
        except:
            self.amount_var.set("0")

        try:
            today_val = float(self.today_var.get())
            if today_val < 0:
                self.today_var.set("0")
        except:
            self.today_var.set("0")

    def on_save(self):
        self.validate_inputs()
        node_id = int(self.node_var.get().strip())
        if not node_id:
            messagebox.showwarning("Validasi", "Node belum dipilih.")
            return

        data = {
            "nama": self.name_var.get().strip(),
            "sampah_kg": float(self.amount_var.get() or 0),
            "sampah_hari_ini": float(self.today_var.get() or 0),
            "dilayanin": self.served_var.get()
        }

        if self.shared and node_id in self.shared.node_type:
            self.shared.node_type[node_id]["tps_data"] = data

        messagebox.showinfo("Saved", f"Node {node_id} berhasil disimpan:\n{data}")
        print(self.shared.node_type[node_id])



    # =======================
    # RUN LOOP
    # =======================
    def run(self):
        self.root.mainloop()
