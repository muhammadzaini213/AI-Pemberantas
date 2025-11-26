#!/usr/bin/env python3
"""
Simple Tkinter UI for "TPS State (rafif)"
Versi tanpa image sama sekali.
"""

from pathlib import Path
import csv
import tkinter as tk
from tkinter import ttk, messagebox

CSV_PATH = Path("./tps_states.csv")   # simpan CSV di folder yang sama

# Ensure CSV exists with header
if not CSV_PATH.exists():
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Nama TPS", "Jumlah Sampah (kg)", "Dilayanin Hari Ini"])


def load_saved():
    rows = []
    if CSV_PATH.exists():
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            for r in reader:
                rows.append(r)
    return rows


def save_row(name, amount, served):
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([name, amount, served])


def build_ui():
    root = tk.Tk()
    root.title("TPS State (rafif)")
    root.geometry("720x400")

    frm = ttk.Frame(root, padding=10)
    frm.pack(fill="both", expand=True)

    # Left: form
    left = ttk.Frame(frm)
    left.pack(side="left", fill="y", padx=(0, 10))

    ttk.Label(left, text="Nama TPS:").grid(row=0, column=0, sticky="w")
    name_var = tk.StringVar()
    ttk.Entry(left, textvariable=name_var, width=30).grid(row=1, column=0, pady=(0, 8))

    ttk.Label(left, text="Jumlah sampah per hari (kg):").grid(row=2, column=0, sticky="w")
    amount_var = tk.StringVar()
    ttk.Entry(left, textvariable=amount_var, width=30).grid(row=3, column=0, pady=(0, 8))

    served_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(left, text="Dilayanin hari ini", variable=served_var).grid(row=4, column=0, pady=(0, 8), sticky="w")

    def on_add():
        name = name_var.get().strip()
        amount = amount_var.get().strip()
        served = served_var.get()
        if not name:
            messagebox.showwarning("Validasi", "Nama TPS harus diisi.")
            return
        if amount == "":
            amount_val = "0"
        else:
            try:
                amount_val = str(float(amount))
            except Exception:
                messagebox.showwarning("Validasi", "Jumlah sampah harus angka.")
                return
        save_row(name, amount_val, str(served))
        update_listbox()
        name_var.set("")
        amount_var.set("")
        served_var.set(False)

    ttk.Button(left, text="Tambah / Simpan", command=on_add).grid(row=5, column=0, pady=(6, 0), sticky="w")

    # Right: saved entries only (WITHOUT IMAGE)
    right = ttk.Frame(frm)
    right.pack(side="left", fill="both", expand=True)

    # Placeholder (agar layout tetap rapi, tapi tanpa gambar)
    ttk.Label(right, text="").pack(anchor="n", pady=(0, 8))

    # Listbox section
    list_frame = ttk.Frame(right)
    list_frame.pack(fill="both", expand=True)

    ttk.Label(list_frame, text="Saved TPS States:").pack(anchor="w")
    listbox = tk.Listbox(list_frame, height=5)
    listbox.pack(fill="both", expand=True, pady=(4, 0))

    def update_listbox():
        listbox.delete(0, tk.END)
        for row in load_saved():
            display = f"Nama: {row[0]} | Sampah: {row[1]} kg | Dilayanin: {row[2]}"
            listbox.insert(tk.END, display)

    def on_delete_selected():
        sel = listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        rows = load_saved()
        del rows[idx]
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Nama TPS", "Jumlah Sampah (kg)", "Dilayanin Hari Ini"])
            writer.writerows(rows)
        update_listbox()

    btn_row = ttk.Frame(list_frame)
    btn_row.pack(fill="x", pady=(6, 0))
    ttk.Button(btn_row, text="Hapus Terpilih", command=on_delete_selected).pack(side="left")

    update_listbox()
    root.mainloop()


if __name__ == "__main__":
    build_ui()
