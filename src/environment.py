# ================== WINDOW ==================
APP_NAME = "Balikpapan Graph + Agent TPS/TPA"
WIDTH = 1000
HEIGHT = 800
CAM_SPEED = 10

# ================== TEST SETUP ==================
GRAPH_FILE = "./data/roadData.graphml"
NUM_AGENTS = 3
VEHICLE_SPEED = 10 # Sementara masih pake ini
NUM_TPS = 3
NUM_TPA = 0

# ================== TPS SETUP ==================
TPS_DATA = [
    {
        # "id": 1,
        "trash_per_seconds": 30,
        "extraction_cap": 300,
        "location": object # Graph nodes
    },
    {
        # "id": 2,
        "trash_per_seconds": 30,
        "extraction_cap": 300,
        "location": object # Graph nodes
    }
]

# ================== VEHICLE SETUP ==================
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