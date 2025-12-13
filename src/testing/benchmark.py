import time
from collections import defaultdict
from ..utils.timesync import sync, getDt
from ..utils.nodes import initNodes, generate_daily_garbage, generate_car_in_garage
from ..classes.knowledge import KnowledgeModel
from ..classes.ai_model import AIModel
from ..environment import SHIFT_START, SHIFT_END
from .objective_function import ObjectiveFunction

def run_benchmark(GRAPH, shared, num_days=7, speed_multiplier=10, verbose=False):
    print(f"\n{'='*70}")
    print(f"[BENCHMARK] Starting {num_days}-day simulation (speed: {speed_multiplier}x)")
    print(f"{'='*70}\n")
    
    # ======================== INITIALIZATION ========================
    shared.vehicles.clear()
    shared.total_vehicles = 0
    shared.speed = speed_multiplier
    shared.paused = False
    
    sim_time_acc = 0.0
    last_time = time.time()
    
    TPS_nodes, TPA_nodes, GARAGE_nodes = initNodes(GRAPH, shared)
    
    vehicles = []
    generate_car_in_garage(GARAGE_nodes, shared, vehicles, GRAPH, TPS_nodes, TPA_nodes)
    
    last_garbage_generation_day = shared.sim_day
    
    # ======================== MODEL INITIALIZATION ========================
    knowledge_model = KnowledgeModel(GRAPH, shared, TPS_nodes, TPA_nodes, GARAGE_nodes)
    shared.knowledge_model = knowledge_model
    
    ai_model = AIModel(knowledge_model, shared)
    shared.ai_model = ai_model
    
    if verbose:
        print(f"[BENCHMARK] Initialized with {len(vehicles)} vehicles")
        print(f"[BENCHMARK] TPS: {len(TPS_nodes)}, TPA: {len(TPA_nodes)}, Garages: {len(GARAGE_nodes)}")
    
    # ======================== METRICS TRACKING ========================
    metrics = {
        "days_simulated": 0,
        "total_garbage_collected": 0,
        "total_trips": 0,
        "total_distance": 0,
        "total_reschedules": 0,
        "slowdown_discoveries": 0,
        "vehicles_used": len(vehicles),
        "daily_metrics": [],
        "hourly_slowdowns": defaultdict(int),
        "edge_slowdown_patterns": {},
        "vehicle_utilization": {},
        "tps_service_rates": {},
        "simulation_time_seconds": 0,
        "slowdown_encounters": 0
    }
    
    daily_start_time = time.time()
    target_hour = SHIFT_START
    
    # ======================== SIMULATION LOOP ========================
    simulation_start = time.time()
    
    while shared.sim_day <= num_days:
        dt, last_time = getDt(time, last_time)
        
        sim_time_acc += dt * shared.speed * (60 ** 1)
        total_minutes = int(sim_time_acc / 60)
        shared.sim_hour = (8 + (total_minutes // 60)) % 24
        shared.sim_min = total_minutes % 60
        shared.sim_day = 1 + (total_minutes // (24 * 60))
        
        last_garbage_generation_day = generate_daily_garbage(
            shared, TPS_nodes, ai_model, last_garbage_generation_day
        )
        
        ai_model.update(dt, vehicles)
        
        for v in vehicles:
            v.update(dt, shared)
        
        for v in vehicles:
            knowledge_model.update_vehicle_status(v.id, v.actuator_get_status())
        
        # ======================== METRICS COLLECTION ========================
        
        if shared.sim_hour == 0 and shared.sim_min == 0 and shared.sim_day > metrics["days_simulated"]:
            daily_elapsed = time.time() - daily_start_time
            
            current_slowdown_encounters = 0
            for edge_id, hour_data in knowledge_model.discovered_slowdowns.items():
                for hour, data in hour_data.items():
                    current_slowdown_encounters += data["count"]
            
            metrics["slowdown_encounters"] = current_slowdown_encounters
            
            daily_data = {
                "day": shared.sim_day - 1,
                "garbage_collected": ai_model.total_garbage_collected,
                "trips": ai_model.total_trips,
                "reschedules": ai_model.reschedule_count,
                "known_slowdowns": knowledge_model.get_slowdown_count(),
                "simulation_time": daily_elapsed,
                "vehicle_stats": {}
            }
            
            for v in vehicles:
                daily_data["vehicle_stats"][v.id] = {
                    "daily_dist": v.daily_dist,
                    "total_dist": v.total_dist,
                    "state": v.state,
                    "load": v.load
                }
                metrics["total_distance"] += v.daily_dist
                v.daily_dist = 0
            
            for tps_id in TPS_nodes:
                tps_data = shared.node_type[tps_id].get("tps_data", {})
                metrics["tps_service_rates"][tps_id] = {
                    "current_garbage": tps_data.get("sampah_kg", 0),
                    "daily_generation": tps_data.get("sampah_per_hari", 0),
                    "discovered": knowledge_model.get_discovered_garbage(tps_id)
                }
            
            metrics["daily_metrics"].append(daily_data)
            metrics["days_simulated"] = shared.sim_day - 1
            
            if verbose:
                print(f"\n{'='*70}")
                print(f"[BENCHMARK] Day {daily_data['day']} Complete")
                print(f"  Garbage Collected: {daily_data['garbage_collected']:.2f} kg")
                print(f"  Trips: {daily_data['trips']}")
                print(f"  Reschedules: {daily_data['reschedules']}")
                print(f"  Known Slowdowns: {daily_data['known_slowdowns']} patterns")
                print(f"  Real Time: {daily_elapsed:.2f}s")
                print(f"{'='*70}\n")
            
            daily_start_time = time.time()
            
            ai_model.reset_daily()
        
        if shared.sim_hour != target_hour:
            target_hour = shared.sim_hour
            if not verbose and shared.sim_hour % 4 == 0:
                print(f"[BENCHMARK] Day {shared.sim_day}, Hour {shared.sim_hour:02d}:00 - "
                      f"Garbage: {ai_model.total_garbage_collected:.0f}kg, "
                      f"Trips: {ai_model.total_trips}")
    
    simulation_end = time.time()
    metrics["simulation_time_seconds"] = simulation_end - simulation_start
    
    # ======================== FINAL METRICS ========================
    metrics["total_garbage_collected"] = ai_model.total_garbage_collected
    metrics["total_trips"] = ai_model.total_trips
    metrics["total_reschedules"] = ai_model.reschedule_count
    metrics["slowdown_discoveries"] = knowledge_model.get_slowdown_count()
    
    final_slowdown_encounters = 0
    for edge_id, hour_data in knowledge_model.discovered_slowdowns.items():
        for hour, data in hour_data.items():
            final_slowdown_encounters += data["count"]
            metrics["hourly_slowdowns"][hour] = metrics["hourly_slowdowns"].get(hour, 0) + data["count"]
    
    metrics["slowdown_encounters"] = final_slowdown_encounters
    
    slowdown_summary = knowledge_model.get_slowdown_summary()
    for hour, edges in slowdown_summary.items():
        metrics["edge_slowdown_patterns"][hour] = len(edges)
    
    for v in vehicles:
        metrics["vehicle_utilization"][v.id] = {
            "total_distance_km": v.total_dist,
            "final_state": v.state,
            "final_load": v.load
        }
    
    # ======================== PRINT SUMMARY ========================
    print(f"\n{'='*70}")
    print(f"[BENCHMARK] Simulation Complete!")
    print(f"{'='*70}")
    print(f"Days Simulated:           {metrics['days_simulated']}")
    print(f"Real Time:                {metrics['simulation_time_seconds']:.2f}s")
    print(f"Simulation Speed:         {speed_multiplier}x")
    print(f"")
    print(f"=== Collection Metrics ===")
    print(f"Total Garbage Collected:  {metrics['total_garbage_collected']:.2f} kg")
    print(f"Total Trips:              {metrics['total_trips']}")
    print(f"Total Distance:           {metrics['total_distance']:.2f} km")
    print(f"Avg per Day:              {metrics['total_garbage_collected']/max(1,metrics['days_simulated']):.2f} kg/day")
    print(f"")
    print(f"=== AI Performance ===")
    print(f"Reschedules:              {metrics['total_reschedules']}")
    print(f"Slowdown Patterns Found:  {metrics['slowdown_discoveries']}")
    print(f"Slowdown Encounters:      {metrics['slowdown_encounters']}")
    print(f"")
    print(f"=== Vehicle Performance ===")
    print(f"Vehicles Used:            {metrics['vehicles_used']}")
    avg_dist = metrics['total_distance'] / max(1, metrics['vehicles_used'])
    print(f"Avg Distance per Vehicle: {avg_dist:.2f} km")
    print(f"")
    print(f"=== Hourly Slowdown Distribution ===")
    for hour in sorted(metrics['hourly_slowdowns'].keys()):
        count = metrics['hourly_slowdowns'][hour]
        print(f"  Hour {hour:02d}:00 - {count} encounters")
    print(f"{'='*70}\n")
    
    # ======================== OBJECTIVE FUNCTION ========================
    print(f"{'='*70}")
    print(f"CALCULATING OBJECTIVE FUNCTION")
    print(f"{'='*70}")
    
    obj_func = ObjectiveFunction()
    obj_result = obj_func.calculate(metrics, shared, knowledge_model)
    obj_func.print_report(obj_result, "Benchmark Results")
    
    metrics['objective_function'] = obj_result
    
    return metrics

