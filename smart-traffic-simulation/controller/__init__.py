"""
Smart City Adaptive Traffic Control Package (Indian Left-Hand Traffic).
Exposes public Integration API functions.
"""

from controller.api import (
    get_traffic_state,
    get_intersection_state,
    get_peak_period,
    get_emergency_vehicles,
    get_signal_state,
    apply_signal_decision
)

__all__ = [
    "get_traffic_state",
    "get_intersection_state",
    "get_peak_period",
    "get_emergency_vehicles",
    "get_signal_state",
    "apply_signal_decision"
]
