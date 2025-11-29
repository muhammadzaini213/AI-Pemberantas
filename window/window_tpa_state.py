import tkinter as tk
from tkinter import ttk, messagebox

class TPAStateWindow:
    def __init__(self, master=None):
        if master is None:
            self.root = tk.Tk()
        else:
            self.root = tk.Toplevel(master)

        self.root.title("TPA State - Sistem Sampah Balikpapan")
        self.root.geometry("400x280")
        self.shared = None

        frm = ttk.Frame(self.root, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Node ID:").grid(row=0, column=0, sticky="w")
        self.node_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.node_var, width=30, state="readonly").grid(row=1, column=0, pady=(0, 10))

        ttk.Label(frm, text="Nama TPA:").grid(row=2, column=0, sticky="w")
        self.name_var = tk.StringVar(value="TPA")
        ttk.Entry(frm, textvariable=self.name_var, width=30).grid(row=3, column=0, pady=(0, 10))

        ttk.Label(frm, text="Sampah Terkumpul (kg):").grid(row=4, column=0, sticky="w")
        self.total_var = tk.StringVar(value="0")
        ttk.Entry(frm, textvariable=self.total_var, width=30, state="readonly").grid(row=5, column=0, pady=(0, 10))

        self.save_btn = ttk.Button(frm, text="Update Status TPA", command=self.on_save)
        self.save_btn.grid(row=6, column=0, sticky="ew")

    # ============== SHARED ==============
    def attach_shared(self, shared):
        self.shared = shared
        shared.tpa_state_window = self
        for node_id, flags in shared.node_type.items():
            if "tpa_data" not in flags:
                flags["tpa_data"] = {
                    "nama": "TPA",
                    "total_sampah": 0
                }

    # ============== SETTERS ==============
    def set_node(self, node_id, data=None):
        self.node_var.set(str(node_id))
        
        if data is None and self.shared and node_id in self.shared.node_type:
            data = self.shared.node_type[node_id].get("tpa_data", {
                "nama": "TPA",
                "total_sampah": 0
            })

        self.name_var.set(data.get("nama", "TPA"))
        self.total_var.set(str(data.get("total_sampah", 0)))

    def set_output(self, text, is_error=False):
        color = "red" if is_error else "green"
        self.output_label.config(text=text, foreground=color)

    # ============== LOGIC ==============
    def validate_inputs(self):
        if self.name_var.get().strip() == "":
            self.set_output("Error: Nama TPA wajib diisi!", is_error=True)
            return False

        try:
            total_val = float(self.total_var.get())
            if total_val < 0:
                self.total_var.set("0")
        except:
            self.set_output("Error: Jumlah sampah harus angka!", is_error=True)
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
            "total_sampah": float(self.total_var.get() or 0)
        }

        if self.shared and node_id in self.shared.node_type:
            self.shared.node_type[node_id]["tpa_data"] = data

        print(f"--- Update TPA ---")
        print(f"Node ID: {node_id}")
        print(f"Lokasi: {data['nama']}")
        print(f"Total Timbunan: {data['total_sampah']} kg")
        
        self.set_output(f"Sukses! Status {data['nama']} diperbarui.")
        messagebox.showinfo("Saved", f"Node {node_id} berhasil disimpan:\n{data}")

    def run(self):
        self.root.mainloop()