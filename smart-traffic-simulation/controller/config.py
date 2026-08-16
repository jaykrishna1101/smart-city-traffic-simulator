import os

# Base directory paths
CONTROLLER_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(CONTROLLER_DIR, ".."))

# Config & Output paths
SUMO_CONFIG_PATH = os.path.join(PROJECT_DIR, "simulation", "config", "simulation.sumocfg")
OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")
OUTPUT_CSV_PATH = os.path.join(OUTPUT_DIR, "traffic_data.csv")
OUTPUT_JSON_PATH = os.path.join(OUTPUT_DIR, "latest_state.json")

FIXED_RESULTS_CSV = os.path.join(OUTPUT_DIR, "fixed_results.csv")
ADAPTIVE_RESULTS_CSV = os.path.join(OUTPUT_DIR, "adaptive_results.csv")
COMPARISON_JSON_PATH = os.path.join(OUTPUT_DIR, "comparison.json")

# Default Control Mode ("FIXED" or "ADAPTIVE")
CONTROL_MODE = "ADAPTIVE"

# Network Intersection directional incoming edge definitions (Indian Left-Hand Traffic)
INTERSECTION_MAP = {
    "INT_NW": {
        "north": "N1_NW",
        "south": "SW_NW",
        "east": "NE_NW",
        "west": "W1_NW"
    },
    "INT_NE": {
        "north": "N2_NE",
        "south": "SE_NE",
        "east": "E1_NE",
        "west": "NW_NE"
    },
    "INT_SW": {
        "north": "NW_SW",
        "south": "S1_SW",
        "east": "SE_SW",
        "west": "W2_SW"
    },
    "INT_SE": {
        "north": "NE_SE",
        "south": "S2_SE",
        "east": "E2_SE",
        "west": "SW_SE"
    }
}

# Signal Phase Mappings to exact SUMO LHT net.xml phase indices
PHASE_MAP = {
    "INT_NW": {
        "NORTH_SOUTH": 0,
        "YELLOW_NS": 1,
        "EAST_WEST": 4,
        "YELLOW_EW": 5
    },
    "INT_NE": {
        "EAST_WEST": 0,
        "YELLOW_EW": 1,
        "NORTH_SOUTH": 4,
        "YELLOW_NS": 5
    },
    "INT_SW": {
        "NORTH_SOUTH": 0,
        "YELLOW_NS": 1,
        "EAST_WEST": 4,
        "YELLOW_EW": 5
    },
    "INT_SE": {
        "NORTH_SOUTH": 0,
        "YELLOW_NS": 1,
        "EAST_WEST": 4,
        "YELLOW_EW": 5
    }
}

# Logical Peak Period boundaries (Simulation clock seconds)
PEAK_PERIOD_BOUNDARIES = {
    "MORNING_PEAK": (0.0, 180.0),
    "NORMAL": (180.0, 240.0),
    "EVENING_PEAK": (240.0, 480.0)
}

# Configurable Congestion Thresholds
CONGESTION_LEVELS = {
    "SEVERE": {"queue": 15, "waiting_time": 45.0},
    "HIGH": {"queue": 8, "waiting_time": 25.0},
    "MEDIUM": {"queue": 3, "waiting_time": 10.0},
    "LOW": {"queue": 0, "waiting_time": 0.0}
}

# Traffic Pressure Calculation Weights
VEHICLE_WEIGHT = 1.0
QUEUE_WEIGHT = 2.0
WAITING_WEIGHT = 0.5

# Adaptive Signal Controller Parameters
MIN_GREEN_TIME = 10         # Minimum green duration (seconds)
MAX_GREEN_TIME = 60         # Maximum green duration (seconds)
YELLOW_TIME = 4             # Yellow transition duration (seconds)
STARVATION_THRESHOLD = 90.0 # Anti-starvation threshold (seconds)
EMERGENCY_TRIGGER_DIST = 150.0 # Distance to TLS for ambulance/fire/police priority
