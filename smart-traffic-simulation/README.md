# Smart City Adaptive Traffic Management System (Indian Left-Hand Traffic)

A Smart City Adaptive Traffic Management System built with Eclipse SUMO, Python 3, and TraCI. Configured strictly for **Indian Urban Traffic Rules (Left-Hand Traffic / LHT)**.

---

## 1. Project Overview
This project simulates real-world urban road conditions in an Indian city featuring multi-lane grid arterials, fixed-time vs. pressure-adaptive signal control, logical peak traffic periods, and multi-agency emergency vehicle priority overrides (Ambulance, Fire Engine, Police).

---

## 2. Indian Left-Hand Traffic (LHT) Design System
- **Rule System**: Left-Hand Traffic (`lefthand="true"` in SUMO `netconvert`).
- **Road Behavior**:
  - Vehicles drive on the **LEFT** side of two-way carriageways.
  - Opposing traffic travels on the opposite carriageway.
  - **Left turns**: Inner, un-crossed turns.
  - **Right turns**: Cross center junction traffic.
  - **Straight movements**: Remain on the left-side carriageway.

---

## 3. System Architecture

```
                    SUMO Simulation (LHT)
                              │
                 ┌────────────┼────────────┐
                 │            │            │
               Roads       Vehicles     Signals
                 │            │            │
                 └────────────┼────────────┘
                              │
                            TraCI
                              │
                              ▼
                      Simulation Manager
                              │
                              ▼
                       Traffic Metrics
                              │
                              ▼
                        Traffic State
                              │
                              ▼
                   Adaptive Signal Controller
                              │
                      Signal Decision
                              │
                              ▼
                            TraCI
                              │
                              ▼
                     SUMO Traffic Lights
```

---

## 4. Installation & Requirements

### System Requirements
- Windows 10/11
- Python 3.10+
- Eclipse SUMO 1.20.0+ (with `sumo`, `sumo-gui`, `netconvert`)

### Dependencies
Install standard Python dependencies:
```powershell
pip install -r requirements.txt
```

---

## 5. Windows Environment Setup Guide
Set the `SUMO_HOME` environment variable to point to your SUMO installation path:
```powershell
$env:SUMO_HOME = "C:\Program Files (x86)\Eclipse\Sumo"
$env:PATH += ";$env:SUMO_HOME\bin;$env:SUMO_HOME\tools"
```

---

## 6. Running the Simulation

Use the universal `run.py` CLI script:

### Run Adaptive Mode (Headless):
```powershell
python run.py --mode adaptive
```

### Run Adaptive Mode (GUI with `sumo-gui`):
```powershell
python run.py --mode adaptive --gui
```

### Run Fixed-Time Control Mode:
```powershell
python run.py --mode fixed
```

### Run Specific Scenario Filter (Morning / Evening Peak):
```powershell
python run.py --mode adaptive --scenario morning
python run.py --mode adaptive --scenario evening
```

### Run Fixed vs Adaptive Benchmark Comparison:
```powershell
python run.py --compare
```

---

## 7. Traffic Scenarios & Simulation Timeline

| Scenario Period | Simulation Clock | Logical Time of Day | Traffic Pattern |
|---|---|---|---|
| `MORNING_PEAK` | `0s – 180s` | 09:00 – 12:00 | Heavy inbound commute (West/North $\rightarrow$ East/South) |
| `NORMAL` | `180s – 240s` | 12:00 – 16:00 | Balanced moderate grid traffic |
| `EVENING_PEAK` | `240s – 480s` | 16:00 – 19:00 | Heavy outbound commute (East/South $\rightarrow$ West/North) |

---

## 8. Real-Time Adaptive Signal Control Algorithm

The traffic pressure formula evaluates each cardinal approach:
$$\text{Pressure}_{\text{approach}} = (1.0 \cdot \text{vehicles}) + (2.0 \cdot \text{queue}) + (0.5 \cdot \text{waiting\_time})$$

Orthogonal movement group pressures ($P_{\text{NS}}$ vs $P_{\text{EW}}$):
- $P_{\text{NS}} = P_{\text{North}} + P_{\text{South}}$
- $P_{\text{EW}} = P_{\text{East}} + P_{\text{West}}$

### Green Duration Scaling & Safety Bounds:
$$\text{Green Duration} = \text{clamp}\left(10 + (60 - 10) \cdot \frac{P_{\text{target}}}{\max(P_{\text{total}}, 1.0)}, 10, 60\right)$$
- **Minimum Green**: 10 seconds (prevents rapid signal flickering).
- **Maximum Green**: 60 seconds (prevents approach starvation).
- **Anti-Starvation**: Approaches waiting $> 90$s with queued traffic force green priority.
- **Yellow Transition**: 4 seconds safe yellow transition before switching green phases.

---

## 9. Multi-Agency Emergency Priority System

Active detection and priority routing for emergency services:
- **Fleet**: `AMBULANCE_01`, `FIRE_TRUCK_01`, `POLICE_01`, `AMBULANCE_02`.
- **Trigger**: When an emergency vehicle approaches within 150m of a signalized junction, the controller logs `[EMERGENCY DETECTED]`, executes a 4s safe yellow, and holds green for the emergency movement.
- **Clearance**: Upon entering the outbound edge, the controller logs `[EMERGENCY CLEARED]` and resumes adaptive signal control.

---

## 10. Fixed vs. Adaptive Empirical Benchmark Results

Measured side-by-side performance across 480 simulation steps under identical Indian LHT demand:

| Metric | Fixed Mode | Adaptive Mode | Empirical Improvement |
|---|---|---|---|
| **Total Vehicles Inserted** | 431 | 431 | — |
| **Throughput (Completed Trips)** | 1 | 2 | **100.0% increase** |
| **Average Waiting Time** | 3.58 sec | 0.71 sec | **80.2% reduction** |
| **Maximum Halting Queue** | 38 vehs | 17 vehs | **55.3% reduction** |
| **Average Speed** | 24.82 km/h | 32.83 km/h | **32.3% increase** |
| **Congestion Events (High/Severe)** | 947 | 114 | **88.0% reduction** |
| **Emergency Response Time** | 113.8 sec | 60.0 sec | **47.3% reduction** |

---

## 11. Decoupled Integration API (`controller/api.py`)

Python functions for connecting web dashboards or REST APIs without modifying simulation internals:

```python
from controller import (
    get_traffic_state,
    get_intersection_state,
    get_peak_period,
    get_emergency_vehicles,
    get_signal_state,
    apply_signal_decision
)

# Example API invocation
state = get_traffic_state()
print("Current Scenario Period:", get_peak_period())
print("Active Ambulances:", get_emergency_vehicles())
```

---

## 12. Output File Formats

- `output/traffic_data.csv` — Full step-by-step telemetry log.
- `output/fixed_results.csv` — Fixed-time benchmark telemetry.
- `output/adaptive_results.csv` — Adaptive mode benchmark telemetry.
- `output/latest_state.json` — Real-time JSON snapshot for external interfaces.
- `output/comparison.json` — Empirical comparison report.

---

## 13. Troubleshooting

- **SUMO_HOME Not Found**: Ensure `SUMO_HOME` environment variable is set to your Eclipse SUMO installation folder.
- **TraCI Connection Refused**: Verify no zombie `sumo.exe` processes are running in Task Manager.
- **Console Character Encoding**: Windows PowerShell handles standard output cleanly; Unicode icons are sanitized for CP1252 compatibility.

---

## 14. Future Roadmap
- Integration with FastAPI / WebSocket server for real-time web dashboard rendering.
- Connected vehicle V2X speed advisory integration.
- Public transit bus rapid transit (BRT) lane priority extensions.
