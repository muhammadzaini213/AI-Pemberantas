import time
from collections import defaultdict
from ..utils.timesync import sync, getDt
from ..utils.nodes import initNodes, generate_daily_garbage, generate_car_in_garage
from ..classes.knowledge import KnowledgeModel
from ..classes.ai_model import AIModel
from ..environment import SHIFT_START, SHIFT_END
from ..utils.preprocessing import preprocess_graph

class PerformanceMeasure:
    """Class untuk mengukur dan tracking performance metrics"""
    
    def __init__(self, num_vehicles, shift_duration):
        self.num_vehicles = num_vehicles
        self.shift_duration = shift_duration  # dalam jam
        
        # Core metrics
        self.total_garbage_collected = 0
        self.total_trips = 0
        self.total_distance = 0
        self.total_work_time = 0  # dalam menit
        self.total_idle_time = 0
        
        # Vehicle-specific metrics
        self.vehicle_metrics = defaultdict(lambda: {
            'distance': 0,
            'trips': 0,
            'garbage_collected': 0,
            'work_time': 0,
            'idle_time': 0,
            'overtime': 0,
            'states_history': defaultdict(int),
            'last_trip_distance': 0
        })
        
        # TPS metrics
        self.tps_metrics = defaultdict(lambda: {
            'visits': 0,
            'garbage_collected': 0,
            'remaining_garbage': 0,
            'service_rate': 0.0,
            'total_generated': 0
        })
        
        # Efficiency metrics
        self.reschedules = 0
        self.failed_routes = 0
        self.congestion_encounters = 0
        
        # Time tracking
        self.daily_performance = []
        
        # Snapshot untuk comparison
        self.last_snapshot = {
            'garbage': 0,
            'trips': 0,
            'distance': 0
        }
    
    def update_from_snapshot(self, ai_model, vehicles, tps_nodes, shared):
        """
        Update metrics dari snapshot AI model dan vehicles
        Lebih reliable daripada tracking incremental
        """
        # Update dari AI model
        self.total_garbage_collected = ai_model.total_garbage_collected
        self.total_trips = ai_model.total_trips
        self.reschedules = ai_model.reschedule_count
        
        # Update dari vehicles - sesuai struktur Vehicle class
        total_distance = 0
        for v in vehicles:
            vid = v.id
            # Vehicle.total_dist sudah dalam km, tidak perlu dibagi lagi
            self.vehicle_metrics[vid]['distance'] = v.total_dist
            self.vehicle_metrics[vid]['trips'] = 0  # akan dihitung dari garbage
            total_distance += v.total_dist
        
        self.total_distance = total_distance
        
        # Update TPS metrics
        for tps_id in tps_nodes:
            tps_data = shared.node_type.get(tps_id, {}).get("tps_data", {})
            current = tps_data.get("sampah_kg", 0)
            daily_gen = tps_data.get("sampah_per_hari", 0)
            
            self.tps_metrics[tps_id]['remaining_garbage'] = current
            self.tps_metrics[tps_id]['total_generated'] = daily_gen
            
            # Estimate garbage collected (generated - remaining)
            collected = max(0, daily_gen - current)
            self.tps_metrics[tps_id]['garbage_collected'] = collected
    
    def calculate_kpis(self):
        """Calculate Key Performance Indicators"""
        kpis = {}
        
        # 1. Collection Efficiency
        total_generated = sum(m['total_generated'] for m in self.tps_metrics.values())
        total_remaining = sum(m['remaining_garbage'] for m in self.tps_metrics.values())
        
        if total_generated > 0:
            kpis['collection_rate'] = ((total_generated - total_remaining) / total_generated * 100)
        else:
            kpis['collection_rate'] = 0
        
        # 2. Distance & Trip Metrics (distance sudah dalam km dari Vehicle)
        kpis['total_distance_km'] = self.total_distance
        kpis['total_trips'] = self.total_trips
        kpis['total_garbage_kg'] = self.total_garbage_collected
        
        # 3. Efficiency Metrics
        if self.total_trips > 0:
            kpis['avg_garbage_per_trip'] = self.total_garbage_collected / self.total_trips
            kpis['avg_distance_per_trip'] = (self.total_distance * 1000) / self.total_trips  # convert to meters
        else:
            kpis['avg_garbage_per_trip'] = 0
            kpis['avg_distance_per_trip'] = 0
        
        if self.total_distance > 0:
            kpis['garbage_per_km'] = self.total_garbage_collected / self.total_distance
        else:
            kpis['garbage_per_km'] = 0
        
        # 4. Vehicle Performance
        kpis['vehicles_performance'] = {}
        for vid, metrics in self.vehicle_metrics.items():
            if metrics['distance'] > 0:
                efficiency = self.total_garbage_collected / metrics['distance']
            else:
                efficiency = 0
                
            kpis['vehicles_performance'][vid] = {
                'distance_km': metrics['distance'],
                'total_dist_m': metrics['distance'] * 1000,
                'efficiency': efficiency
            }
        
        # 5. TPS Service Quality
        serviced_tps = sum(1 for m in self.tps_metrics.values() 
                          if m['total_generated'] > 0 and m['remaining_garbage'] < m['total_generated'])
        total_tps = sum(1 for m in self.tps_metrics.values() if m['total_generated'] > 0)
        
        kpis['tps_coverage'] = (serviced_tps / total_tps * 100) if total_tps > 0 else 0
        
        # Average service rate per TPS
        service_rates = []
        for m in self.tps_metrics.values():
            if m['total_generated'] > 0:
                rate = ((m['total_generated'] - m['remaining_garbage']) / m['total_generated'] * 100)
                service_rates.append(rate)
        
        kpis['avg_tps_service_rate'] = sum(service_rates) / len(service_rates) if service_rates else 0
        
        # 6. Operational Metrics
        kpis['reschedules_per_trip'] = (self.reschedules / self.total_trips) if self.total_trips > 0 else 0
        kpis['failed_routes'] = self.failed_routes
        kpis['total_reschedules'] = self.reschedules
        
        # 7. Vehicle Utilization (simplified - based on distance)
        avg_distance_per_vehicle = self.total_distance / self.num_vehicles if self.num_vehicles > 0 else 0
        # Estimate: 8 hour shift, 20 km/h avg speed = 160 km max potential
        max_potential_distance = self.shift_duration * 20  # in km
        kpis['vehicle_utilization'] = (avg_distance_per_vehicle / max_potential_distance * 100) if max_potential_distance > 0 else 0
        
        return kpis
    
    def print_performance_report(self):
        """Print comprehensive performance report"""
        kpis = self.calculate_kpis()
        
        print("\n" + "="*70)
        print("PERFORMANCE MEASUREMENT REPORT")
        print("="*70)
        
        print("\n📊 COLLECTION PERFORMANCE")
        print(f"  Total Garbage Collected: {self.total_garbage_collected:,.0f} kg")
        print(f"  Collection Rate: {kpis['collection_rate']:.1f}%")
        
        print("\n🚛 DISTANCE & EFFICIENCY")
        print(f"  Total Distance: {kpis['total_distance_km']:.2f} km")
        print(f"  Efficiency: {kpis['garbage_per_km']:.1f} kg/km")
        print(f"  Vehicle Utilization (distance-based): {kpis['vehicle_utilization']:.1f}%")
        
        print("\n🎯 TPS SERVICE QUALITY")
        print(f"  TPS Coverage: {kpis['tps_coverage']:.1f}%")
        print(f"  Average Service Rate: {kpis['avg_tps_service_rate']:.1f}%")
        serviced = sum(1 for m in self.tps_metrics.values() 
                    if m['total_generated'] > 0 and m['remaining_garbage'] < m['total_generated'])
        total = sum(1 for m in self.tps_metrics.values() if m['total_generated'] > 0)
        print(f"  TPS Serviced: {serviced}/{total}")
        
        print("\n⚙️ OPERATIONAL EFFICIENCY")
        print(f"  Total Reschedules: {self.reschedules}")
        print(f"  Failed Routes: {kpis['failed_routes']}")
        
        print("\n🚗 INDIVIDUAL VEHICLE PERFORMANCE")
        for vid, perf in kpis['vehicles_performance'].items():
            print(f"  {vid}:")
            print(f"    Distance: {perf['distance_km']:.2f} km")
            print(f"    Efficiency: {perf['efficiency']:.1f} kg/km")
        
        print("\n" + "="*70)
        
        return kpis



def run_benchmark(GRAPH, shared, num_days=7, speed_multiplier=10, verbose=True):
    """Enhanced benchmark with comprehensive performance measurement"""
    
    shared.vehicles.clear()
    shared.total_vehicles = 0
    shared.speed = speed_multiplier
    shared.paused = False
    
    sim_time_acc = 0.0
    last_time = time.time()
    
    # Initialize
    TPS_nodes, TPA_nodes, GARAGE_nodes = initNodes(GRAPH, shared)
    GRAPH = preprocess_graph(GRAPH, TPS_nodes, TPA_nodes, GARAGE_nodes)
    vehicles = []
    generate_car_in_garage(GARAGE_nodes, shared, vehicles, GRAPH, TPS_nodes, TPA_nodes)
    
    last_garbage_generation_day = shared.sim_day
    knowledge_model = KnowledgeModel(GRAPH, shared, TPS_nodes, TPA_nodes, GARAGE_nodes)
    shared.knowledge_model = knowledge_model
    ai_model = AIModel(knowledge_model, shared)
    shared.ai_model = ai_model
    
    # Initialize Performance Measure
    shift_duration = SHIFT_END - SHIFT_START
    performance = PerformanceMeasure(len(vehicles), shift_duration)
    
    # Tracking metrics
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
        "vehicle_utilization": {},
        "performance_kpis": {}
    }
    
    daily_start_time = time.time()
    target_hour = SHIFT_START
    simulation_start = time.time()
    
    # Main simulation loop
    while shared.sim_day <= num_days:
        dt, last_time = getDt(time, last_time)
        sim_time_acc += dt * shared.speed * 60
        total_minutes = int(sim_time_acc / 60)
        
        shared.sim_hour = (8 + total_minutes // 60) % 24
        shared.sim_min = total_minutes % 60
        shared.sim_day = 1 + (total_minutes // (24*60))
        
        # Generate garbage
        last_garbage_generation_day = generate_daily_garbage(
            shared, TPS_nodes, ai_model, last_garbage_generation_day
        )
        
        # Update AI and vehicles
        ai_model.update(dt, vehicles)
        
        for v in vehicles:
            v.update(dt, shared)
            knowledge_model.update_vehicle_status(v.id, v.actuator_get_status())
        
        # Daily report
        if shared.sim_hour == 0 and shared.sim_min == 0 and shared.sim_day > metrics["days_simulated"]:
            daily_elapsed = time.time() - daily_start_time
            
            # Update performance measure dari snapshot
            performance.update_from_snapshot(ai_model, vehicles, TPS_nodes, shared)
            
            # Compile daily data
            daily_data = {
                "day": shared.sim_day - 1,
                "garbage_collected": ai_model.total_garbage_collected,
                "trips": ai_model.total_trips,
                "reschedules": ai_model.reschedule_count,
                "vehicle_stats": {}
            }
            
            for v in vehicles:
                daily_data["vehicle_stats"][v.id] = {
                    "daily_dist": v.daily_dist,  # sudah dalam km
                    "total_dist": v.total_dist,  # sudah dalam km
                    "state": v.state,
                    "load": v.load
                }
                metrics["total_distance"] += v.daily_dist  # sudah dalam km
                v.daily_dist = 0
            
            # TPS service rates
            for tps_id in TPS_nodes:
                tps_data = shared.node_type[tps_id].get("tps_data", {})
                current_garbage = getattr(tps_data, "sampah_kg", 0) if "sampah_kg" in tps_data else 0
                daily_generation = tps_data.get("sampah_per_hari", 0)
                
                # Simulasikan garbage yang terkumpul: generated - current
                collected = max(0, daily_generation - current_garbage)
                
                # Simpan ke metrics
                performance.tps_metrics[tps_id]['remaining_garbage'] = current_garbage
                performance.tps_metrics[tps_id]['total_generated'] = daily_generation
                performance.tps_metrics[tps_id]['garbage_collected'] = collected
            
            metrics["daily_metrics"].append(daily_data)
            metrics["days_simulated"] = shared.sim_day - 1
            
            # Calculate daily KPIs
            daily_kpis = performance.calculate_kpis()
            performance.daily_performance.append({
                'day': shared.sim_day - 1,
                'kpis': daily_kpis
            })
            
            if verbose:
                print(f"\n[BENCHMARK] Day {shared.sim_day - 1} Summary:")
                print(f"  Garbage Collected: {ai_model.total_garbage_collected:.0f}kg")
                print(f"  Trips: {ai_model.total_trips}")
                print(f"  Distance: {performance.total_distance:.2f}km")
                print(f"  Collection Rate: {daily_kpis['collection_rate']:.1f}%")
            
            daily_start_time = time.time()
            ai_model.reset_daily()
        
        # Hourly updates
        if shared.sim_hour != target_hour:
            target_hour = shared.sim_hour
            if not verbose and shared.sim_hour % 4 == 0:
                print(f"[BENCHMARK] Day {shared.sim_day}, Hour {shared.sim_hour:02d}:00 - "
                      f"Garbage: {ai_model.total_garbage_collected:.0f}kg, "
                      f"Trips: {ai_model.total_trips}")
    
    # Final calculations
    simulation_end = time.time()
    metrics["simulation_time_seconds"] = simulation_end - simulation_start
    metrics["total_garbage_collected"] = ai_model.total_garbage_collected
    metrics["total_trips"] = ai_model.total_trips
    metrics["total_reschedules"] = ai_model.reschedule_count
    
    # Final update performance dari snapshot
    performance.update_from_snapshot(ai_model, vehicles, TPS_nodes, shared)
    
    for v in vehicles:
        metrics["vehicle_utilization"][v.id] = {
            "total_dist": v.total_dist,
            "final_state": v.state,
            "final_load": v.load
        }
    
    # Calculate final KPIs
    final_kpis = performance.calculate_kpis()
    metrics['performance_kpis'] = final_kpis
    metrics['total_distance'] = performance.total_distance
    
    # Print performance report
    performance.print_performance_report()
    
    # Print summary
    print("\n" + "="*70)
    print("SIMULATION SUMMARY")
    print("="*70)
    print(f"Days Simulated:           {metrics['days_simulated']}")
    print(f"Simulation Time:          {metrics['simulation_time_seconds']:.2f}s")
    print(f"")
    print(f"Total Distance:           {performance.total_distance:.2f} km")
    print(f"Total Garbage Collected:  {performance.total_garbage_collected:,.0f} kg")
    print(f"Total Trips:              {performance.total_trips}")
    print(f"Total Reschedules:        {performance.reschedules}")
    print(f"")
    print(f"Collection Rate:          {final_kpis['collection_rate']:.1f}%")
    print(f"Efficiency:               {final_kpis['garbage_per_km']:.1f} kg/km")
    print(f"Avg per Trip:             {final_kpis['avg_garbage_per_trip']:.1f} kg")
    print(f"Avg Distance per Trip:    {final_kpis['avg_distance_per_trip']:.0f} m")
    print(f"Vehicle Utilization:      {final_kpis['vehicle_utilization']:.1f}%")
    print(f"TPS Coverage:             {final_kpis['tps_coverage']:.1f}%")
    print("="*70)
    
    return metrics