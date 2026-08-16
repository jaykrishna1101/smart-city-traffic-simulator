import os
import sys

if 'SUMO_HOME' in os.environ:
    sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))

import traci
from controller.traffic_state import TrafficStateAggregator
from controller.adaptive_controller import AdaptiveTrafficController
from controller.peak_hour import PeakHourDetector
from controller.emergency import EmergencyDetector

# Singleton helper instances for API access
_aggregator = TrafficStateAggregator()
_peak_detector = PeakHourDetector()
_emergency_detector = EmergencyDetector()
_controller = AdaptiveTrafficController()

def get_traffic_state() -> dict:
    """
    Exposes the complete real-time traffic state dictionary across all intersections.
    """
    return _aggregator.get_traffic_state()

def get_intersection_state(intersection_id: str) -> dict:
    """
    Exposes the real-time traffic state dictionary for a specific intersection.
    """
    full_state = _aggregator.get_traffic_state()
    return full_state.get("intersections", {}).get(intersection_id, {})

def get_peak_period() -> str:
    """
    Exposes the current logical traffic period string (MORNING_PEAK, NORMAL, EVENING_PEAK).
    """
    sim_time = traci.simulation.getTime()
    return _peak_detector.get_period(sim_time)

def get_emergency_vehicles() -> list:
    """
    Exposes active emergency vehicles (Ambulances, Fire Trucks, Police) in the network.
    """
    return _emergency_detector.get_emergency_vehicles()

def get_signal_state(intersection_id: str) -> dict:
    """
    Exposes signal phase index, state string, and remaining phase duration for an intersection.
    """
    sim_time = traci.simulation.getTime()
    return _aggregator.get_tls_state(intersection_id, sim_time)

def apply_signal_decision(decision: dict):
    """
    Applies a signal decision dictionary to SUMO via TraCI.
    """
    _controller.apply_signal_decision(decision)
