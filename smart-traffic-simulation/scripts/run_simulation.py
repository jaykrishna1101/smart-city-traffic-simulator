import os
import sys
import argparse
import time

# Ensure SUMO tools are available in sys.path
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.path.append('C:\\Program Files (x86)\\Eclipse\\Sumo\\tools')

import traci

def get_logical_period(sim_time):
    if sim_time < 180:
        return "MORNING_PEAK (09:00 - 12:00)"
    elif sim_time < 240:
        return "NORMAL (12:00 - 16:00)"
    else:
        return "EVENING_PEAK (16:00 - 19:00)"

def run_simulation(gui=False):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.abspath(os.path.join(script_dir, ".."))
    config_file = os.path.join(project_dir, "simulation", "config", "simulation.sumocfg")

    sumo_home = os.environ.get("SUMO_HOME", "C:\\Program Files (x86)\\Eclipse\\Sumo")
    binary_name = "sumo-gui.exe" if gui else "sumo.exe"
    sumo_binary = os.path.join(sumo_home, "bin", binary_name)

    if not os.path.exists(sumo_binary):
        sumo_binary = "sumo-gui" if gui else "sumo"

    print(f"Starting SUMO Simulation ({'GUI' if gui else 'Headless'})...")
    print(f"Configuration file: {config_file}")

    traci_cmd = [sumo_binary, "-c", config_file]
    traci.start(traci_cmd)

    current_period = None
    step = 0

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        sim_time = traci.simulation.getTime()
        period = get_logical_period(sim_time)

        if period != current_period:
            current_period = period
            print(f"\n>>> [SIMULATION TIME: {sim_time:5.1f}s] LOGICAL SCENARIO SWITCHED TO: {current_period} <<<")

        # Periodically log traffic stats
        if step % 30 == 0:
            active_vehs = traci.vehicle.getIDCount()
            print(f"Step {int(sim_time):3d}s | Active Vehicles: {active_vehs:3d} | Current Period: {period}")

        # Highlight emergency vehicle when detected
        vehs = traci.vehicle.getIDList()
        for v in vehs:
            if "AMBULANCE" in v:
                road = traci.vehicle.getRoadID(v)
                speed = traci.vehicle.getSpeed(v) * 3.6
                if step % 10 == 0:
                    print(f"  [EMERGENCY DETECTED] {v} on road '{road}' driving at {speed:.1f} km/h")

        step += 1
        if gui:
            time.sleep(0.02) # Smooth GUI animation

    traci.close()
    print("\nSimulation execution completed successfully!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Smart City Traffic Simulation")
    parser.add_argument("--gui", action="store_true", help="Launch simulation with sumo-gui")
    parser.add_argument("--nogui", action="store_true", help="Run simulation in headless mode")
    args = parser.parse_args()

    # Default to GUI if --nogui is not explicitly specified
    use_gui = True
    if args.nogui:
        use_gui = False

    run_simulation(gui=use_gui)
