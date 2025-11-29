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
        self.current_node_id = None  # track node yang sedang diedit

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
        # Display: Armada Bertugas (READ-ONLY)
        # -------------------------
        ttk.Label(frm, text="Armada Bertugas (managed by simulation):").grid(row=6, column=0, sticky="w")
        self.armada_bertugas_var = tk.StringVar(value="0")
        ttk.Entry(frm, textvariable=self.armada_bertugas_var, width=30, state="readonly").grid(row=7, column=0, pady=(0, 10))

        # -------------------------
        # Display: Armada Standby (READ-ONLY)
        # -------------------------
        ttk.Label(frm, text="Armada Standby (managed by simulation):").grid(row=8, column=0, sticky="w")
        self.armada_standby_var = tk.StringVar(value="0")
        ttk.Entry(frm, textvariable=self.armada_standby_var, width=30, state="readonly").grid(row=9, column=0, pady=(0, 10))

        # -------------------------
        # Info Frame
        # -------------------------
        info_frame = ttk.LabelFrame(frm, text="Info", padding=8)
        info_frame.grid(row=10, column=0, sticky="ew", pady=10)
        
        info_text = "⚠️ Hanya ubah:\n• Nama Garage\n• Jumlah Armada Total\n\narmada_bertugas dan armada_standby\ndiatur otomatis oleh simulasi."
        ttk.Label(info_frame, text=info_text, justify="left").pack(anchor="w")

        # -------------------------
        # Tombol Save
        # -------------------------
        self.save_btn = ttk.Button(frm, text="💾 Update Garage", command=self.on_save)
        self.save_btn.grid(row=11, column=0, sticky="ew")

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
        self.current_node_id = node_id
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

    # =======================
    # VALIDASI & SAVE
    # =======================
    def validate_inputs(self):
        # Validasi nama Garage
        if self.name_var.get().strip() == "":
            messagebox.showwarning("Validasi", "Nama Garage tidak boleh kosong.")
            return False

        # Validasi jumlah armada total
        try:
            total_val = int(self.total_armada_var.get())
            if total_val < 0:
                messagebox.showwarning("Validasi", "Jumlah Armada Total harus >= 0.")
                return False
        except ValueError:
            messagebox.showerror("Validasi", "Jumlah Armada Total harus berupa angka.")
            return False

        return True

    def on_save(self):
        """Save hanya nama dan total_armada"""
        # Debug: print apa yang sedang disimpan
        print(f"\n[GarageStateWindow] on_save called")
        print(f"[GarageStateWindow] current_node_id: {self.current_node_id}")
        print(f"[GarageStateWindow] shared: {self.shared}")
        
        if not self.validate_inputs():
            print("[GarageStateWindow] Validasi gagal")
            return

        if not self.current_node_id:
            messagebox.showwarning("Validasi", "Node belum dipilih.")
            return

        node_id = self.current_node_id
        print(f"[GarageStateWindow] Saving node_id: {node_id}")

        if not self.shared:
            messagebox.showerror("Error", "Shared state tidak ter-attach.")
            print("[GarageStateWindow] ERROR: shared is None")
            return

        if node_id not in self.shared.node_type:
            messagebox.showerror("Error", f"Node {node_id} tidak ditemukan di shared state.")
            print(f"[GarageStateWindow] ERROR: node {node_id} not in shared.node_type")
            return

        # Get nilai dari form
        nama_baru = self.name_var.get().strip()
        total_armada_baru = int(self.total_armada_var.get() or 0)
        
        print(f"[GarageStateWindow] nama_baru: {nama_baru}")
        print(f"[GarageStateWindow] total_armada_baru: {total_armada_baru}")

        # Get current garage_data untuk preserve armada_bertugas dan armada_standby
        current_garage_data = self.shared.node_type[node_id].get("garage_data", {
            "nama": "Garage",
            "total_armada": 0,
            "armada_bertugas": 0,
            "armada_standby": 0
        })

        # Update HANYA nama dan total_armada
        updated_data = {
            "nama": nama_baru,
            "total_armada": total_armada_baru,
            "armada_bertugas": current_garage_data.get("armada_bertugas", 0),
            "armada_standby": current_garage_data.get("armada_standby", 0)
        }

        # Update ke shared
        self.shared.node_type[node_id]["garage_data"] = updated_data
        print(f"[GarageStateWindow] Data updated in shared")
        print(f"[GarageStateWindow] Final data: {updated_data}")

        # Output ke console (untuk debugging)
        print(f"\n--- Update Garage ---")
        print(f"Node ID: {node_id}")
        print(f"Nama: {updated_data['nama']}")
        print(f"Total Armada: {updated_data['total_armada']}")
        print(f"Armada Bertugas (managed by sim): {updated_data['armada_bertugas']}")
        print(f"Armada Standby (managed by sim): {updated_data['armada_standby']}")
        print("---\n")
        
        messagebox.showinfo(
            "Berhasil", 
            f"Garage {node_id} berhasil diupdate:\n"
            f"• Nama: {updated_data['nama']}\n"
            f"• Total Armada: {updated_data['total_armada']}"
        )

    # =======================
    # RUN LOOP
    # =======================
    def run(self):
        self.root.mainloop()