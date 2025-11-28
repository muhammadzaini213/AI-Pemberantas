import pygame
from ..environment import WIDTH, HEIGHT, TPA_COL, TPS_COL, GARAGE_COL

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

        # range
        self.min_x = min(p[0] for p in pos_dict.values())
        self.max_x = max(p[0] for p in pos_dict.values())
        self.min_y = min(p[1] for p in pos_dict.values())
        self.max_y = max(p[1] for p in pos_dict.values())

        # === CACHE SCREEN COORDINATES ===
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

        # bila scale/offset berubah → invalidate cache
        if (self.scale != self.last_scale or
            self.offset_x != self.last_offx or
            self.offset_y != self.last_offy):
            self.cache = {}

        # jika sudah ada cache, pakai
        if node in self.cache:
            return self.cache[node]

        # compute baru
        screen_pos = self.transform(x, y)
        self.cache[node] = screen_pos
        return screen_pos

    def finish_frame(self):
        self.last_scale = self.scale
        self.last_offx = self.offset_x
        self.last_offy = self.offset_y

    # Draw edges + nodes + culling
    def draw_graph(self, screen, G, default_color, edge_color):
        # ==== Draw edges ====
        for u, v in G.edges():
            x1, y1 = self.transform_cached(u)
            x2, y2 = self.transform_cached(v)

            if (x1 < -10 and x2 < -10) or (x1 > self.WIDTH+10 and x2 > self.WIDTH+10):
                continue
            if (y1 < -10 and y2 < -10) or (y1 > self.HEIGHT+10 and y2 > self.HEIGHT+10):
                continue

            pygame.draw.line(screen, edge_color, (x1, y1), (x2, y2), 2)

        # ==== Draw nodes ====
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
            r = 6  # radius toleransi klik
            if abs(mx - x) <= r and abs(my - y) <= r:
                return n
        return None

    def get_edge_screen_pos(self, u, v):
        """Ambil posisi layar dari dua node edge"""
        x1, y1 = self.transform_cached(u)
        x2, y2 = self.transform_cached(v)
        return x1, y1, x2, y2

    def get_edge_at_pos(self, mx, my):
        """
        Deteksi apakah klik berada dekat salah satu edge.
        Return tuple (u,v) jika ada, else None.
        """
        TOL = 5  # toleransi klik
        for u, v in self.pos.keys():  # <-- nanti ganti dengan G.edges() saat draw
            x1, y1, x2, y2 = self.get_edge_screen_pos(u, v)
            # hitung jarak titik ke garis (u,v)
            if self._point_near_line(mx, my, x1, y1, x2, y2, TOL):
                return (u, v)
        return None

    def _point_near_line(self, px, py, x1, y1, x2, y2, tol):
        """Cek apakah titik (px,py) dekat garis (x1,y1)-(x2,y2)"""
        # jarak titik ke garis
        if x1 == x2 and y1 == y2:
            # edge berupa titik (sangat kecil)
            dist = ((px - x1)**2 + (py - y1)**2)**0.5
            return dist <= tol
        else:
            # proyeksi titik ke garis
            t = max(0, min(1, ((px-x1)*(x2-x1) + (py-y1)*(y2-y1)) / ((x2-x1)**2 + (y2-y1)**2)))
            proj_x = x1 + t * (x2 - x1)
            proj_y = y1 + t * (y2 - y1)
            dist = ((px - proj_x)**2 + (py - proj_y)**2)**0.5
            return dist <= tol
        
    def handle_mouse_click(self, mouse_pos, G=None):
        shared = self.shared
        if not shared.paused:
            return

        mx, my = mouse_pos

        # ==== Node click ====
        node = self.get_node_at_pos(mx, my)
        if node is not None:
            # pastikan node_type ada
            if node not in shared.node_type:
                shared.node_type[node] = {
                    "tps": False,
                    "tpa": False,
                    "garage": False,
                    "tps_data": {"nama": "", "sampah_kg":0, "sampah_hari_ini":0, "dilayanin":False}
                }

            # Ambil data TPS dari node_type
            tps_data = shared.node_type[node].get("tps_data", None)
            if hasattr(shared, "tps_state_window") and shared.tps_state_window:
                shared.tps_state_window.set_node(node, tps_data)

            # NodeStateWindow tetap update flags
            if hasattr(shared, "node_state_window") and shared.node_state_window:
                shared.node_state_window.set_node(node, shared.node_type[node])


            return  # node diklik → return

        # ==== Edge click ====
        if G is not None:
            for u, v in G.edges():
                x1, y1, x2, y2 = self.get_edge_screen_pos(u, v)
                if self._point_near_line(mx, my, x1, y1, x2, y2, tol=5):
                    edge_id = f"{u}-{v}"
                    if edge_id not in shared.edge_type:
                        shared.edge_type[edge_id] = {"delay": 0, "slowdown": 0}
                    if hasattr(shared, "edge_state_window") and shared.edge_state_window:
                        shared.edge_state_window.set_edge(edge_id, shared.edge_type[edge_id])
                    break
