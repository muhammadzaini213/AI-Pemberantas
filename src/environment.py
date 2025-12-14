# ================== WINDOW ==================
APP_NAME = "Simulasi Truk Sampah Balikpapan"
WIDTH = 1000
HEIGHT = 600
CAM_SPEED = 10
MAX_FPS = 60

# ================== TEST SETUP ==================
GRAPH_FILE = "./data/simpl_balikpapan_timur_drive.graphml"


# ================== VEHICLE ==================
VEHICLE_SPEED = 280
VEHICLE_CAP = 30000


# ================== SHIFT SETTINGS (00:00 WITH INTEGER 0) ==================
SIM_START = 1
SHIFT_START = 1
SHIFT_END = 13
TIME_OFFSET = 17

# ================== SPRITES ==================
NODE_COL = (255,120,120) # Node kuning
LINE_COL = (150,150,150) # Jalanan putih

AGENT_COL = (0,255,0) # Mobil Hijau
TPS_COL = (255,220,0) # TPS kuning
TPA_COL = (0,150,255) # TPA biru
GARAGE_COL = (139, 69, 19) # Garasi coklat