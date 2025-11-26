#!/usr/bin/env python3
"""
TPS State (rafif)
Versi minimalis tanpa CSV dan tanpa listbox.
Hanya form input + tombol Save.
"""

import tkinter as tk
from tkinter import ttk, messagebox


def build_ui():
    root = tk.Tk()
    root.title("TPS State (rafif)")
    root.geometry("400x260")

    frm = ttk.Frame(root, padding=12)
    frm.pack(fill="both", expand=True)

    # -------------------------
    #  Input: Nama TPS
    # -------------------------
    ttk.Label(frm, text="Nama TPS:").grid(row=0, column=0, sticky="w")
    name_var = tk.StringVar()
    ttk.Entry(frm, textvariable=name_var, width=30).grid(row=1, column=0, pady=(0, 10))

    # -------------------------
    #  Input: Jumlah Sampah
    # -------------------------
    ttk.Label(frm, text="Jumlah sampah per hari (kg):").grid(row=2, column=0, sticky="w")
    amount_var = tk.StringVar()
    ttk.Entry(frm, textvariable=amount_var, width=30).grid(row=3, column=0, pady=(0, 10))

    # -------------------------
    #  Checkbox
    # -------------------------
    served_var = tk.BooleanVar()
    ttk.Checkbutton(frm, text="Dilayanin hari ini", variable=served_var).grid(
        row=4, column=0, sticky="w", pady=(0, 12)
    )

    # -------------------------
    #  Tombol Save
    # -------------------------
    def on_save():
        name = name_var.get().strip()
        amount = amount_var.get().strip()

        if not name:
            messagebox.showwarning("Validasi", "Nama TPS harus diisi.")
            return

        try:
            amount_val = float(amount) if amount else 0.0
        except ValueError:
            messagebox.showwarning("Validasi", "Jumlah sampah harus angka.")
            return

        served = served_var.get()

        # Hasil disimpan hanya di memori (dictionary)
        data = {
            "nama": name,
            "sampah_kg": amount_val,
            "dilayanin": served
        }

        messagebox.showinfo("Saved", f"Data berhasil disimpan:\n\n{data}")

        # Reset form
        name_var.set("")
        amount_var.set("")
        served_var.set(False)

    ttk.Button(frm, text="Save", command=on_save).grid(row=5, column=0, sticky="w")

    root.mainloop()


if __name__ == "__main__":
    build_ui()
