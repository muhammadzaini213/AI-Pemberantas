import pygame
from ..environment import WIDTH, HEIGHT, TPA_COL, TPS_COL, GARAGE_COL
import math

class GraphViewer:
    def __init__(self, pos_dict, shared, width=WIDTH, height=HEIGHT, node_size=2):
        self.pos = pos_dict
        self.shared = shared
        self.WIDTH = width
        self.HEIGHT = height
        self.NODE_SIZE = node_size
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0

        self.min_x = min(p[0] for p in pos_dict.values())
        self.max_x = max(p[0] for p in pos_dict.values())
        self.min_y = min(p[1] for p in pos_dict.values())
        self.max_y = max(p[1] for p in pos_dict.values())

        self.cache = {}
        self.last_scale = None
        self.last_offx = None
        self.last_offy = None

    def transform(self, x, y):
        px = (x - self.min_x) * self.scale + self.offset_x
        py = (self.max_y - y) * self.scale + self.offset_y
        return int(px), int(py)

    def transform_cached(self, node):
        x, y = self.pos[node]

        if (self.scale != self.last_scale or
            self.offset_x != self.last_offx or
            self.offset_y != self.last_offy):
            self.cache = {}

        if node in self.cache:
            return self.cache[node]

        screen_pos = self.transform(x, y)
        self.cache[node] = screen_pos
        return screen_pos

    def finish_frame(self):
        self.last_scale = self.scale
        self.last_offx = self.offset_x
        self.last_offy = self.offset_y

    def draw_arrow(self, screen, color, start_pos, end_pos, width=2, arrow_size=8):
        x1, y1 = start_pos
        x2, y2 = end_pos
        
        pygame.draw.line(screen, color, start_pos, end_pos, width)
        
        angle = math.atan2(y2 - y1, x2 - x1)
        
        arrow_length = arrow_size
        arrow_angle = math.pi / 6
        
        left_x = x2 - arrow_length * math.cos(angle - arrow_angle)
        left_y = y2 - arrow_length * math.sin(angle - arrow_angle)
        
        right_x = x2 - arrow_length * math.cos(angle + arrow_angle)
        right_y = y2 - arrow_length * math.sin(angle + arrow_angle)
        
        pygame.draw.polygon(screen, color, [(x2, y2), (left_x, left_y), (right_x, right_y)])

    def draw_graph(self, screen, G, default_color, edge_color):
        for u, v in G.edges():
            x1, y1 = self.transform_cached(u)
            x2, y2 = self.transform_cached(v)

            if (x1 < -10 and x2 < -10) or (x1 > self.WIDTH+10 and x2 > self.WIDTH+10):
                continue
            if (y1 < -10 and y2 < -10) or (y1 > self.HEIGHT+10 and y2 > self.HEIGHT+10):
                continue

            edge_id = f"{u}-{v}"
            edge_data = self.shared.edge_type.get(edge_id, None)
            
            if edge_data and edge_data.get("slowdown", 0) > 0:
                color = (255, 0, 0)
                width = 5
            else:
                color = edge_color
                width = 2

            self.draw_arrow(screen, color, (x1, y1), (x2, y2), width)

        for n in G.nodes():
            x, y = self.transform_cached(n)

            if not (-10 <= x <= self.WIDTH+10 and -10 <= y <= self.HEIGHT+10):
                continue

            flags = self.shared.node_type.get(n, None)

            if flags:
                if flags["tps"]:
                    color = TPS_COL
                    radius = 3
                elif flags["tpa"]:
                    color = TPA_COL
                    radius = 4
                elif flags["garage"]:
                    color = GARAGE_COL
                    radius = 5
                else:
                    color = default_color
                    radius = self.NODE_SIZE
            else:
                color = default_color
                radius = self.NODE_SIZE

            pygame.draw.circle(screen, color, (x, y), radius)

    def draw_dynamic_objects(self, screen, vehicles):
        for vehicle in vehicles:
            x, y = vehicle.get_pos(self.pos)
            ax, ay = self.transform(x, y)
            if -6 <= ax <= self.WIDTH + 6 and -6 <= ay <= self.HEIGHT + 6:
                pygame.draw.circle(screen, (0,255,0), (ax, ay), 6)

    def get_node_at_pos(self, mx, my):
        for n in self.pos:
            x, y = self.transform_cached(n)
            r = 6
            if abs(mx - x) <= r and abs(my - y) <= r:
                return n
        return None

    def get_vehicle_at_pos(self, mx, my, vehicles):
        for vehicle in vehicles:
            x, y = vehicle.get_pos(self.pos)
            ax, ay = self.transform(x, y)
            r = 8
            if abs(mx - ax) <= r and abs(my - ay) <= r:
                return vehicle
        return None

    def get_edge_screen_pos(self, u, v):
        x1, y1 = self.transform_cached(u)
        x2, y2 = self.transform_cached(v)
        return x1, y1, x2, y2

    def get_edge_at_pos(self, mx, my):
        TOL = 5
        for u, v in self.pos.keys():
            x1, y1, x2, y2 = self.get_edge_screen_pos(u, v)
            if self._point_near_line(mx, my, x1, y1, x2, y2, TOL):
                return (u, v)
        return None

    def _point_near_line(self, px, py, x1, y1, x2, y2, tol):
        if x1 == x2 and y1 == y2:
            dist = ((px - x1)**2 + (py - y1)**2)**0.5
            return dist <= tol
        else:
            t = max(0, min(1, ((px-x1)*(x2-x1) + (py-y1)*(y2-y1)) / ((x2-x1)**2 + (y2-y1)**2)))
            proj_x = x1 + t * (x2 - x1)
            proj_y = y1 + t * (y2 - y1)
            dist = ((px - proj_x)**2 + (py - proj_y)**2)**0.5
            return dist <= tol
        
    def handle_mouse_click(self, mouse_pos, G=None, vehicles=None):
        shared = self.shared
        if not shared.paused:
            return

        mx, my = mouse_pos

        if vehicles is None and hasattr(shared, 'vehicles'):
            vehicles = shared.vehicles

        if vehicles is not None:
            print(f"[DEBUG] vehicles list ada, len={len(vehicles)}")
            vehicle = self.get_vehicle_at_pos(mx, my, vehicles)
            print(f"[DEBUG] get_vehicle_at_pos returned: {vehicle}")
            
            if vehicle is not None:
                print("cliks")
                car_id = getattr(vehicle, 'id', None) or getattr(vehicle, 'car_id', None)
                print(f"[DEBUG] car_id found: {car_id}")
                print(f"[DEBUG] has car_state_window: {hasattr(shared, 'car_state_window')}")
                print(f"[DEBUG] car_state_window value: {getattr(shared, 'car_state_window', None)}")
                
                if car_id is not None and hasattr(shared, "car_state_window") and shared.car_state_window:
                    car_data = {
                        "garage_node": getattr(vehicle, 'garage_node', ""),
                        "state": getattr(vehicle, 'state', "Idle"),
                        "speed": getattr(vehicle, 'speed', 0),
                        "daily_dist": getattr(vehicle, 'daily_dist', 0),
                        "total_dist": getattr(vehicle, 'total_dist', 0),
                        "load": getattr(vehicle, 'load', 0),
                        "max_load": getattr(vehicle, 'max_load', 1000),
                        "route": getattr(vehicle, 'route', [])
                    }
                    shared.car_state_window.set_car(car_id, car_data)
                    print(f"[DEBUG] Car state window SET for {car_id}")
                else:
                    print(f"[DEBUG] Condition failed - car_id:{car_id}, has_window:{hasattr(shared, 'car_state_window')}, window_value:{getattr(shared, 'car_state_window', None)}")

        node = self.get_node_at_pos(mx, my)
        if node is not None:
            print(f"[DEBUG] Node diklik: {node}")
            if node not in shared.node_type:
                shared.node_type[node] = {
                    "tps": False,
                    "tpa": False,
                    "garage": False,
                    "tps_data": {"nama": "", "sampah_kg":0, "sampah_hari_ini":0, "dilayanin":False},
                    "tpa_data": {"nama": "TPA", "total_sampah": 0},
                    "garage_data": {"nama": "Garage", "total_armada": 0, "armada_bertugas": 0, "armada_standby": 0}
                }

            node_info = shared.node_type[node]

            if node_info.get("tps", False) and hasattr(shared, "tps_state_window") and shared.tps_state_window:
                tps_data = node_info.get("tps_data", {
                    "nama": "",
                    "sampah_kg": 0,
                    "sampah_hari_ini": 0,
                    "dilayanin": False
                })
                shared.tps_state_window.set_node(node, tps_data)

            elif node_info.get("tpa", False) and hasattr(shared, "tpa_state_window") and shared.tpa_state_window:
                tpa_data = node_info.get("tpa_data", {
                    "nama": "TPA",
                    "total_sampah": 0
                })
                shared.tpa_state_window.set_node(node, tpa_data)

            elif node_info.get("garage", False) and hasattr(shared, "garage_state_window") and shared.garage_state_window:
                garage_data = node_info.get("garage_data", {
                    "nama": "Garage",
                    "total_armada": 0,
                })
                shared.garage_state_window.set_node(node, garage_data)

            else:
                if hasattr(shared, "node_state_window") and shared.node_state_window:
                    shared.node_state_window.set_node(node, shared.node_type[node])

            return

        if G is not None:
            for u, v in G.edges():
                x1, y1, x2, y2 = self.get_edge_screen_pos(u, v)
                if self._point_near_line(mx, my, x1, y1, x2, y2, tol=5):
                    print(f"[DEBUG] Edge diklik: {u}-{v}")
                    edge_id = f"{u}-{v}"
                    if edge_id not in shared.edge_type:
                        shared.edge_type[edge_id] = {"slowdown": 0}
                    if hasattr(shared, "edge_state_window") and shared.edge_state_window:
                        shared.edge_state_window.set_edge(edge_id, shared.edge_type[edge_id])
                    break