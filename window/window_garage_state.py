import tkinter as tk
from tkinter import ttk, messagebox

class GarageStateWindow:
    def __init__(self, master=None):
        # Root atau Toplevel
        if master is None:
            self.root = tk.Tk()
        else:
            self.root = tk.Toplevel(master)

        self.root.title("Garage State - Sistem Sampah Balikpapan")
        self.root.geometry("400x380")
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
        # Input: Nama Garage
        # -------------------------
        ttk.Label(frm, text="Nama Garage:").grid(row=2, column=0, sticky="w")
        self.name_var = tk.StringVar(value="Garage")
        ttk.Entry(frm, textvariable=self.name_var, width=30).grid(row=3, column=0, pady=(0, 10))

        # -------------------------
        # Input: Jumlah Armada Total
        # -------------------------
        ttk.Label(frm, text="Jumlah Armada Total:").grid(row=4, column=0, sticky="w")
        self.total_armada_var = tk.StringVar(value="0")
        ttk.Entry(frm, textvariable=self.total_armada_var, width=30).grid(row=5, column=0, pady=(0, 10))

        # -------------------------
        # Input: Armada Bertugas
        # -------------------------
        ttk.Label(frm, text="Armada Bertugas:").grid(row=6, column=0, sticky="w")
        self.armada_bertugas_var = tk.StringVar(value="0")
        ttk.Entry(frm, textvariable=self.armada_bertugas_var, width=30).grid(row=7, column=0, pady=(0, 10))

        # -------------------------
        # Input: Armada Standby
        # -------------------------
        ttk.Label(frm, text="Armada Standby:").grid(row=8, column=0, sticky="w")
        self.armada_standby_var = tk.StringVar(value="0")
        ttk.Entry(frm, textvariable=self.armada_standby_var, width=30).grid(row=9, column=0, pady=(0, 10))

        # -------------------------
        # Tombol Save
        # -------------------------
        self.save_btn = ttk.Button(frm, text="Update Status Garage", command=self.on_save)
        self.save_btn.grid(row=10, column=0, sticky="ew")

    # =======================
    # ATTACH SHARED
    # =======================
    def attach_shared(self, shared):
        self.shared = shared
        shared.garage_state_window = self
        for node_id, flags in shared.node_type.items():
            if "garage_data" not in flags:
                flags["garage_data"] = {
                    "nama": "Garage",
                    "total_armada": 0,
                    "armada_bertugas": 0,
                    "armada_standby": 0
                }

    # =======================
    # SETTERS
    # =======================
    def set_node(self, node_id, data=None):
        self.node_var.set(str(node_id))
        
        # ambil data dari node_type jika tidak diberikan
        if data is None and self.shared and node_id in self.shared.node_type:
            data = self.shared.node_type[node_id].get("garage_data", {
                "nama": "Garage",
                "total_armada": 0,
                "armada_bertugas": 0,
                "armada_standby": 0
            })

        self.name_var.set(data.get("nama", "Garage"))
        self.total_armada_var.set(str(data.get("total_armada", 0)))
        self.armada_bertugas_var.set(str(data.get("armada_bertugas", 0)))
        self.armada_standby_var.set(str(data.get("armada_standby", 0)))

    def set_output(self, text, is_error=False):
        """Mengupdate status label"""
        color = "red" if is_error else "green"
        self.output_label.config(text=text, foreground=color)

    # =======================
    # VALIDASI & SAVE
    # =======================
    def validate_inputs(self):
        # Validasi nama Garage
        if self.name_var.get().strip() == "":
            self.set_output("Error: Nama Garage wajib diisi!", is_error=True)
            return False

        # Validasi jumlah armada total
        try:
            total_val = int(self.total_armada_var.get())
            if total_val < 0:
                self.total_armada_var.set("0")
        except:
            self.set_output("Error: Jumlah armada total harus angka!", is_error=True)
            return False

        # Validasi armada bertugas
        try:
            bertugas_val = int(self.armada_bertugas_var.get())
            if bertugas_val < 0:
                self.armada_bertugas_var.set("0")
        except:
            self.set_output("Error: Armada bertugas harus angka!", is_error=True)
            return False

        # Validasi armada standby
        try:
            standby_val = int(self.armada_standby_var.get())
            if standby_val < 0:
                self.armada_standby_var.set("0")
        except:
            self.set_output("Error: Armada standby harus angka!", is_error=True)
            return False

        # Validasi logika: bertugas + standby harus = total
        total = int(self.total_armada_var.get())
        bertugas = int(self.armada_bertugas_var.get())
        standby = int(self.armada_standby_var.get())
        
        if bertugas + standby != total:
            self.set_output("Error: Bertugas + Standby harus sama dengan Total!", is_error=True)
            return False

        return True

    def on_save(self):
        if not self.validate_inputs():
            return

        node_id_str = self.node_var.get().strip()
        if not node_id_str:
            messagebox.showwarning("Validasi", "Node belum dipilih.")
            return

        node_id = int(node_id_str)

        data = {
            "nama": self.name_var.get().strip(),
            "total_armada": int(self.total_armada_var.get() or 0),
            "armada_bertugas": int(self.armada_bertugas_var.get() or 0),
            "armada_standby": int(self.armada_standby_var.get() or 0)
        }

        if self.shared and node_id in self.shared.node_type:
            self.shared.node_type[node_id]["garage_data"] = data

        # Output ke console (untuk debugging)
        print(f"--- Update Garage ---")
        print(f"Node ID: {node_id}")
        print(f"Nama: {data['nama']}")
        print(f"Total Armada: {data['total_armada']}")
        print(f"Armada Bertugas: {data['armada_bertugas']}")
        print(f"Armada Standby: {data['armada_standby']}")
        
        self.set_output(f"Sukses! Status {data['nama']} diperbarui.")
        messagebox.showinfo("Saved", f"Node {node_id} berhasil disimpan:\n{data}")

    # =======================
    # RUN LOOP
    # =======================
    def run(self):
        self.root.mainloop()