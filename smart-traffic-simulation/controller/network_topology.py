import os
import sys

if 'SUMO_HOME' in os.environ:
    sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))

import traci

def get_traffic_lights() -> list:
    """
    Dynamically discovers all traffic light IDs in the current SUMO network.
    """
    try:
        return list(traci.trafficlight.getIDList())
    except traci.TraCIException:
        return []

def get_controlled_lanes(tls_id: str) -> list:
    """
    Returns unique list of incoming lane IDs controlled by the given traffic light.
    """
    try:
        lanes = traci.trafficlight.getControlledLanes(tls_id)
        return list(dict.fromkeys([l for l in lanes if l and not l.startswith(':')]))
    except traci.TraCIException:
        return []

def get_incoming_lanes(tls_id: str) -> list:
    """
    Alias for get_controlled_lanes.
    """
    return get_controlled_lanes(tls_id)

def get_controlled_links(tls_id: str) -> list:
    """
    Returns list of formatted link tuples (from_lane, to_lane, via_lane) controlled by tls_id.
    """
    try:
        raw_links = traci.trafficlight.getControlledLinks(tls_id)
        formatted_links = []
        for link_list in raw_links:
            if link_list:
                for from_lane, to_lane, via_lane in link_list:
                    formatted_links.append((from_lane, to_lane, via_lane))
        return formatted_links
    except traci.TraCIException:
        return []

def get_incoming_edges(tls_id: str) -> list:
    """
    Returns unique list of incoming edge IDs approaching tls_id.
    """
    lanes = get_controlled_lanes(tls_id)
    edges = [lane.rpartition('_')[0] for lane in lanes if lane]
    return list(dict.fromkeys([e for e in edges if e]))

def get_outgoing_edges(tls_id: str) -> list:
    """
    Returns unique list of outgoing edge IDs exiting tls_id.
    """
    links = get_controlled_links(tls_id)
    outgoing = [link[1].rpartition('_')[0] for link in links if len(link) >= 2 and link[1]]
    return list(dict.fromkeys([e for e in outgoing if e and not e.startswith(':')]))

def get_signal_phases(tls_id: str) -> list:
    """
    Retrieves complete phase definition objects for tls_id.
    """
    try:
        logics = traci.trafficlight.getCompleteRedYellowGreenDefinition(tls_id)
        if logics and len(logics) > 0:
            return logics[0].phases
        return []
    except traci.TraCIException:
        return []

def get_intersection_topology(tls_id: str) -> dict:
    """
    Retrieves comprehensive, network-independent topology and current state for tls_id.
    """
    try:
        current_phase = traci.trafficlight.getPhase(tls_id)
        phase_state = traci.trafficlight.getRedYellowGreenState(tls_id)
        next_switch = traci.trafficlight.getNextSwitch(tls_id)
        sim_time = traci.simulation.getTime()
        remaining_duration = max(0.0, round(next_switch - sim_time, 1))
    except traci.TraCIException:
        current_phase = -1
        phase_state = "UNKNOWN"
        remaining_duration = 0.0

    phases = get_signal_phases(tls_id)
    inc_lanes = get_incoming_lanes(tls_id)
    inc_edges = get_incoming_edges(tls_id)
    out_edges = get_outgoing_edges(tls_id)
    ctrl_links = get_controlled_links(tls_id)

    return {
        "tls_id": tls_id,
        "incoming_lanes": inc_lanes,
        "incoming_edges": inc_edges,
        "outgoing_edges": out_edges,
        "controlled_links": [(l[0], l[1]) for l in ctrl_links],
        "num_phases": len(phases),
        "current_phase": current_phase,
        "phase_duration": remaining_duration,
        "phase_state": phase_state
    }
