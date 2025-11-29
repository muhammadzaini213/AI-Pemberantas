# ================== WINDOW ==================
APP_NAME = "Simulasi Truk Sampah Balikpapan"
WIDTH = 1000
HEIGHT = 800
CAM_SPEED = 10
MAX_FPS = 60

# ================== TEST SETUP ==================
GRAPH_FILE = "./data/simpl_klandasan_ilir_drive.graphml"
VEHICLE_SPEED = 60 # Sementara masih pake ini

# ===== Shift Settings =====
SHIFT_START = 6  # 06:00 - Truk mulai beroperasi
SHIFT_END = 22   # 22:00 - Truk kembali ke garasi

# ================== SPRITES ==================
NODE_COL = (255,120,120) # Node kuning
LINE_COL = (150,150,150) # Jalanan putih

AGENT_COL = (0,255,0) # Mobil Hijau
TPS_COL = (255,220,0) # TPS kuning
TPA_COL = (0,150,255) # TPA biru
GARAGE_COL = (139, 69, 19) # Garasi coklat