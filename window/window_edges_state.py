import tkinter as tk
from tkinter import ttk

# ============================================
#                  UI
# ============================================
window = tk.Tk()
window.title("Edges State Configuration")
window.geometry("420x280")
window.configure(bg="#ECF0F1")

# Container Main Frame
main_frame = tk.Frame(window, bg="#E8E8E8", padx=25, pady=25)
main_frame.pack(fill="both", expand=True)

# Title
title_label = tk.Label(main_frame, text="Edges State Settings",
                       font=("Arial", 13, "bold"),
                       bg="#F5F5F5", fg="#2C3E50")
title_label.pack(anchor="w", pady=(0, 20))

# Content Frame
content_frame = tk.Frame(main_frame, bg="#FFFFFF", relief="flat", bd=1)
content_frame.pack(fill="both", expand=True)

# =====================
# Field: Edge ID
# =====================
edge_id_label = tk.Label(content_frame, text="Edges ID:", font=("Arial", 10),
                         bg="#FFFFFF", anchor="w", width=20)
edge_id_label.grid(row=0, column=0, padx=20, pady=15, sticky="w")

edge_id_var = tk.StringVar()
edge_id_entry = tk.Entry(content_frame, textvariable=edge_id_var, width=15)
edge_id_entry.grid(row=0, column=1, padx=20, pady=15, sticky="w")


# Helper utk spinbox row
def create_input_row(parent, label_text, default_value, unit, from_val, to_val, row):
    label = tk.Label(parent, text=label_text, font=("Arial", 10),
                     bg="#FFFFFF", anchor="w", width=20)
    label.grid(row=row, column=0, padx=20, pady=15, sticky="w")

    input_frame = tk.Frame(parent, bg="#FFFFFF")
    input_frame.grid(row=row, column=1, padx=20, pady=15, sticky="w")

    var = tk.StringVar(value=default_value)
    spinbox = ttk.Spinbox(
        input_frame,
        from_=from_val,
        to=to_val,
        width=8,
        textvariable=var,
        format="%02.0f",
        font=("Arial", 9)
    )
    spinbox.pack(side="left")

    unit_label = tk.Label(input_frame, text=unit, font=("Arial", 9),
                          bg="#FFFFFF", fg="#666666")
    unit_label.pack(side="left", padx=(8, 0))

    return var, spinbox


# =====================
#      Input Fields
# =====================
delay_var, delay_spinbox = create_input_row(
    content_frame, "Potensi keterlambatan:", "0", "%", 0, 100, 1
)

slowdown_var, slowdown_spinbox = create_input_row(
    content_frame, "Efek perlambatan:", "0", "km/j", 0, 200, 2
)

# Separator
separator = ttk.Separator(content_frame, orient="horizontal")
separator.grid(row=3, column=0, columnspan=2, sticky="we", padx=20, pady=10)

# Button frame
button_frame = tk.Frame(content_frame, bg="#FFFFFF")
button_frame.grid(row=4, column=0, columnspan=2, pady=15)


# ============================================
#                  GETTERS
# ============================================
def get_edge_id():
    """Mengambil ID edge."""
    return edge_id_var.get().strip()


def get_edges_state():
    """
    Mengambil seluruh nilai input:
    - edge_id
    - potensi keterlambatan
    - efek perlambatan
    """
    return {
        "edge_id": get_edge_id(),
        "potensi_keterlambatan": int(delay_var.get() or 0),
        "efek_perlambatan": int(slowdown_var.get() or 0)
    }


# ============================================
#                  SETTERS
# ============================================
def set_edge_id(value):
    """Mengisi nilai Edge ID."""
    edge_id_var.set(value)


def set_delay(value):
    """Mengupdate nilai potensi keterlambatan."""
    delay_var.set(str(value))


def set_slowdown(value):
    """Mengupdate nilai efek perlambatan."""
    slowdown_var.set(str(value))


# ============================================
#            VALIDATION & EVENTS
# ============================================
def validate_inputs():
    """Validasi spinbox agar tetap dalam range."""
    try:
        delay = int(delay_var.get())
        if delay < 0 or delay > 100:
            delay_var.set("0")
    except:
        delay_var.set("0")

    try:
        slowdown = int(slowdown_var.get())
        if slowdown < 0 or slowdown > 200:
            slowdown_var.set("0")
    except:
        slowdown_var.set("0")


def apply_settings():
    """Event klik tombol Apply."""
    validate_inputs()
    settings = get_edges_state()

    print("=== Settings Applied ===")
    print(f"Edge ID: {settings['edge_id']}")
    print(f"Potensi Keterlambatan: {settings['potensi_keterlambatan']}%")
    print(f"Efek Perlambatan: {settings['efek_perlambatan']} km/j")


# Bind validation
delay_spinbox.bind('<FocusOut>', lambda e: validate_inputs())
slowdown_spinbox.bind('<FocusOut>', lambda e: validate_inputs())

# Button
apply_btn = ttk.Button(button_frame,
                       text="Apply Settings",
                       command=apply_settings,
                       width=15)
apply_btn.pack()

# ============================================
#                  RUN
# ============================================
window.mainloop()
