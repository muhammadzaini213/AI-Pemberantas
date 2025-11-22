import tkinter as tk

# ================ UI ================ 
root = tk.Tk()
root.title("Tkinter Starter App")
root.geometry("400x250")

# Label
label = tk.Label(root, text="Enter your name:")
label.pack(pady=10)

# Entry
entry = tk.Entry(root)
entry.pack(pady=5)

# Output Label
output_label = tk.Label(root, text="")
output_label.pack(pady=10)

# Button
button = tk.Button(root, text="Greet")
button.pack(pady=5)


# ================ GETTER ==============
def get_name():
    """
    Mengambil data dari input window
    """
    return entry.get()


# ================ SETTER ==============
def set_output(text):
    """
    Mengupdate data di window
    """
    output_label.config(text=text)


# ================ LOGIC / EVENTS ==============
def on_greet_click():
    name = get_name()  # ambil data dari entry
    if name.strip() == "":
        set_output("Please enter your name!")
    else:
        set_output(f"Hello, {name}!")

button.config(command=on_greet_click)


# ================ RUN APP ==============
root.mainloop()
