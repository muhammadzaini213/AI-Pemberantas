import random
from ..classes.vehicle import Vehicle

# ========== GENERATE TPS GARBAGES ==========
def generate_tps_garbage(TPS_nodes, shared):
        for tps_id in TPS_nodes:
            if tps_id in shared.node_type:
                tps_data = shared.node_type[tps_id].get("tps_data", {})
                sampah_per_hari = tps_data.get("sampah_per_hari", 0)
                
                if sampah_per_hari > 0:
                    variance = sampah_per_hari * 0.30
                    random_variance = random.uniform(-variance, variance)
                    actual_sampah = sampah_per_hari + random_variance
                    actual_sampah = max(0, actual_sampah)
                    
                    tps_data["sampah_kg"] = actual_sampah
                    print(f"[Simulation] TPS {tps_id}: Initial garbage {actual_sampah:.2f} kg")



# ========== GENERATE DAILY GARBAGES ==========
def generate_daily_garbage(shared, TPS_nodes, ai_model, last_garbage_generation_day):
    if shared.sim_day > last_garbage_generation_day:
        print(f"\n[Simulation] Day {shared.sim_day}: Generating daily garbage...")
        
        ai_model.reset_daily()
        
        for tps_id in TPS_nodes:
            if tps_id in shared.node_type:
                tps_data = shared.node_type[tps_id].get("tps_data", {})
                sampah_per_hari = tps_data.get("sampah_per_hari", 0)
                
                if sampah_per_hari > 0:
                    variance = sampah_per_hari * 0.30
                    random_variance = random.uniform(-variance, variance)
                    daily_garbage = sampah_per_hari + random_variance
                    daily_garbage = max(0, daily_garbage)
                    
                    tps_data["sampah_kg"] += daily_garbage
                    print(f"[Simulation] TPS {tps_id}: +{daily_garbage:.2f} kg (total: {tps_data['sampah_kg']:.2f} kg)")
        
        last_garbage_generation_day = shared.sim_day
    return last_garbage_generation_day



# ========== SPAWN CARS FROM GARAGE ==========
def generate_car_in_garage(GARAGE_nodes, shared, vehicles, GRAPH, TPS_nodes, TPA_nodes):
    
    # ===== CREATE VEHICLES =====
    print(f"\n{'='*60}")
    print(f"[Simulation] CREATING VEHICLES")
    print(f"{'='*60}")

    garage_list = list(GARAGE_nodes)
    
    if garage_list:
        total_vehicles_created = 0
        
        print(f"[Simulation] Resetting garage stats...")
        for garage_id in garage_list:
            if garage_id in shared.node_type:
                garage_data = shared.node_type[garage_id].get("garage_data", {})
                garage_data["armada_bertugas"] = 0
                garage_data["armada_standby"] = 0
                print(f"[Simulation]   Garage {garage_id}: total_armada={garage_data.get('total_armada', 0)}")
        
        print(f"\n[Simulation] Creating vehicles for each garage...")
        for garage_id in garage_list:
            if garage_id in shared.node_type:
                garage_data = shared.node_type[garage_id].get("garage_data", {})
                armada_count = garage_data.get("total_armada", 0)
                
                if armada_count > 0:
                    print(f"\n[Simulation] Garage {garage_id}: Creating {armada_count} vehicles...")
                    
                    for i in range(armada_count):
                        vehicle = Vehicle(GRAPH, TPS_nodes, TPA_nodes, garage_list, shared=shared)
                        vehicle.garage_node = garage_id
                        vehicle.current = garage_id
                        vehicle._update_garage_stats()
                        
                        vehicles.append(vehicle)
                        total_vehicles_created += 1
                        
                        if total_vehicles_created % 10 == 0:
                            print(f"[Simulation]   Progress: {total_vehicles_created} vehicles created...")
                    
                    print(f"[Simulation]   ✓ Garage {garage_id}: {armada_count} vehicles created")
        
        print(f"\n{'='*60}")
        print(f"[Simulation] ✓ Total vehicles created: {total_vehicles_created}")
        print(f"{'='*60}")
        
        if total_vehicles_created == 0:
            print(f"\n[WARNING] No armada configured in any garage!")
        
        shared.total_vehicles = total_vehicles_created
    else:
        print("[WARNING] No garage nodes found!")
    
    print(f"\n[Simulation] Assigning vehicles to shared state...")
    print(f"[Simulation]   Local: {len(vehicles)}, Shared (before): {len(shared.vehicles)}")
    
    shared.vehicles = vehicles
    
    print(f"[Simulation]   Shared (after): {len(shared.vehicles)}")
    
    if len(shared.vehicles) != len(vehicles):
        print(f"[ERROR] Mismatch! Local: {len(vehicles)}, Shared: {len(shared.vehicles)}")
    else:
        print(f"[Simulation] ✓ Vehicle assignment successful!")
    
    vehicle_ids = [v.id for v in shared.vehicles]
    unique_ids = set(vehicle_ids)
    if len(vehicle_ids) != len(unique_ids):
        print(f"[WARNING] Duplicate vehicle IDs!")
        print(f"[WARNING]   Total: {len(vehicle_ids)}, Unique: {len(unique_ids)}")
    
    print(f"{'='*60}\n")



# ========== INITIALIZE AND LOAD NODES ==========
def initNodes(GRAPH, shared):
    TPS_nodes = set()
    TPA_nodes = set()
    GARAGE_nodes = set()

    shared.init_node_types(GRAPH, TPS_nodes, TPA_nodes, GARAGE_nodes)
    
    for node_id, node_data in shared.node_type.items():
        if node_data.get("tps", False):
            TPS_nodes.add(node_id)
        if node_data.get("tpa", False):
            TPA_nodes.add(node_id)
        if node_data.get("garage", False):
            GARAGE_nodes.add(node_id)
    
    print(f"[Simulation] Loaded TPS nodes: {len(TPS_nodes)}")
    print(f"[Simulation] Loaded TPA nodes: {len(TPA_nodes)}")
    print(f"[Simulation] Loaded Garage nodes: {len(GARAGE_nodes)}")
    
    if TPA_nodes:
        print(f"[Simulation] TPA nodes list: {list(TPA_nodes)}")
    else:
        print(f"[Simulation] ⚠️ WARNING: NO TPA NODES CONFIGURED!")
    
    shared.node_count = GRAPH.number_of_nodes()
    shared.edge_count = GRAPH.number_of_edges()
    shared.num_tps = len(TPS_nodes)
    shared.num_tpa = len(TPA_nodes)
    shared.num_garage = len(GARAGE_nodes)

    generate_tps_garbage(TPS_nodes, shared)
    return TPS_nodes, TPA_nodes, GARAGE_nodes