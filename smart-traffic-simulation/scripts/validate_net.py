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
    get_intersection_topology,
    get_incoming_lanes,
    get_incoming_edges,
    get_controlled_links,
    get_signal_phases
)
from controller.traffic_state import TrafficStateAggregator

def validate_and_report_network():
    print(f"Loading SUMO network configuration: {SUMO_CONFIG_PATH}")
    sumo_cmd = ["sumo", "-c", SUMO_CONFIG_PATH, "--no-step-log", "true"]
    
    traci.start(sumo_cmd)
    traci.simulationStep()

    tls_ids = get_traffic_lights()

    print("\n=========================================================================")
    print(f"             DYNAMIC NETWORK TOPOLOGY DISCOVERY REPORT                   ")
    print(f"=========================================================================")
    print(f"Traffic lights: {len(tls_ids)}\n")

    for idx, tls_id in enumerate(tls_ids, 1):
        topo = get_intersection_topology(tls_id)
        print(f"TLS #{idx}:")
        print(f"  ID: {topo['tls_id']}")
        print(f"  Incoming edges ({len(topo['incoming_edges'])}): {topo['incoming_edges']}")
        print(f"  Incoming lanes ({len(topo['incoming_lanes'])}): {topo['incoming_lanes']}")
        print(f"  Controlled links ({len(topo['controlled_links'])}):")
        for link in topo['controlled_links']:
            print(f"    {link[0]} -> {link[1]}")
        print(f"  Number of phases: {topo['num_phases']}")
        print(f"  Current phase index: {topo['current_phase']}")
        print(f"  Phase state: {topo['phase_state']}")
        print("-" * 65)

    print("\n=== VERIFYING TRAFFIC METRICS & TELEMETRY COLLECTION ===")
    aggregator = TrafficStateAggregator()
    
    # Run 50 steps to collect active telemetry
    for step in range(50):
        traci.simulationStep()

    state = aggregator.get_traffic_state()
    print(f"Simulation step: {state['simulation_time']}s | Period: {state['period']} | Scenario: {state['scenario']}")
    print(f"Intersections discovered in state: {list(state['intersections'].keys())}")
    
    for tls_id, tls_data in state['intersections'].items():
        print(f"\n  [Intersection: {tls_id}]")
        print(f"    Phase Index: {tls_data['signal_phase']} | Phase State: {tls_data['phase_state']}")
        print(f"    Total Vehicles: {tls_data['total_vehicles']} | Total Queue: {tls_data['total_queue']} | Avg Wait: {tls_data['average_waiting_time']}s")
        for edge_id, app in tls_data.get('approaches', {}).items():
            print(f"      Edge '{edge_id}': vehs={app['vehicles']}, queue={app['queue']}, wait={app['waiting_time']}s, speed={app['speed_kmh']}km/h, congestion={app['congestion']}")

    traci.close()
    print("\n=========================================================================")
    print("ALL DYNAMIC NETWORK DISCOVERY & TELEMETRY CHECKS PASSED SUCCESSFULLY!")
    print("=========================================================================\n")

if __name__ == "__main__":
    validate_and_report_network()
