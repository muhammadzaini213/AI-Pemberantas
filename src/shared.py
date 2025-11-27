class SharedState:
    def __init__(self):
        self.fps = 0
        self.sim_hour = 8
        self.sim_min = 0
        self.sim_day = 1
        self.speed = 1.0
        self.paused = False

    def on_refresh(self):
        self.validate_time()

        time_tuple, day = self.get_simulation_time()
        hour, minute = time_tuple.split(":")

        self.shared.sim_hour = int(hour)
        self.shared.sim_min = int(minute)
        self.shared.sim_day = int(day)

        # speed
        s = self.get_simulation_speed()
        self.shared.speed = float(s.replace("x", ""))

        # pause
        self.shared.paused = self.get_pause_state()
