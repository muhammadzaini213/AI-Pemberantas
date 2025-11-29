import tkinter as tk
from tkinter import ttk, messagebox

class CarStateWindow:
    def __init__(self, master=None):
        if master is None:
            self.root = tk.Tk()
        else:
            self.root = tk.Toplevel(master)

        self.root.title("Car State - Truk Sampah Balikpapan")
        self.root.geometry("400x580")
        self.shared = None 

        frm = ttk.Frame(self.root, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="ID Kendaraan:").grid(row=0, column=0, sticky="w")
        self.car_id_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.car_id_var, width=30, state="readonly").grid(row=1, column=0, pady=(0, 10))

        ttk.Label(frm, text="Garage Node ID:").grid(row=2, column=0, sticky="w")
        self.garage_node_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.garage_node_var, width=30).grid(row=3, column=0, pady=(0, 10))

        ttk.Label(frm, text="State:").grid(row=4, column=0, sticky="w")
        self.state_var = tk.StringVar(value="Idle")
        state_options = ["Idle", "Moving", "Loading", "Unloading", "Stuck", "Standby"]
        ttk.Combobox(frm, textvariable=self.state_var, values=state_options, state="readonly", width=28).grid(row=5, column=0, pady=(0, 10))

        ttk.Label(frm, text="Speed (km/j):").grid(row=6, column=0, sticky="w")
        self.speed_var = tk.StringVar(value="0")
        ttk.Entry(frm, textvariable=self.speed_var, width=30).grid(row=7, column=0, pady=(0, 10))

        ttk.Label(frm, text="Trip Hari Ini (km):").grid(row=8, column=0, sticky="w")
        self.daily_dist_var = tk.StringVar(value="0")
        ttk.Entry(frm, textvariable=self.daily_dist_var, width=30, state="readonly").grid(row=9, column=0, pady=(0, 10))

        ttk.Label(frm, text="Total Odometer (km):").grid(row=10, column=0, sticky="w")
        self.total_dist_var = tk.StringVar(value="0")
        ttk.Entry(frm, textvariable=self.total_dist_var, width=30, state="readonly").grid(row=11, column=0, pady=(0, 10))

        ttk.Label(frm, text="Muatan (kg):").grid(row=12, column=0, sticky="w")
        self.load_var = tk.StringVar(value="0")
        ttk.Entry(frm, textvariable=self.load_var, width=30).grid(row=13, column=0, pady=(0, 10))

        ttk.Label(frm, text="Muatan Maksimum (kg):").grid(row=14, column=0, sticky="w")
        self.max_load_var = tk.StringVar(value="1000")
        ttk.Entry(frm, textvariable=self.max_load_var, width=30).grid(row=15, column=0, pady=(0, 10))

        ttk.Label(frm, text="List Node Rute (pisahkan dengan koma):").grid(row=16, column=0, sticky="w")
        
        text_frame = ttk.Frame(frm)
        text_frame.grid(row=17, column=0, pady=(0, 10), sticky="ew")
        
        self.route_text = tk.Text(text_frame, width=30, height=4, wrap="word")
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.route_text.yview)
        self.route_text.configure(yscrollcommand=scrollbar.set)
        
        self.route_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.save_btn = ttk.Button(frm, text="Simpan Data Truk", command=self.on_save)
        self.save_btn.grid(row=18, column=0, sticky="ew")


    # ============== SHARED ==============
    def attach_shared(self, shared):
        self.shared = shared
        shared.car_state_window = self



    # ============== SETTERS ==============
    def set_car(self, car_id, data=None):
        self.car_id_var.set(str(car_id))
        
        if data is None:
            data = {}

        self.garage_node_var.set(str(data.get("garage_node", "")))
        self.state_var.set(data.get("state", "Idle"))
        self.speed_var.set(str(data.get("speed", 0)))
        self.daily_dist_var.set(str(data.get("daily_dist", 0)))
        self.total_dist_var.set(str(data.get("total_dist", 0)))
        self.load_var.set(str(data.get("load", 0)))
        self.max_load_var.set(str(data.get("max_load", 1000)))
        
        route = data.get("route", [])
        if isinstance(route, list):
            route_str = ", ".join(map(str, route))
        else:
            route_str = str(route)
        
        self.route_text.delete("1.0", "end")
        self.route_text.insert("1.0", route_str)

    # ============== LOGIC ==============
    def validate_inputs(self):
        if self.car_id_var.get().strip() == "":
            return False

        try:
            speed_val = float(self.speed_var.get())
            if speed_val < 0:
                self.speed_var.set("0")
        except:
            return False

        try:
            daily_val = float(self.daily_dist_var.get())
            if daily_val < 0:
                self.daily_dist_var.set("0")
        except:
            return False

        try:
            total_val = float(self.total_dist_var.get())
            if total_val < 0:
                self.total_dist_var.set("0")
        except:
            return False

        try:
            load_val = float(self.load_var.get())
            if load_val < 0:
                self.load_var.set("0")
        except:
            return False

        try:
            max_load_val = float(self.max_load_var.get())
            if max_load_val < 0:
                self.max_load_var.set("0")
        except:
            return False

        if float(self.load_var.get()) > float(self.max_load_var.get()):
            return False

        return True

    def on_save(self):
            if not self.validate_inputs():
                messagebox.showerror("Error", "Data tidak valid! Periksa kembali input Anda.")
                return

            car_id = self.car_id_var.get().strip()

            route_str = self.route_text.get("1.0", "end").strip()
            route_list = []
            if route_str:
                route_list = [node.strip() for node in route_str.split(",") if node.strip()]

            data = {
                "garage_node": self.garage_node_var.get().strip(),
                "state": self.state_var.get(),
                "speed": float(self.speed_var.get() or 0),
                "daily_dist": float(self.daily_dist_var.get() or 0),
                "total_dist": float(self.total_dist_var.get() or 0),
                "load": float(self.load_var.get() or 0),
                "max_load": float(self.max_load_var.get() or 1000),
                "route": route_list
            }

            if self.shared and hasattr(self.shared, 'vehicles'):
                vehicle_found = False
                for vehicle in self.shared.vehicles:
                    if vehicle.id == car_id:
                        vehicle_found = True
                        
                        old_state = vehicle.state
                        
                        state_mapping = {
                            "Idle": "idle",
                            "Moving": "random",
                            "Loading": "at_tps",
                            "Unloading": "at_tpa",
                            "Stuck": "idle",
                            "Standby": "idle"
                        }
                        vehicle.state = state_mapping.get(data["state"], "idle")
                        
                        new_garage = data["garage_node"]
                        if new_garage and new_garage != vehicle.garage_node:
                            vehicle.update_garage_assignment(new_garage)
                        
                        vehicle.daily_dist = data["daily_dist"]
                        vehicle.total_dist = data["total_dist"]
                        
                        vehicle.load = data["load"]
                        vehicle.max_load = data["max_load"]
                        
                        if data["speed"] > 0:
                            vehicle.speed = data["speed"]
                        
                        if route_list:
                            vehicle.route = route_list
                        
                        if old_state != vehicle.state:
                            vehicle._update_state_in_garage_stats(old_state)
                        
                        print(f"\n--- Vehicle {car_id} UPDATED ---")
                        print(f"State: {old_state} -> {vehicle.state}")
                        print(f"Garage: {vehicle.garage_node}")
                        print(f"Load: {vehicle.load}/{vehicle.max_load} kg")
                        print(f"Daily Distance: {vehicle.daily_dist} km")
                        print(f"Total Distance: {vehicle.total_dist} km")
                        print(f"Route: {vehicle.route}")
                        
                        messagebox.showinfo("Berhasil", 
                            f"Kendaraan {car_id} berhasil diupdate!\n\n"
                            f"State: {vehicle.state}\n"
                            f"Load: {vehicle.load}/{vehicle.max_load} kg\n"
                            f"Route nodes: {len(route_list)}")
                        break
                
                if not vehicle_found:
                    messagebox.showerror("Error", f"Kendaraan dengan ID {car_id} tidak ditemukan!")
            else:
                messagebox.showerror("Error", "Shared data tidak tersedia!")

    def run(self):
        self.root.mainloop()