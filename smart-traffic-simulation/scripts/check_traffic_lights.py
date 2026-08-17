import os
import sys
import traci

def main():
    # Path to sumocfg file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(script_dir)
    scenario_dir = os.path.join(base_dir, "2026-08-16-19-51-46")
    sumocfg_path = os.path.join(scenario_dir, "osm.sumocfg")

    if not os.path.exists(sumocfg_path):
        print(f"Error: SUMO configuration file not found at {sumocfg_path}")
        sys.exit(1)

    sumo_cmd = [
        "sumo",
        "-c", sumocfg_path,
        "--no-step-log", "true",
        "--waiting-time-memory", "1000"
    ]

    print(f"Starting SUMO with config: {sumocfg_path}")
    traci.start(sumo_cmd)

    # Perform one simulation step to initialize traffic light state
    traci.simulationStep()

    tl_ids = traci.trafficlight.getIDList()

    print("\nTraffic Light IDs:")
    print(list(tl_ids))
    print()

    for tl_id in tl_ids:
        # Fetch detailed properties
        current_phase = traci.trafficlight.getPhase(tl_id)
        current_state = traci.trafficlight.getRedYellowGreenState(tl_id)
        phase_duration = traci.trafficlight.getPhaseDuration(tl_id)
        controlled_lanes = traci.trafficlight.getControlledLanes(tl_id)
        controlled_links = traci.trafficlight.getControlledLinks(tl_id)

        # Get type if available from logic definition
        logics = traci.trafficlight.getCompleteRedYellowGreenDefinition(tl_id)
        tl_type = logics[0].type if len(logics) > 0 else "Unknown"
        type_str_map = {0: "static (fixed)", 3: "actuated", 4: "NEMA", 5: "delay_based"}
        type_desc = type_str_map.get(tl_type, f"Unknown ({tl_type})")

        print(f"ID: {tl_id}")
        print(f"Type: {type_desc}")
        print(f"Current phase: {current_phase}")
        print(f"Current state: {current_state}")
        print(f"Phase duration: {phase_duration}")
        print(f"Controlled lanes: {list(dict.fromkeys(controlled_lanes))}")
        print(f"Controlled links count: {len(controlled_links)}")
        print("Controlled links (incoming -> outgoing):")
        for link in controlled_links:
            # link is a list of tuples: [(from_lane, to_lane, via_lane), ...]
            if link:
                from_lane, to_lane, via_lane = link[0]
                print(f"  {from_lane} -> {to_lane}")
            else:
                print("  Empty link")
        print("-" * 50)

    traci.close()
    print("\nTraCI connection closed cleanly.")

if __name__ == "__main__":
    main()
