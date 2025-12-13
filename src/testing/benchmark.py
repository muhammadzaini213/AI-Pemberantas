import time
from collections import defaultdict
from ..utils.timesync import sync, getDt
from ..utils.nodes import initNodes, generate_daily_garbage, generate_car_in_garage
from ..classes.knowledge import KnowledgeModel
from ..classes.ai_model import AIModel
from ..environment import SHIFT_START, SHIFT_END
from .objective_function import ObjectiveFunction

def run_benchmark(GRAPH, shared, num_days=7, speed_multiplier=10, verbose=True):
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
    knowledge_model = KnowledgeModel(GRAPH, shared, TPS_nodes, TPA_nodes, GARAGE_nodes)
    shared.knowledge_model = knowledge_model
    ai_model = AIModel(knowledge_model, shared)
    shared.ai_model = ai_model
    
    metrics = {
        "days_simulated": 0,
        "total_garbage_collected": 0,
        "total_trips": 0,
        "total_distance": 0,
        "total_reschedules": 0,
        "vehicles_used": len(vehicles),
        "daily_metrics": [],
        "hourly_slowdowns": defaultdict(int),
        "tps_service_rates": {},
        "simulation_time_seconds": 0,
        "vehicle_utilization": {},  # <-- tambahkan ini
    }

    
    daily_start_time = time.time()
    target_hour = SHIFT_START
    simulation_start = time.time()
    
    while shared.sim_day <= num_days:
        dt, last_time = getDt(time, last_time)
        sim_time_acc += dt * shared.speed * 60
        total_minutes = int(sim_time_acc / 60)
        shared.sim_hour = (8 + total_minutes // 60) % 24
        shared.sim_min = total_minutes % 60
        shared.sim_day = 1 + (total_minutes // (24*60))
        
        last_garbage_generation_day = generate_daily_garbage(
            shared, TPS_nodes, ai_model, last_garbage_generation_day
        )
        
        ai_model.update(dt, vehicles)
        for v in vehicles:
            v.update(dt, shared)
            knowledge_model.update_vehicle_status(v.id, v.actuator_get_status())
        
        if shared.sim_hour == 0 and shared.sim_min == 0 and shared.sim_day > metrics["days_simulated"]:
            daily_elapsed = time.time() - daily_start_time
            daily_data = {
                "day": shared.sim_day - 1,
                "garbage_collected": ai_model.total_garbage_collected,
                "trips": ai_model.total_trips,
                "reschedules": ai_model.reschedule_count,
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
    metrics["total_garbage_collected"] = ai_model.total_garbage_collected
    metrics["total_trips"] = ai_model.total_trips
    metrics["total_reschedules"] = ai_model.reschedule_count
    
    for v in vehicles:
        metrics["vehicle_utilization"][v.id] = {
            "total_dist": v.total_dist,
            "final_state": v.state,
            "final_load": v.load
        }
    
    obj_func = ObjectiveFunction()
    metrics['objective_function'] = obj_func.calculate(metrics, shared, knowledge_model)
    obj_func.print_report(metrics['objective_function'], scenario_name="Benchmark")
    return metrics
