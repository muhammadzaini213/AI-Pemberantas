# ================== WINDOW ==================
APP_NAME = "Simulasi Truk Sampah Balikpapan"
WIDTH = 1000
HEIGHT = 800
CAM_SPEED = 10
MAX_FPS = 60

# ================== TEST SETUP ==================
GRAPH_FILE = "./data/simpl_balikpapan_drive.graphml"
NUM_VEHICLE = 10
VEHICLE_SPEED = 500 # Sementara masih pake ini
NUM_TPS = 7
NUM_TPA = 2
NUM_GARAGE = 3

# ================== TPS SETUP ==================
TPS_DATA = [
    {
        # "id": 1,
        "trash_per_day": 30,
        "extraction_cap": 300, # Ini nanti kita random per hari, jadi cuma titik tengahnya aja
        "location": object # Graph nodes
    },
    {
        # "id": 2,
        "trash_per_day": 30,
        "extraction_cap": 300,
        "location": object # Graph nodes
    }
]

# ================== VEHICLE SETUP ==================
OPERATIONAL_TIME = 5000 # Nanti ikutin jam operasionalnya
VEHICLE_DATA = [
    {
        # "id": 1,
        "capacity": 200,
        "speed": 30,
        "fuel": 100,
    },
    {
        # "id": 2,
        "capacity": 200,
        "speed": 30,
        "fuel": 100,
    }
]

# ================== SPRITES ==================
NODE_COL = (255,120,120) # Node kuning
LINE_COL = (150,150,150) # Jalanan putih

AGENT_COL = (0,255,0) # Mobil Hijau
TPS_COL = (255,220,0) # TPS kuning
TPA_COL = (0,150,255) # TPA biru
GARAGE_COL = (139, 69, 19) # Garasi coklat