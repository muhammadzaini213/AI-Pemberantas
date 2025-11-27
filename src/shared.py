class SharedState:
    def __init__(self):
        self.fps = 0
        self.sim_hour = 8
        self.sim_min = 0
        self.sim_day = 1
        self.speed = 1.0
        self.paused = False
        self.node_state_window = None

        # === TIPE NODE (TPS / TPA / GARAGE) ===
        self.node_type = {}   # node_id → { "tps": bool, "tpa": bool, "garage": bool }

    def init_node_types(self, G, tps_nodes, tpa_nodes, garage_nodes):
        """
        Dipanggil sekali setelah graph di-load dan node khusus telah dihitung.
        """
        self.node_type = {
            n: {
                "tps": n in tps_nodes,
                "tpa": n in tpa_nodes,
                "garage": n in garage_nodes
            }
            for n in G.nodes()
        }

    def on_refresh(self):
        self.validate_time()

        time_tuple, day = self.get_simulation_time()
        hour, minute = time_tuple.split(":")

        self.sim_hour = int(hour)
        self.sim_min = int(minute)
        self.sim_day = int(day)

        s = self.get_simulation_speed()
        self.speed = float(s.replace("x", ""))

        self.paused = self.get_pause_state()
