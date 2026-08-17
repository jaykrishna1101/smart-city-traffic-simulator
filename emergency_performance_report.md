# Fixed vs Adaptive Emergency Vehicle Performance Report
**Scenario:** Chatrapati–Ring Road, Nagpur, India  
**Traffic Rules:** Indian Left-Hand Traffic (LHT)  
**Simulation Platform:** SUMO 1.27.1 + Python / TraCI  
**Random Seed:** 42 | **Evaluation Window:** 350.0s  

---

## 1. Executive Summary

This report evaluates the performance of **Emergency Vehicle Priority Management** under two distinct traffic control paradigms across identical network geometry, traffic demand, and emergency departure schedules:

1. **Fixed Mode (Conventional Control)**: Standard fixed/actuated signal timing with no emergency priority preemption. Emergency vehicles must queue behind normal traffic and obey red lights.
2. **Adaptive Mode + Emergency Priority**: Dynamic traffic-pressure-based signal control with topology-aware emergency priority preemption. The system detects approaching emergency vehicles, executes safe green phase transitions (`EMERGENCY_GREEN`), clears the intersection, and seamlessly restores adaptive control.

### Key Results
- **Response Time Reduction**: Emergency vehicles arrived **26.7% faster** overall (up to **38.3% faster** for Ambulance).
- **Waiting Time Elimination**: Emergency intersection waiting time was reduced by **92.0%** across all vehicles (100% eliminated for Ambulance and Police).
- **Travel Speed**: Average emergency cruising speed increased by **+38.3%** (from 33.8 km/h to 46.8 km/h).
- **General Traffic Coexistence**: General traffic waiting time also decreased (from 7.72s to 3.81s) due to adaptive pressure balancing before and after priority overrides.

---

## 2. Emergency Vehicle Performance Breakdown

| Metric | Fixed Control (No Priority) | Adaptive + Emergency Priority | Performance Gain | Status |
|---|---|---|---|---|
| **Average Response / Travel Time** | **65.0 s** | **47.7 s** | **▼ 26.7% reduction** | ✅ Significant Improvement |
| **Average Waiting Time at Signals** | **8.33 s** | **0.67 s** | **▼ 92.0% reduction** | ✅ Near-Zero Signal Delay |
| **Average Time Loss (Delay)** | **30.10 s** | **12.96 s** | **▼ 56.9% reduction** | ✅ Substantial Flow Efficiency |
| **Average Emergency Speed** | **33.84 km/h** | **46.79 km/h** | **▲ +38.3% increase** | ✅ Faster Transit |

---

## 3. Individual Emergency Vehicle Analysis

### 🚑 Ambulance (`AMBULANCE_NAGPUR`)
- **Route:** `route_AMBULANCE_DEMO` (560.3 m, 10 edges)
- **Target Intersection:** `cluster_2683490416_2683507646_2683507647_2684658305_#2more`
- **Departure Time:** `t = 50.0 s`

| Metric | Fixed Control | Adaptive + Priority | Improvement |
|---|---|---|---|
| Travel Duration | 60.0 s | 37.0 s | **▼ 38.3% faster** |
| Waiting Time at Red Signals | 18.0 s | 0.0 s | **▼ 100.0% eliminated** |
| Time Loss / Delay | 30.18 s | 6.99 s | **▼ 76.8% reduction** |
| Average Speed | 33.07 km/h | 53.68 km/h | **▲ +62.3% increase** |
| Full Stops Count | 19 | 1 | **▼ 94.7% reduction** |

---

### 🚓 Police Cruiser (`POLICE_NAGPUR`)
- **Route:** `route_POLICE_DEMO` (692.9 m, 11 edges)
- **Target Intersection:** `cluster_2683490405_298938456`
- **Departure Time:** `t = 150.0 s`

| Metric | Fixed Control | Adaptive + Priority | Improvement |
|---|---|---|---|
| Travel Duration | 68.0 s | 50.0 s | **▼ 26.5% faster** |
| Waiting Time at Red Signals | 3.0 s | 0.0 s | **▼ 100.0% eliminated** |
| Time Loss / Delay | 31.52 s | 14.14 s | **▼ 55.1% reduction** |
| Average Speed | 36.29 km/h | 48.59 km/h | **▲ +33.9% increase** |
| Full Stops Count | 4 | 1 | **▼ 75.0% reduction** |

---

### 🚒 Fire Truck (`FIRETRUCK_NAGPUR`)
- **Route:** `route_FIRETRUCK_DEMO` (612.7 m, 9 edges)
- **Target Intersection:** `cluster_2683490405_298938456`
- **Departure Time:** `t = 250.0 s`

| Metric | Fixed Control | Adaptive + Priority | Improvement |
|---|---|---|---|
| Travel Duration | 67.0 s | 56.0 s | **▼ 16.4% faster** |
| Waiting Time at Red Signals | 4.0 s | 2.0 s | **▼ 50.0% reduction** |
| Time Loss / Delay | 28.60 s | 17.76 s | **▼ 37.9% reduction** |
| Average Speed | 32.15 km/h | 38.10 km/h | **▲ +18.5% increase** |
| Full Stops Count | 5 | 3 | **▼ 40.0% reduction** |

---

## 4. General Traffic Impact Assessment

A common concern with emergency preemption is whether priority overrides disrupt general traffic. The table below shows general background traffic metrics during the identical evaluation window:

| General Traffic Metric | Fixed Control | Adaptive + Emergency Priority | Impact |
|---|---|---|---|
| Total Background Vehicles Inserted | 269 | 269 | Identical Demand |
| Completed Non-Emergency Vehicles | 149 | 151 | +1.3% throughput |
| General Traffic Average Speed | 47.15 km/h | 47.82 km/h | +1.4% improvement |
| General Traffic Average Waiting Time | 7.72 s | 3.81 s | **▼ 50.6% reduction** |

**Conclusion:** The adaptive controller quickly compensates for emergency phase holds by allocating green time according to real-time approach queues immediately after emergency vehicle clearance, preventing network-wide congestion spillback.

---

## 5. Artifacts and Data Sources

- **Structured Comparison JSON:** [`emergency_comparison.json`](file:///c:/Users/jkkho/OneDrive/Documents/traffic_simulation/smart-traffic-simulation/output/evaluation/emergency_comparison.json)
- **Detailed Evaluation CSV:** [`emergency_report.csv`](file:///c:/Users/jkkho/OneDrive/Documents/traffic_simulation/smart-traffic-simulation/output/evaluation/emergency_report.csv)
- **Evaluation Runner Script:** [`evaluate_emergency_priority.py`](file:///c:/Users/jkkho/OneDrive/Documents/traffic_simulation/smart-traffic-simulation/scripts/evaluate_emergency_priority.py)
