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

    def draw_arrow_fast(self, screen, color, x1, y1, x2, y2, width, draw_head=True):
        """
        Faster arrow drawing. If draw_head=False, only draw a line.
        Width and arrow size should already be adapted to current scale.
        """
        # draw main line (always)
        pygame.draw.line(screen, color, (x1, y1), (x2, y2), max(1, int(width)))

        if not draw_head:
            return

        # light trig only when needed
        dx = x2 - x1
        dy = y2 - y1
        length = (dx*dx + dy*dy) ** 0.5
        if length < 1:
            return

        ux = dx / length
        uy = dy / length

        # arrow size proportional to width (already scaled)
        size = max(3, 4 + int(width))
        px = -uy
        py = ux

        p1 = (x2, y2)
        p2 = (x2 - ux*size + px*size*0.5, y2 - uy*size + py*size*0.5)
        p3 = (x2 - ux*size - px*size*0.5, y2 - uy*size - py*size*0.5)

        # integer coords for polygon
        pygame.draw.polygon(screen, color, ( (int(p1[0]),int(p1[1])), (int(p2[0]),int(p2[1])), (int(p3[0]),int(p3[1])) ))


    def draw_graph(self, screen, G, default_color, edge_color):

        # cache coords
        if not hasattr(self, "_coord_cache"):
            self._coord_cache = {}
        self._coord_cache.clear()
        for n in G.nodes():
            self._coord_cache[n] = self.transform_cached(n)

        scale = max(self.scale, 1e-9)

        # ----- ARROW RULES -----
        ARROW_MIN_SCALE = 3      # arrow hanya muncul di zoom sangat dekat
        ARROW_MIN_LEN_PX = 150       # jarak layar minimal untuk munculkan arrow


        for u, v in G.edges():
            x1, y1 = self._coord_cache[u]
            x2, y2 = self._coord_cache[v]

            # skip if offscreen
            if (max(x1, x2) < -15 or min(x1, x2) > self.WIDTH + 15 or
                max(y1, y2) < -15 or min(y1, y2) > self.HEIGHT + 15):
                continue

            # edge length on screen
            dx = x2 - x1
            dy = y2 - y1
            onscreen_len = (dx*dx + dy*dy) ** 0.5

            # get edge style
            edge_id = f"{u}-{v}"
            e = self.shared.edge_type.get(edge_id)
            is_slow = e and e.get("slowdown", 0) > 0
            color = (255, 0, 0) if is_slow else edge_color

            # width scales with zoom
            base_width = 1 if not is_slow else 2
            width = max(1, int(base_width * min(1.0, scale * 1.4)))

            # -------------------------
            #  SHOULD DRAW ARROWHEAD?
            # -------------------------
            draw_head = (
                scale >= ARROW_MIN_SCALE and
                onscreen_len >= ARROW_MIN_LEN_PX
            )

            # always draw the line
            self.draw_arrow_fast(screen, color, x1, y1, x2, y2, width, draw_head=draw_head)

        # ----- draw important nodes only -----
        for n in G.nodes():
            x, y = self._coord_cache[n]
            if not (-10 <= x <= self.WIDTH+10 and -10 <= y <= self.HEIGHT+10):
                continue

            flags = self.shared.node_type.get(n)
            if not flags:
                continue

            if flags.get("tps"):
                pygame.draw.circle(screen, TPS_COL, (x, y), 3)
            elif flags.get("tpa"):
                pygame.draw.circle(screen, TPA_COL, (x, y), 4)
            elif flags.get("garage"):
                pygame.draw.circle(screen, GARAGE_COL, (x, y), 5)


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