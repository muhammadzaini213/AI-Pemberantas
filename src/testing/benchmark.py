import time
from collections import defaultdict
from ..utils.timesync import sync, getDt
from ..utils.nodes import initNodes, generate_daily_garbage, generate_car_in_garage
from ..classes.knowledge import KnowledgeModel
from ..classes.ai_model import AIModel
from ..environment import SHIFT_START, SHIFT_END

class PerformanceMeasure:
    def __init__(self, num_vehicles, shift_duration):
        self.num_vehicles = num_vehicles
        self.shift_duration = shift_duration

        self.total_garbage_collected = 0
        self.total_trips = 0
        self.total_distance = 0
        self.reschedules = 0

        self.vehicle_metrics = defaultdict(lambda: {
            "distance": 0
        })

        self.tps_metrics = defaultdict(lambda: {
            "remaining_garbage": 0,
            "total_generated": 0
        })

    def update_from_snapshot(self, ai_model, vehicles, tps_nodes, shared):
        self.total_garbage_collected = ai_model.total_garbage_collected
        self.total_trips = ai_model.total_trips
        self.reschedules = ai_model.reschedule_count

        self.total_distance = 0
        for v in vehicles:
            self.vehicle_metrics[v.id]["distance"] = v.total_dist
            self.total_distance += v.total_dist

        for tps_id in tps_nodes:
            tps = shared.node_type[tps_id]["tps_data"]
            self.tps_metrics[tps_id]["remaining_garbage"] = tps["sampah_kg"]
            self.tps_metrics[tps_id]["total_generated"] = tps["sampah_per_hari"]

    def calculate_kpis(self):
        total_generated = sum(m["total_generated"] for m in self.tps_metrics.values())
        total_remaining = sum(m["remaining_garbage"] for m in self.tps_metrics.values())

        collection_rate = (
            ((total_generated - total_remaining) / total_generated) * 100
            if total_generated > 0 else 0
        )

        active_vehicles = sum(
            1 for v in self.vehicle_metrics.values()
            if v["distance"] > 0
        )

        vehicle_utilization = (
            (active_vehicles / self.num_vehicles) * 100
            if self.num_vehicles > 0 else 0
        )

        covered_tps = sum(
            1 for m in self.tps_metrics.values()
            if m["total_generated"] > 0 and m["remaining_garbage"] < m["total_generated"]
        )

        tps_coverage = (
            (covered_tps / len(self.tps_metrics)) * 100
            if self.tps_metrics else 0
        )

        return {
            "collection_rate": collection_rate,
            "total_distance_km": self.total_distance,
            "total_trips": self.total_trips,
            "total_garbage_kg": self.total_garbage_collected,
            "avg_garbage_per_trip": (
                self.total_garbage_collected / self.total_trips
                if self.total_trips > 0 else 0
            ),
            "avg_distance_per_trip": (
                (self.total_distance * 1000) / self.total_trips
                if self.total_trips > 0 else 0
            ),
            "garbage_per_km": (
                self.total_garbage_collected / self.total_distance
                if self.total_distance > 0 else 0
            ),
            "vehicle_utilization": vehicle_utilization,
            "tps_coverage": tps_coverage
        }


def run_benchmark(GRAPH, shared, num_days=7, speed_multiplier=10, verbose=True):

    shared.vehicles.clear()
    shared.total_vehicles = 0
    shared.speed = speed_multiplier
    shared.paused = False

    sim_time_acc = 0.0
    last_time = time.time()

    # ================== INIT ==================
    TPS_nodes, TPA_nodes, GARAGE_nodes = initNodes(GRAPH, shared)

    vehicles = []
    generate_car_in_garage(GARAGE_nodes, shared, vehicles, GRAPH, TPS_nodes, TPA_nodes)

    knowledge_model = KnowledgeModel(GRAPH, shared, TPS_nodes, TPA_nodes, GARAGE_nodes)
    shared.knowledge_model = knowledge_model

    ai_model = AIModel(knowledge_model, shared)
    shared.ai_model = ai_model

    shift_duration = SHIFT_END - SHIFT_START
    performance = PerformanceMeasure(len(vehicles), shift_duration)

    metrics = {
        "days_simulated": 0,
        "total_garbage_collected": 0,
        "total_trips": 0,
        "total_distance": 0,
        "total_reschedules": 0,
        "vehicles_used": len(vehicles),
        "daily_metrics": [],
        "simulation_time_seconds": 0,
        "performance_kpis": {}
    }

    last_garbage_generation_day = shared.sim_day
    simulation_start = time.time()

    last_reported_day = 0

    # ================== MAIN LOOP ==================
    while shared.sim_day <= num_days:
        dt, last_time = getDt(time, last_time)
        sim_time_acc += dt * shared.speed * 60

        total_minutes = int(sim_time_acc / 60)
        shared.sim_hour = (SHIFT_START + total_minutes // 60) % 24
        shared.sim_min = total_minutes % 60
        shared.sim_day = 1 + (total_minutes // (24 * 60))

        if shared.sim_day < num_days:
            last_garbage_generation_day = generate_daily_garbage(
                shared, TPS_nodes, ai_model, last_garbage_generation_day
            )

        # Update AI + vehicles
        ai_model.update(dt, vehicles)
        for v in vehicles:
            v.update(dt, shared)
            knowledge_model.update_vehicle_status(v.id, v.actuator_get_status())

        if (
            shared.sim_hour == SHIFT_END
            and shared.sim_min == 0
            and shared.sim_day - 1 > last_reported_day
        ):
            day = shared.sim_day - 1
            last_reported_day = day

            performance.update_from_snapshot(ai_model, vehicles, TPS_nodes, shared)

            daily_data = {
                "day": day,
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
                v.daily_dist = 0

            metrics["daily_metrics"].append(daily_data)
            metrics["days_simulated"] = day

            daily_kpis = performance.calculate_kpis()
            performance.daily_performance.append({
                "day": day,
                "kpis": daily_kpis
            })

            if verbose:
                print(f"\n[BENCHMARK] Day {day} Summary")
                print(f"  Garbage: {ai_model.total_garbage_collected:,.0f} kg")
                print(f"  Rate:    {daily_kpis['collection_rate']:.1f}%")

            ai_model.reset_daily()

    # ================== FINAL SNAPSHOT ==================
    simulation_end = time.time()
    performance.update_from_snapshot(ai_model, vehicles, TPS_nodes, shared)

    final_kpis = performance.calculate_kpis()

    metrics["simulation_time_seconds"] = simulation_end - simulation_start
    metrics["total_garbage_collected"] = performance.total_garbage_collected
    metrics["total_distance"] = performance.total_distance
    metrics["performance_kpis"] = final_kpis

    # ================== REPORT ==================
    print("\n" + "=" * 70)
    print("SIMULATION SUMMARY")
    print("=" * 70)
    print(f"Days Simulated:           {metrics['days_simulated'] + 1}")
    print(f"Simulation Time:          {metrics['simulation_time_seconds']:.2f}s\n")
    print(f"Total Distance:           {metrics['total_distance']:.2f} km")
    print(f"Total Garbage Collected:  {metrics['total_garbage_collected']:,.0f} kg")
    print(f"Collection Rate:          {final_kpis['collection_rate']:.1f}%")
    print(f"Efficiency:               {final_kpis['garbage_per_km']:.1f} kg/km")
    print(f"Vehicle Utilization:      {final_kpis['vehicle_utilization']:.1f}%")
    print(f"TPS Coverage:             {final_kpis['tps_coverage']:.1f}%")
    print("=" * 70)

    return metrics
