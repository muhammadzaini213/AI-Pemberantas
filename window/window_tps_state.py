#!/usr/bin/env python3
"""
TPS State (rafif)
Versi standar Tkinter + tombol Save yang jelas.
Tanpa gambar.
"""

from pathlib import Path
import csv
import tkinter as tk
from tkinter import ttk, messagebox

CSV_PATH = Path("./tps_states.csv")


# ----------------------------------------
#  CSV Utilities
# ----------------------------------------

def ensure_csv_exists():
    if not CSV_PATH.exists():
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Nama TPS", "Jumlah Sampah (kg)", "Dilayanin Hari Ini"])


def load_rows():
    ensure_csv_exists()
    rows = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)
        rows = list(reader)
    return rows


def save_all_rows(rows):
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Nama TPS", "Jumlah Sampah (kg)", "Dilayanin Hari Ini"])
        writer.writerows(rows)


def append_row(name, amount, served):
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([name, amount, served])


# ----------------------------------------
#  UI Builder
# ----------------------------------------

def build_ui():
    root = tk.Tk()
    root.title("TPS State (rafif)")
    root.geometry("720x420")

    main = ttk.Frame(root, padding=10)
    main.pack(fill="both", expand=True)

    # -----------------------------------------------------------
    #  Left Panel: Input Form
    # -----------------------------------------------------------
    left = ttk.Frame(main)
    left.pack(side="left", fill="y", padx=(0, 12))

    ttk.Label(left, text="Nama TPS:").grid(row=0, column=0, sticky="w")
    name_var = tk.StringVar()
    ttk.Entry(left, textvariable=name_var, width=28).grid(row=1, column=0, pady=(0, 8))

    ttk.Label(left, text="Jumlah sampah per hari (kg):").grid(row=2, column=0, sticky="w")
    amount_var = tk.StringVar()
    ttk.Entry(left, textvariable=amount_var, width=28).grid(row=3, column=0, pady=(0, 8))

    served_var = tk.BooleanVar()
    ttk.Checkbutton(left, text="Dilayanin hari ini", variable=served_var).grid(
        row=4, column=0, sticky="w", pady=(0, 8)
    )

    # ------------------------------
    # Tombol Save (1 data)
    # ------------------------------
    def save_single():
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

        append_row(name, amount_val, served_var.get())
        update_listbox()

        name_var.set("")
        amount_var.set("")
        served_var.set(False)

    ttk.Button(left, text="Save", command=save_single).grid(row=5, column=0, pady=(5, 0), sticky="w")

    # -----------------------------------------------------------
    #  Right Panel: List View
    # -----------------------------------------------------------
    right = ttk.Frame(main)
    right.pack(side="left", fill="both", expand=True)

    ttk.Label(right, text="Daftar TPS yang tersimpan:").pack(anchor="w")

    listbox = tk.Listbox(right, height=10)
    listbox.pack(fill="both", expand=True, pady=(6, 0))

    # ------------------------------
    # Update Listbox
    # ------------------------------
    def update_listbox():
        listbox.delete(0, tk.END)
        for name, amount, served in load_rows():
            listbox.insert(
                tk.END,
                f"Nama: {name} | Sampah: {amount} kg | Dilayanin: {served}"
            )

    # ------------------------------
    # Hapus data terpilih
    # ------------------------------
    def delete_selected():
        sel = listbox.curselection()
        if not sel:
            return

        rows = load_rows()
        del rows[sel[0]]
        save_all_rows(rows)
        update_listbox()

    # ------------------------------
    # Save All (overwrite CSV)
    # ------------------------------
    def save_all():
        rows = []
        for i in range(listbox.size()):
            item = listbox.get(i)
            # Parsing ringan supaya tetap bisa save ulang
            parts = item.split("|")
            name = parts[0].split(":")[1].strip()
            amount = parts[1].split(":")[1].replace("kg", "").strip()
            served = parts[2].split(":")[1].strip()
            rows.append([name, amount, served])

        save_all_rows(rows)
        messagebox.showinfo("Info", "Semua data berhasil disimpan ulang.")

    # Tombol aksi
    btn_row = ttk.Frame(right)
    btn_row.pack(fill="x", pady=6)

    ttk.Button(btn_row, text="Hapus Terpilih", command=delete_selected).pack(side="left")
    ttk.Button(btn_row, text="Save All", command=save_all).pack(side="left", padx=(6, 0))

    update_listbox()
    root.mainloop()


# ----------------------------------------
#  Entry Point
# ----------------------------------------

if __name__ == "__main__":
    ensure_csv_exists()
    build_ui()
