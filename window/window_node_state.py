import tkinter as tk
from tkinter import ttk, messagebox

class NodeStateWindow:
    def __init__(self, master=None):
        if master is None:
            self.root = tk.Tk()
        else:
            self.root = tk.Toplevel(master)

        self.root.title("Node State")
        self.root.geometry("360x240")

        content = ttk.Frame(self.root, padding=12)
        content.pack(fill="both", expand=True)

        ttk.Label(content, text="ID Node:").grid(row=0, column=0, sticky="w")
        self.id_var = tk.StringVar()
        entry = ttk.Entry(content, textvariable=self.id_var, width=20, state="readonly")
        entry.grid(row=1, column=0, pady=(0, 12))

        self.tps_var = tk.BooleanVar()
        self.tpa_var = tk.BooleanVar()
        self.gar_var = tk.BooleanVar()

        def toggle_tps():
            if self.tps_var.get():
                self.tpa_var.set(False)
                self.gar_var.set(False)

        def toggle_tpa():
            if self.tpa_var.get():
                self.tps_var.set(False)
                self.gar_var.set(False)

        def toggle_garage():
            if self.gar_var.get():
                self.tps_var.set(False)
                self.tpa_var.set(False)

        ttk.Checkbutton(content, text="TPS?", variable=self.tps_var, command=toggle_tps)\
            .grid(row=2, column=0, sticky="w", pady=(0, 12))
        ttk.Checkbutton(content, text="TPA?", variable=self.tpa_var, command=toggle_tpa)\
            .grid(row=3, column=0, sticky="w", pady=(0, 12))
        ttk.Checkbutton(content, text="Garasi?", variable=self.gar_var, command=toggle_garage)\
            .grid(row=4, column=0, sticky="w", pady=(0, 12))


        ttk.Button(content, text="Save", command=self.on_save).grid(row=5, column=0, sticky="w")

    # ============== SHARED ==============
    def attach_shared(self, shared):
        self.shared = shared
        shared.node_state_window = self


    # ============== SETTERS ==============
    def set_node(self, node_id, flags):
        self.id_var.set(str(node_id))
        self.tps_var.set(flags.get("tps", False))
        self.tpa_var.set(flags.get("tpa", False))
        self.gar_var.set(flags.get("garage", False))


    # ============== LOGIC ==============
    def on_save(self):
        if not hasattr(self, "shared") or self.id_var.get() == "":
            messagebox.showwarning("Warning", "Node belum dipilih")
            return

        node_id = int(self.id_var.get())
        self.shared.node_type[node_id] = {
            "tps": self.tps_var.get(),
            "tpa": self.tpa_var.get(),
            "garage": self.gar_var.get()
        }

        messagebox.showinfo("Saved", f"Node {node_id} updated")



    def run(self):
        self.root.mainloop()
