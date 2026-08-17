from controller.config import MIN_GREEN_TIME, MAX_GREEN_TIME, STARVATION_THRESHOLD
from controller.traffic_pressure import TrafficPressureCalculator
from controller.network_topology import get_signal_phases

class SignalOptimizer:
    """
    Optimizes traffic signal green durations and phase selections based on dynamic
    traffic pressure and starvation constraints across arbitrary SUMO N-phase controllers.

    FIX (Bug 4): Yellow phase index is now derived by parsing the actual phase sequence,
    mapping each green phase to the correct subsequent yellow/clearance phase —
    not blindly assuming (green_phase + 1) is always yellow.
    """
    def __init__(self):
        self.pressure_calculator = TrafficPressureCalculator()
        self.min_green = MIN_GREEN_TIME
        self.max_green = MAX_GREEN_TIME
        self.starvation_threshold = STARVATION_THRESHOLD
        # Cache yellow phase maps per TLS (built once from phase sequence)
        self._yellow_phase_map = {}

    def _build_yellow_phase_map(self, tls_id: str) -> dict:
        """
        Scans the phase sequence to build a {green_phase_idx: yellow_phase_idx} map.
        A yellow phase is one whose state string contains only 'y', 'Y', or 'r' characters
        (no 'G' or 'g'). The yellow phase immediately following a green phase is mapped.
        Falls back to the next phase index if no explicit yellow is found.
        """
        if tls_id in self._yellow_phase_map:
            return self._yellow_phase_map[tls_id]

        phases = get_signal_phases(tls_id)
        if not phases:
            return {}

        total = len(phases)
        yellow_map = {}

        def is_green(state):
            return 'G' in state or 'g' in state

        def is_yellow(state):
            state_chars = set(state)
            return ('y' in state_chars or 'Y' in state_chars) and 'G' not in state_chars and 'g' not in state_chars

        for i, phase in enumerate(phases):
            if is_green(phase.state):
                # Look ahead for the first yellow/clearance phase
                found_yellow = None
                for offset in range(1, total):
                    candidate_idx = (i + offset) % total
                    candidate_state = phases[candidate_idx].state
                    if is_yellow(candidate_state):
                        found_yellow = candidate_idx
                        break
                    elif is_green(candidate_state):
                        # Another green before a yellow — no yellow transition exists
                        # Use the candidate itself (stay in green)
                        found_yellow = i
                        break

                yellow_map[i] = found_yellow if found_yellow is not None else (i + 1) % total

        self._yellow_phase_map[tls_id] = yellow_map
        return yellow_map

    def calculate_adaptive_green(self, target_pressure: float, total_pressure: float) -> int:
        """
        Higher pressure -> longer green time (up to MAX_GREEN_TIME)
        Lower pressure -> shorter green time (down to MIN_GREEN_TIME)
        """
        if total_pressure <= 0.0 or target_pressure <= 0.0:
            return self.min_green

        ratio = min(1.0, max(0.0, target_pressure / max(total_pressure, 1.0)))
        raw_duration = self.min_green + (self.max_green - self.min_green) * ratio
        green_duration = int(round(raw_duration))
        return max(self.min_green, min(self.max_green, green_duration))

    def optimize_signal(self, intersection_id: str, intersection_data: dict, last_green_times: dict, current_sim_time: float) -> dict:
        """
        Analyzes dynamic phase pressures and starvation states to select the optimal phase
        and adaptive green duration for an intersection.
        """
        phase_pressures = self.pressure_calculator.calculate_phase_pressures(intersection_id, intersection_data)
        total_press = sum(phase_pressures.values())

        phases = get_signal_phases(intersection_id)
        total_phases = len(phases) if phases else 1
        yellow_map = self._build_yellow_phase_map(intersection_id)

        selected_phase = list(phase_pressures.keys())[0] if phase_pressures else 0
        max_press = -1.0
        reason = "Initial phase"

        # Check starvation override across candidate green phases
        starved_override_phase = None
        for p_idx in phase_pressures.keys():
            last_g = last_green_times.get(p_idx, current_sim_time)
            waited = current_sim_time - last_g
            press = phase_pressures[p_idx]

            if waited >= self.starvation_threshold and press > 0:
                starved_override_phase = p_idx
                reason = f"Anti-starvation override for Phase {p_idx} (waited {waited:.1f}s)"
                break

        if starved_override_phase is not None:
            selected_phase = starved_override_phase
        else:
            for p_idx, press in phase_pressures.items():
                if press > max_press:
                    max_press = press
                    selected_phase = p_idx
                    reason = f"Highest traffic pressure (score={press:.1f})"

        target_pressure = phase_pressures.get(selected_phase, 0.0)
        green_duration = self.calculate_adaptive_green(target_pressure, total_press)

        # FIX (Bug 4): Use topology-aware yellow phase mapping
        yellow_phase = yellow_map.get(selected_phase, (selected_phase + 1) % total_phases)

        return {
            "intersection": intersection_id,
            "selected_movement": f"PHASE_{selected_phase}",
            "phase": f"PHASE_{selected_phase}_GREEN",
            "target_phase_index": selected_phase,
            "yellow_phase_index": yellow_phase,
            "green_duration": green_duration,
            "phase_pressures": phase_pressures,
            "reason": reason
        }
