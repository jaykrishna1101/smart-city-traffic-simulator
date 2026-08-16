import os
import sys

if 'SUMO_HOME' in os.environ:
    sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))

import traci

class EmergencyDetector:
    """
    Detects and tracks active emergency vehicles (Ambulances, Fire Trucks, Police) in the SUMO LHT network.
    """
    def get_emergency_vehicles(self) -> list:
        emergency_list = []
        try:
            vehicle_ids = traci.vehicle.getIDList()
        except traci.TraCIException:
            return emergency_list

        for v_id in vehicle_ids:
            v_class = traci.vehicle.getVehicleClass(v_id)
            v_id_upper = v_id.upper()
            
            is_emergency = (
                "AMBULANCE" in v_id_upper or 
                "FIRE" in v_id_upper or 
                "POLICE" in v_id_upper or 
                v_class in ["emergency", "authority"]
            )

            if is_emergency:
                # Determine specific vehicle sub-type
                v_type = "ambulance"
                if "FIRE" in v_id_upper:
                    v_type = "fire_truck"
                elif "POLICE" in v_id_upper:
                    v_type = "police"

                edge_id = traci.vehicle.getRoadID(v_id)
                lane_id = traci.vehicle.getLaneID(v_id)
                speed_ms = traci.vehicle.getSpeed(v_id)
                speed_kmh = round(speed_ms * 3.6, 2)
                lane_pos = round(traci.vehicle.getLanePosition(v_id), 2)
                
                # Retrieve next downstream traffic light info
                next_tls_info = traci.vehicle.getNextTLS(v_id)
                next_tls_id = None
                distance_to_tls = None
                
                if next_tls_info:
                    # next_tls_info format: (tlsID, tlsIndex, distance, state)
                    tls_id, _, dist, _ = next_tls_info[0]
                    next_tls_id = tls_id
                    distance_to_tls = round(dist, 2)

                emergency_list.append({
                    "vehicle_id": v_id,
                    "type": v_type,
                    "edge_id": edge_id,
                    "lane_id": lane_id,
                    "speed_m_s": round(speed_ms, 2),
                    "speed_kmh": speed_kmh,
                    "position": lane_pos,
                    "next_tls": next_tls_id,
                    "distance_to_tls": distance_to_tls
                })

        return emergency_list
