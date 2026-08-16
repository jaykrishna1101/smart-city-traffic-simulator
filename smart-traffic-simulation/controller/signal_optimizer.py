from controller.config import PHASE_MAP, MIN_GREEN_TIME, MAX_GREEN_TIME, STARVATION_THRESHOLD
from controller.traffic_pressure import TrafficPressureCalculator

class SignalOptimizer:
    """
    Optimizes traffic signal green durations and phase selections based on traffic pressure and starvation constraints.
    """
    def __init__(self):
        self.pressure_calculator = TrafficPressureCalculator()
        self.min_green = MIN_GREEN_TIME
        self.max_green = MAX_GREEN_TIME
        self.starvation_threshold = STARVATION_THRESHOLD

    def calculate_adaptive_green(self, target_pressure: float, total_pressure: float) -> int:
        """
        Higher pressure -> longer green time (up to 60s)
        Lower pressure -> shorter green time (down to 10s)
        """
        if total_pressure <= 0.0 or target_pressure <= 0.0:
            return self.min_green

        ratio = min(1.0, max(0.0, target_pressure / max(total_pressure, 1.0)))
        raw_duration = self.min_green + (self.max_green - self.min_green) * ratio
        green_duration = int(round(raw_duration))
        return max(self.min_green, min(self.max_green, green_duration))

    def optimize_signal(self, intersection_id: str, intersection_data: dict, last_green_times: dict, current_sim_time: float) -> dict:
        """
        Analyzes traffic pressures and starvation state to select optimal phase and adaptive green duration.
        """
        pressures = self.pressure_calculator.calculate_intersection_pressures(intersection_data)
        ns_press = pressures["NS_pressure"]
        ew_press = pressures["EW_pressure"]
        total_press = ns_press + ew_press

        ns_last_green = last_green_times.get("NORTH_SOUTH", current_sim_time)
        ew_last_green = last_green_times.get("EAST_WEST", current_sim_time)

        ns_starved_time = current_sim_time - ns_last_green
        ew_starved_time = current_sim_time - ew_last_green

        ns_has_queue = (intersection_data.get("north", {}).get("queue", 0) + intersection_data.get("south", {}).get("queue", 0)) > 0
        ew_has_queue = (intersection_data.get("east", {}).get("queue", 0) + intersection_data.get("west", {}).get("queue", 0)) > 0

        selected_movement = "NORTH_SOUTH"
        reason = "Higher NS traffic pressure"

        # Check starvation override
        if ew_starved_time >= self.starvation_threshold and ew_has_queue:
            selected_movement = "EAST_WEST"
            reason = f"Anti-starvation override for EW (waited {ew_starved_time:.1f}s)"
        elif ns_starved_time >= self.starvation_threshold and ns_has_queue:
            selected_movement = "NORTH_SOUTH"
            reason = f"Anti-starvation override for NS (waited {ns_starved_time:.1f}s)"
        else:
            if ew_press > ns_press:
                selected_movement = "EAST_WEST"
                reason = f"Higher EW traffic pressure ({ew_press} vs {ns_press})"
            else:
                selected_movement = "NORTH_SOUTH"
                reason = f"Higher NS traffic pressure ({ns_press} vs {ew_press})"

        target_pressure = ew_press if selected_movement == "EAST_WEST" else ns_press
        green_duration = self.calculate_adaptive_green(target_pressure, total_press)

        # Get exact phase index for the LHT network
        tls_phases = PHASE_MAP.get(intersection_id, {})
        target_phase = tls_phases.get(selected_movement, 0)
        yellow_phase = tls_phases.get(f"YELLOW_{'EW' if selected_movement == 'EAST_WEST' else 'NS'}", 1)

        return {
            "intersection": intersection_id,
            "selected_movement": selected_movement,
            "phase": f"{selected_movement}_GREEN",
            "target_phase_index": target_phase,
            "yellow_phase_index": yellow_phase,
            "green_duration": green_duration,
            "ns_pressure": ns_press,
            "ew_pressure": ew_press,
            "reason": reason
        }
