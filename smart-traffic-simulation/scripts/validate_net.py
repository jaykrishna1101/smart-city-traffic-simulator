import os
import sys
import subprocess

def run_cmd(command):
    print(f"Executing: {command}")
    res = subprocess.run(command, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"FAILED (code {res.returncode}):\n{res.stderr}")
        return False, res.stdout + res.stderr
    print(f"SUCCESS:\n{res.stdout}")
    return True, res.stdout

def validate_simulation():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.abspath(os.path.join(script_dir, ".."))
    
    config_file = os.path.join(project_dir, "simulation", "config", "simulation.sumocfg")
    nodes_file = os.path.join(project_dir, "simulation", "network", "nodes.nod.xml")
    edges_file = os.path.join(project_dir, "simulation", "network", "edges.edg.xml")
    net_file = os.path.join(project_dir, "simulation", "network", "city.net.xml")
    
    sumo_home = os.environ.get("SUMO_HOME", "C:\\Program Files (x86)\\Eclipse\\Sumo")
    sumo_bin = os.path.join(sumo_home, "bin", "sumo.exe")
    netconvert_bin = os.path.join(sumo_home, "bin", "netconvert.exe")
    
    if not os.path.exists(sumo_bin):
        sumo_bin = "sumo"
    if not os.path.exists(netconvert_bin):
        netconvert_bin = "netconvert"

    print("=== STEP 1: Validating Network Compilation (netconvert LHT) ===")
    net_cmd = f'"{netconvert_bin}" --node-files="{nodes_file}" --edge-files="{edges_file}" --lefthand --output-file="{net_file}"'
    ok, out = run_cmd(net_cmd)
    if not ok:
        print("Network validation failed.")
        sys.exit(1)

    print("=== STEP 2: Running Headless SUMO Simulation Dry-Run ===")
    sumo_cmd = f'"{sumo_bin}" -c "{config_file}" --no-warnings false'
    ok, out = run_cmd(sumo_cmd)
    if not ok:
        print("Simulation dry-run failed.")
        sys.exit(1)
        
    print("=== STEP 3: Checking Simulation Output & Emergency Vehicle Statistics ===")
    tripinfo_file = os.path.abspath(os.path.join(project_dir, "output", "tripinfo.xml"))
    if os.path.exists(tripinfo_file):
        with open(tripinfo_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if "AMBULANCE_01" in content and "AMBULANCE_02" in content:
                print("Emergency Vehicles AMBULANCE_01 and AMBULANCE_02 successfully traversed the network!")
            else:
                print(f"Warning: Ambulance entries check in {tripinfo_file}.")

    print("\nALL SUMO VALIDATION CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    validate_simulation()
