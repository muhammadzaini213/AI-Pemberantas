#!/usr/bin/env python3
"""
Node State (rafif)
TPS dan TPA tidak bisa dicentang bersamaan.
"""

import tkinter as tk
from tkinter import ttk, messagebox


def build_node_state_ui():
    root = tk.Tk()
    root.title("Node State (rafif)")
    root.geometry("360x240")

    frm = ttk.Frame(root, padding=12)
    frm.pack(fill="both", expand=True)

    # -----------------------------------
    # Input: ID Node (angka)
    # -----------------------------------
    ttk.Label(frm, text="ID Node:").grid(row=0, column=0, sticky="w")

    id_var = tk.StringVar()

    def validate_int(P):
        return P.isdigit() or P == ""

    vcmd = (root.register(validate_int), '%P')

    ttk.Entry(
        frm,
        textvariable=id_var,
        width=20,
        validate="key",
        validatecommand=vcmd
    ).grid(row=1, column=0, pady=(0, 12))

    # -----------------------------------
    # Checkbox TPS dan TPA (mutual exclusive)
    # -----------------------------------
    tps_var = tk.BooleanVar()
    tpa_var = tk.BooleanVar()

    def toggle_tps():
        """Jika TPS dicentang, matikan TPA."""
        if tps_var.get():
            tpa_var.set(False)

    def toggle_tpa():
        """Jika TPA dicentang, matikan TPS."""
        if tpa_var.get():
            tps_var.set(False)

    ttk.Checkbutton(frm, text="TPS?", variable=tps_var, command=toggle_tps).grid(
        row=2, column=0, sticky="w", pady=(0, 6)
    )

    ttk.Checkbutton(frm, text="TPA?", variable=tpa_var, command=toggle_tpa).grid(
        row=3, column=0, sticky="w", pady=(0, 12)
    )

    # -----------------------------------
    # Tombol Save
    # -----------------------------------
    def on_save():
        if id_var.get().strip() == "":
            messagebox.showwarning("Validasi", "ID Node harus diisi.")
            return

        data = {
            "id_node": int(id_var.get()),
            "is_tps": tps_var.get(),
            "is_tpa": tpa_var.get()
        }

        messagebox.showinfo("Saved", f"Data node tersimpan:\n\n{data}")

        # Reset
        id_var.set("")
        tps_var.set(False)
        tpa_var.set(False)

    ttk.Button(frm, text="Save", command=on_save).grid(row=4, column=0, sticky="w")

    root.mainloop()


if __name__ == "__main__":
    build_node_state_ui()
