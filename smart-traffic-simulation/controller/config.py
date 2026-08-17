import os

# Base directory paths
CONTROLLER_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(CONTROLLER_DIR, ".."))

# Scenario Metadata & Paths
SCENARIO_NAME = "CHATRAPATI_RING_ROAD"
SCENARIO_DIR = os.path.join(PROJECT_DIR, "2026-08-16-19-51-46")
SUMO_CONFIG_PATH = os.path.join(SCENARIO_DIR, "osm.sumocfg")

OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")
OUTPUT_CSV_PATH = os.path.join(OUTPUT_DIR, "traffic_data.csv")
OUTPUT_JSON_PATH = os.path.join(OUTPUT_DIR, "latest_state.json")

FIXED_RESULTS_CSV = os.path.join(OUTPUT_DIR, "fixed_results.csv")
ADAPTIVE_RESULTS_CSV = os.path.join(OUTPUT_DIR, "adaptive_results.csv")
COMPARISON_JSON_PATH = os.path.join(OUTPUT_DIR, "comparison.json")

# Default Control Mode ("FIXED" or "ADAPTIVE")
CONTROL_MODE = "ADAPTIVE"

# Logical Peak Period boundaries (Simulation clock seconds)
# Peak Hours:
# 09:00 - 12:00 -> MORNING_PEAK (0s - 180s in demo clock)
# 12:00 - 16:00 -> NORMAL       (180s - 240s in demo clock)
# 16:00 - 19:00 -> EVENING_PEAK (240s - 480s in demo clock)
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
# MIN_GREEN_TIME must be >= the largest minDur in the OSM actuated signal programs
# (osm.net.xml shows minDur values of 13s-16s; setting to 16s prevents premature switching)
MIN_GREEN_TIME = 16         # Minimum green duration (seconds) — matches OSM minDur=16s
MAX_GREEN_TIME = 90         # Maximum green duration (seconds)
YELLOW_TIME = 6             # Yellow transition duration (seconds) — matches OSM yellow phases
STARVATION_THRESHOLD = 60.0 # Anti-starvation threshold (seconds) — faster starvation relief
EMERGENCY_TRIGGER_DIST = 200.0 # Distance to TLS for ambulance/fire/police priority
