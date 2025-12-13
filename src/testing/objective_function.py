import numpy as np
from typing import Dict, List, Any
from ..environment import VEHICLE_SPEED, SHIFT_START, SHIFT_END

class ObjectiveFunction:
    def __init__(self, w1=1.0, w2=100.0, w3=5000.0, w4=0.3):
        self.w1 = w1  # Distance weight
        self.w2 = w2  # Overtime weight
        self.w3 = w3  # Unserved TPS weight
        self.w4 = w4  # Workload std dev weight
        
        self.SHIFT_START = SHIFT_START
        self.SHIFT_END = SHIFT_END
        self.SHIFT_DURATION_HOURS = self.SHIFT_END - self.SHIFT_START  # 9 hours
        
    def calculate(self, metrics: Dict[str, Any], shared=None, knowledge_model=None) -> Dict[str, float]:
        total_distance_km = metrics.get('total_distance', 0)
        avg_overtime_minutes = self._calculate_avg_overtime(metrics)
        unserved_tps_count = self._calculate_unserved_tps(metrics, shared, knowledge_model)
        workload_std_dev_km = self._calculate_workload_std_dev(metrics)
        
        # ============== CALCULATE COSTS ==============
        distance_cost = self.w1 * total_distance_km
        overtime_cost = self.w2 * avg_overtime_minutes
        unserved_cost = self.w3 * unserved_tps_count
        workload_cost = self.w4 * workload_std_dev_km
        
        objective_value = distance_cost + overtime_cost + unserved_cost + workload_cost
        
        return {
            'total_distance_km': total_distance_km,
            'avg_overtime_minutes': avg_overtime_minutes,
            'unserved_tps_count': unserved_tps_count,
            'workload_std_dev_km': workload_std_dev_km,
            'objective_value': objective_value,
            'components': {
                'distance_cost': distance_cost,
                'overtime_cost': overtime_cost,
                'unserved_cost': unserved_cost,
                'workload_cost': workload_cost
            },
            'weights': {
                'w1': self.w1,
                'w2': self.w2,
                'w3': self.w3,
                'w4': self.w4
            }
        }
    
    def _calculate_avg_overtime(self, metrics: Dict[str, Any]) -> float:
        daily_metrics = metrics.get('daily_metrics', [])
        if not daily_metrics:
            return 0.0
        
        total_overtime_minutes = 0.0
        total_vehicle_days = 0
        
        for day_data in daily_metrics:
            vehicle_stats = day_data.get('vehicle_stats', {})
            
            for vehicle_id, stats in vehicle_stats.items():
                distance_km = stats.get('daily_dist', 0)
                estimated_hours = distance_km / VEHICLE_SPEED
                
                overtime_hours = max(0, estimated_hours - self.SHIFT_DURATION_HOURS)
                total_overtime_minutes += overtime_hours * 60
                total_vehicle_days += 1
        
        avg_overtime = total_overtime_minutes / max(1, total_vehicle_days)
        return avg_overtime
    
    def _calculate_unserved_tps(self, metrics: Dict[str, Any], shared=None, knowledge_model=None) -> int:
        if not shared or not knowledge_model:
            total_garbage_collected = metrics.get('total_garbage_collected', 0)
            return 0
        
        unserved_count = 0
        tps_service_rates = metrics.get('tps_service_rates', {})
        
        for tps_id, data in tps_service_rates.items():
            current_garbage = data.get('current_garbage', 0)
            daily_generation = data.get('daily_generation', 0)
            
            if current_garbage > daily_generation * 0.5:
                unserved_count += 1
        
        return unserved_count
    
    def _calculate_workload_std_dev(self, metrics: Dict[str, Any]) -> float:
        vehicle_utilization = metrics.get('vehicle_utilization', {})
        
        if not vehicle_utilization:
            return 0.0
        
        distances = [
            data.get('total_distance_km', 0) 
            for data in vehicle_utilization.values()
        ]
        
        if len(distances) < 2:
            return 0.0
        
        std_dev = np.std(distances)
        return std_dev
    
    def print_report(self, result: Dict[str, Any], scenario_name: str = "Simulation"):
        print("\n" + "="*70)
        print(f"OBJECTIVE FUNCTION REPORT: {scenario_name}")
        print("="*70)
        
        print("\n--- Raw Metrics ---")
        print(f"Total Distance:           {100 * result['total_distance_km']:.2f} km")
        print(f"Avg Overtime per Vehicle: {result['avg_overtime_minutes']:.2f} minutes")
        print(f"Unserved TPS Count:       {result['unserved_tps_count']}")
        print(f"Workload Std Dev:         {result['workload_std_dev_km']:.2f} km")
        
        print("\n--- Weighted Costs ---")
        components = result['components']
        print(f"Distance Cost:   {components['distance_cost']:>12.2f}  (w1={result['weights']['w1']} × {result['total_distance_km']:.2f})")
        print(f"Overtime Cost:   {components['overtime_cost']:>12.2f}  (w2={result['weights']['w2']} × {result['avg_overtime_minutes']:.2f})")
        print(f"Unserved Cost:   {components['unserved_cost']:>12.2f}  (w3={result['weights']['w3']} × {result['unserved_tps_count']})")
        print(f"Workload Cost:   {components['workload_cost']:>12.2f}  (w4={result['weights']['w4']} × {result['workload_std_dev_km']:.2f})")
        
        print("\n--- Total Objective Value ---")
        print(f"OBJECTIVE = {result['objective_value']:.2f}")
        
        total = result['objective_value']
        if total > 0:
            print("\n--- Cost Breakdown ---")
            print(f"Distance:  {(components['distance_cost']/total)*100:>6.2f}%")
            print(f"Overtime:  {(components['overtime_cost']/total)*100:>6.2f}%")
            print(f"Unserved:  {(components['unserved_cost']/total)*100:>6.2f}%")
            print(f"Workload:  {(components['workload_cost']/total)*100:>6.2f}%")
        
        print("="*70 + "\n")



# ============== INTEGRATION ==============
def evaluate_benchmark_with_objective(metrics, shared=None, knowledge_model=None):
    obj_func = ObjectiveFunction()
    result = obj_func.calculate(metrics, shared, knowledge_model)
    obj_func.print_report(result)
    return result
