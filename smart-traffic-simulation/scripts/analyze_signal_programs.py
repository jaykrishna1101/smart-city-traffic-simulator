import os
import sys

# Ensure project directory is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import traci
from controller.config import SUMO_CONFIG_PATH
from controller.network_topology import (
    get_traffic_lights,
    get_controlled_links,
    get_incoming_lanes,
    get_incoming_edges,
    get_signal_phases
)

def classify_phase_type(state_str: str) -> str:
    state_set = set(state_str)
    if 'G' in state_set or 'g' in state_set:
        return "GREEN"
    elif 'y' in state_set or 'Y' in state_set:
        return "YELLOW"
    elif state_set == {'r'} or state_set == {'r', 'u'}:
        return "ALL_RED"
    else:
        return "OTHER"

def analyze_signal_programs():
    print(f"Connecting TraCI to SUMO config: {SUMO_CONFIG_PATH}")
    sumo_cmd = ["sumo", "-c", SUMO_CONFIG_PATH, "--no-step-log", "true"]
    traci.start(sumo_cmd)
    traci.simulationStep()

    tls_ids = get_traffic_lights()

    print("\n=========================================================================")
    print(f"       CHATRAPATI-RING ROAD DETAILED SIGNAL PROGRAM ANALYSIS             ")
    print(f"=========================================================================\n")
    print(f"Total Traffic Light Controllers: {len(tls_ids)}\n")

    report_data = {}

    for idx, tls_id in enumerate(tls_ids, 1):
        logics = traci.trafficlight.getCompleteRedYellowGreenDefinition(tls_id)
        logic = logics[0] if logics else None
        
        program_id = logic.programID if logic else "Unknown"
        tl_type_int = logic.type if logic else -1
        type_str_map = {0: "static (fixed)", 3: "actuated", 4: "NEMA", 5: "delay_based"}
        type_desc = type_str_map.get(tl_type_int, f"Unknown ({tl_type_int})")

        phases = logic.phases if logic else []
        links = get_controlled_links(tls_id)
        inc_lanes = get_incoming_lanes(tls_id)
        inc_edges = get_incoming_edges(tls_id)

        print(f"-------------------------------------------------------------------------")
        print(f"TLS #{idx} ID: {tls_id}")
        print(f"Program ID: {program_id} | Program Type: {type_desc}")
        print(f"Incoming Edges ({len(inc_edges)}): {inc_edges}")
        print(f"Incoming Lanes ({len(inc_lanes)}): {inc_lanes}")
        print(f"Controlled Link Signals ({len(links)}):")
        for l_idx, (from_l, to_l, via_l) in enumerate(links):
            print(f"  Link [{l_idx:2d}]: {from_l} -> {to_l}")
        print(f"\nTotal Phases: {len(phases)}")

        green_phases = []
        yellow_phases = []
        phase_details = []

        for p_idx, phase in enumerate(phases):
            duration = phase.duration
            min_dur = getattr(phase, 'minDur', -1)
            max_dur = getattr(phase, 'maxDur', -1)
            state_str = phase.state
            p_type = classify_phase_type(state_str)

            # Identify movements permitted by green signals in this phase
            permitted_movements = []
            permitted_edges = set()

            for l_idx, char in enumerate(state_str):
                if char in ['G', 'g'] and l_idx < len(links):
                    from_l, to_l, _ = links[l_idx]
                    from_e = from_l.rpartition('_')[0]
                    to_e = to_l.rpartition('_')[0]
                    permitted_movements.append(f"{from_l}->{to_l}")
                    if from_e:
                        permitted_edges.add(from_e)

            if p_type == "GREEN":
                green_phases.append(p_idx)
            elif p_type == "YELLOW":
                yellow_phases.append(p_idx)

            print(f"\n  Phase {p_idx}:")
            print(f"    Duration: {duration}s (minDur={min_dur}, maxDur={max_dur})")
            print(f"    Type: {p_type}")
            print(f"    State String ({len(state_str)} chars): {state_str}")
            if p_type == "GREEN":
                print(f"    Permitted Entry Edges ({len(permitted_edges)}): {sorted(list(permitted_edges))}")
                print(f"    Permitted Link Movements ({len(permitted_movements)}): {permitted_movements}")
            else:
                print(f"    Transition Phase (Yellow / Red Clearance)")

            phase_details.append({
                "phase_index": p_idx,
                "duration": duration,
                "type": p_type,
                "state": state_str,
                "permitted_edges": sorted(list(permitted_edges)),
                "permitted_movements": permitted_movements
            })

        print(f"\n  SUMMARY FOR TLS '{tls_id}':")
        print(f"    Green Phases (Selectable by Adaptive Controller): {green_phases}")
        print(f"    Yellow/Clearance Transition Phases: {yellow_phases}")

        report_data[tls_id] = {
            "program_id": program_id,
            "type": type_desc,
            "phases": phase_details,
            "green_phases": green_phases,
            "yellow_phases": yellow_phases
        }

    traci.close()
    print("\n=========================================================================")
    print("           SIGNAL PROGRAM ANALYSIS COMPLETED SUCCESSFULLY                 ")
    print("=========================================================================\n")
    return report_data

if __name__ == "__main__":
    analyze_signal_programs()
