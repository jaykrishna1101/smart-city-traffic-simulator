import os
import json
from datetime import datetime, timezone
from controller.config import COMPARISON_JSON_PATH, SCENARIO_NAME

INTERSECTION_FRIENDLY_NAMES = {
    "cluster_2683490405_298938456": "Chatrapati Main Square",
    "joinedS_2705384848_3138462214": "Ring Road Junction",
    "cluster_2683490416_2683507646_2683507647_2684658305_#2more": "Wardha Road Interchange"
}

INTERSECTION_COORDINATES = {
    "cluster_2683490405_298938456": (21.1095, 79.0722),
    "joinedS_2705384848_3138462214": (21.1120, 79.0810),
    "cluster_2683490416_2683507646_2683507647_2684658305_#2more": (21.0965, 79.0634)
}

def derive_signal_color(phase_state: str) -> str:
    """Derives a primary signal color (green, yellow, red) from a SUMO phase state string."""
    if not phase_state:
        return "green"
    state_upper = phase_state.upper()
    if 'Y' in state_upper:
        return "yellow"
    if 'G' in phase_state or 'g' in phase_state:
        return "green"
    return "red"

def format_clock(sim_time_sec: float) -> str:
    """Formats simulation seconds into a digital HH:MM:SS string."""
    total_sec = int(max(0.0, sim_time_sec))
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    seconds = total_sec % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def load_cached_comparison() -> list:
    """Loads benchmark comparison data from output/comparison.json if present."""
    if not os.path.exists(COMPARISON_JSON_PATH):
        return []
    try:
        with open(COMPARISON_JSON_PATH, 'r', encoding='utf-8') as f:
            raw = json.load(f)

        fixed_data = raw.get("fixed", {})
        adaptive_data = raw.get("adaptive", {})

        metrics_def = [
            ("Average waiting time", "average_waiting_time", "sec", True),
            ("Average queue length", "average_queue_length", "veh", True),
            ("Max queue length", "max_queue", "veh", True),
            ("Average speed", "average_speed_kmh", "km/h", False),
            ("Throughput", "throughput", "veh", False),
            ("Congestion events", "congestion_events", "events", True),
            ("Emergency response time", "emergency_response_time", "sec", True),
        ]

        comparison_list = []
        for label, key, unit, lower_is_better in metrics_def:
            f_val = fixed_data.get(key)
            a_val = adaptive_data.get(key)
            if f_val is not None and a_val is not None:
                if f_val > 0:
                    diff = (f_val - a_val) if lower_is_better else (a_val - f_val)
                    imp = round((diff / f_val) * 100.0, 1)
                else:
                    imp = 0.0
                comparison_list.append({
                    "metric": label,
                    "fixed": f_val,
                    "adaptive": a_val,
                    "improvement": imp,
                    "unit": unit
                })
        return comparison_list
    except Exception:
        return []

def serialize_simulation_state(
    sim_time: float,
    state: dict,
    decisions: dict = None,
    tracker = None,
    mode: str = "ADAPTIVE",
    status: str = "running"
) -> dict:
    """
    Serializes complete SUMO traffic simulation state into a JSON-safe dictionary
    following the SmartFlow WebSocket message envelope contract.
    """
    decisions = decisions or {}
    mode_normalized = mode.upper().replace("-", "_")
    is_adaptive = mode_normalized in ["ADAPTIVE", "EMERGENCY_DEMO"]
    period = state.get("period", "NORMAL")
    scenario = state.get("scenario", SCENARIO_NAME)

    raw_intersections = state.get("intersections", {})
    raw_emergency_vehs = state.get("emergency_vehicles", [])

    # Identify which traffic lights have approaching emergency vehicles
    emergency_target_tls = set()
    for em in raw_emergency_vehs:
        next_tls = em.get("next_tls")
        if next_tls:
            emergency_target_tls.add(next_tls)

    # 1. Intersections & Signals & Approaches
    intersections_list = []
    signals_list = []
    adaptive_control_list = []
    roads_list = []

    total_active_vehs = 0
    total_queue_sum = 0
    max_queue_val = 0
    all_speeds_kmh = []
    all_wait_times = []
    total_flow_sum = 0
    congestion_count = 0

    for tls_id, tls_data in raw_intersections.items():
        name = INTERSECTION_FRIENDLY_NAMES.get(tls_id, tls_id)
        coords = INTERSECTION_COORDINATES.get(tls_id, (21.10, 79.07))
        phase_idx = tls_data.get("signal_phase", 0)
        phase_state = tls_data.get("phase_state", "")
        phase_rem = tls_data.get("phase_remaining", 0.0)
        avg_wait = tls_data.get("average_waiting_time", 0.0)
        avg_spd_kmh = tls_data.get("average_speed_kmh", 0.0)
        tot_vehs = tls_data.get("total_vehicles", 0)
        tot_q = tls_data.get("total_queue", 0)

        total_active_vehs += tot_vehs
        total_queue_sum += tot_q
        if tot_q > max_queue_val:
            max_queue_val = tot_q
        all_speeds_kmh.append(avg_spd_kmh)
        all_wait_times.append(avg_wait)

        # Approaches
        approaches_arr = []
        for edge_id, app in tls_data.get("approaches", {}).items():
            q_len = app.get("queue", 0)
            v_cnt = app.get("vehicles", 0)
            w_time = app.get("waiting_time", 0.0)
            s_kmh = app.get("speed_kmh", 0.0)
            flow = app.get("traffic_flow", 0)
            cong = app.get("congestion", "LOW")

            total_flow_sum += flow
            if cong in ["HIGH", "SEVERE"]:
                congestion_count += 1

            approaches_arr.append({
                "direction": edge_id,
                "vehicles": v_cnt,
                "queueLength": q_len,
                "waitingTime": w_time,
                "speedKmh": s_kmh,
                "congestion": cong
            })

            # Road entry
            roads_list.append({
                "roadName": f"Approach {edge_id}",
                "coordinates": [[coords[0] - 0.002, coords[1] - 0.002], [coords[0], coords[1]]],
                "vehicleCount": v_cnt,
                "queueLength": q_len,
                "congestionLevel": min(100, int((q_len / 15.0) * 100)) if q_len > 0 else 0
            })

        # Calculate congestion percentage (0-100)
        cong_level = min(100, max(0, int((tot_q / 20.0) * 100))) if tot_q > 0 else 0

        # Status: emergency | congested | normal
        if tls_id in emergency_target_tls:
            status_str = "emergency"
        elif cong_level > 50 or avg_wait > 25.0:
            status_str = "congested"
        else:
            status_str = "normal"

        intersections_list.append({
            "id": tls_id,
            "name": name,
            "zone": "Nagpur Urban Ring Road",
            "latitude": coords[0],
            "longitude": coords[1],
            "approaches": approaches_arr,
            "averageWaitingTime": avg_wait,
            "congestionLevel": cong_level,
            "status": status_str,
            "totalVehicles": tot_vehs,
            "totalQueue": tot_q,
            "averageSpeedKmh": avg_spd_kmh,
            "signalPhase": phase_idx,
            "phaseState": phase_state,
            "phaseRemaining": phase_rem,
            "controlledLanes": tls_data.get("controlled_lanes", []),
            "controlledEdges": tls_data.get("controlled_edges", [])
        })

        # Signal entry
        decision = decisions.get(tls_id, {})
        has_emergency_priority = "EMERGENCY" in str(decision.get("reason", "")).upper()
        signal_color = derive_signal_color(phase_state)

        control_mode = "emergency" if has_emergency_priority else ("adaptive" if is_adaptive else "fixed")
        green_duration = decision.get("green_duration", 16)

        signals_list.append({
            "intersectionId": tls_id,
            "currentPhase": f"Phase {phase_idx} ({signal_color.upper()})",
            "state": signal_color,
            "remainingTime": round(phase_rem, 1),
            "currentGreenTime": green_duration,
            "controlMode": control_mode,
            "phaseState": phase_state
        })

        # Adaptive control entry
        if decision:
            adaptive_control_list.append({
                "intersectionId": tls_id,
                "approach": decision.get("selected_movement", f"Phase {phase_idx}"),
                "vehicleCount": tot_vehs,
                "calculatedGreenTime": green_duration,
                "actualGreenTime": green_duration,
                "reason": decision.get("reason", "Standard traffic pressure optimization")
            })

    # 2. Emergency vehicles
    emergency_list = []
    for em in raw_emergency_vehs:
        v_id = em.get("vehicle_id", "EMERGENCY_VEH")
        v_type_raw = em.get("type", "ambulance").lower()
        if "fire" in v_type_raw:
            v_type = "fire"
        elif "police" in v_type_raw:
            v_type = "police"
        else:
            v_type = "ambulance"

        next_tls = em.get("next_tls")
        dist = em.get("distance_to_tls")
        speed_kmh = em.get("speed_kmh", 0.0)

        # Estimate response time (seconds to reach intersection or clearance)
        if dist is not None and speed_kmh > 0:
            speed_ms = speed_kmh / 3.6
            resp_time = round(dist / max(speed_ms, 1.0), 1)
        else:
            resp_time = round(dist / 12.0, 1) if dist is not None else 0.0

        emergency_list.append({
            "id": v_id,
            "type": v_type,
            "location": f"Edge {em.get('edge_id', 'Unknown')} (Lane {em.get('lane_id', '')})",
            "status": "approaching" if next_tls else "cleared",
            "priorityStatus": "active" if next_tls else "standby",
            "priorityIntersection": next_tls or "None",
            "responseTime": resp_time,
            "speedKmh": speed_kmh,
            "distanceToTls": dist
        })

    # 3. Aggregated Traffic Metrics
    active_vehs = len(getattr(tracker, "departed_ids_set", [])) - len(getattr(tracker, "arrived_ids_set", [])) if tracker else total_active_vehs
    active_vehs = max(active_vehs, total_active_vehs)
    completed_vehs = len(getattr(tracker, "arrived_ids_set", [])) if tracker else 0
    avg_speed = round(sum(all_speeds_kmh) / max(len(all_speeds_kmh), 1), 1)
    avg_wait = round(sum(all_wait_times) / max(len(all_wait_times), 1), 1)
    avg_queue = round(total_queue_sum / max(len(raw_intersections), 1), 1)

    # Traffic efficiency index (0-100%): 100% minus wait and queue penalties
    efficiency = max(5, min(100, int(100 - (avg_wait * 1.2 + avg_queue * 2.0))))

    traffic_metrics = {
        "activeVehicles": active_vehs,
        "completedVehicles": completed_vehs,
        "averageSpeed": avg_speed,
        "averageWaitingTime": avg_wait,
        "averageQueueLength": avg_queue,
        "maximumQueueLength": max_queue_val,
        "trafficFlow": total_flow_sum,
        "congestionEvents": congestion_count if not tracker else tracker.congestion_events,
        "trafficEfficiency": efficiency
    }

    # 4. Performance Comparison
    perf_comparison = load_cached_comparison()

    payload = {
        "type": "simulation_update",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "simulation": {
            "time": round(sim_time, 1),
            "clock": format_clock(sim_time),
            "period": period,
            "scenario": scenario,
            "mode": mode_normalized,
            "status": status,
            "adaptiveMode": is_adaptive
        },
        "traffic": traffic_metrics,
        "intersections": intersections_list,
        "signals": signals_list,
        "adaptiveControl": adaptive_control_list,
        "emergencyVehicles": emergency_list,
        "roads": roads_list,
        "performanceComparison": perf_comparison
    }

    return payload
