import osmnx as ox
import time
from .sa_vrp_garage_as_tpa import simulated_annealing_vrp
from .location_generator import generate_nodes
from .sa_visualization import plot_cost_history, plot_final_routes

G = ox.load_graphml("./data/simpl_balikpapan_kota_drive.graphml")


NUM_TPS = 100 # Jumlah tps
NUM_VEHICLES = 4 # Jumlah truk sampah

TPS_nodes, TPA_nodes = generate_nodes(
    G, num_tps=NUM_TPS, num_tpa=1
)

num_vehicles = NUM_VEHICLES
vehicle_capacities = [100] * num_vehicles
vehicle_speeds = [5] * num_vehicles  


start_time = time.time()

best_routes, best_cost, history = simulated_annealing_vrp(
    G, TPS_nodes, TPA_nodes,
    vehicle_capacities=vehicle_capacities,
    vehicle_speeds=vehicle_speeds,
    demand_per_tps=None,
    operational_time=500000000.0,
    max_iter=3000,
    T_start=1000.0,
    T_end=0.01,
    alpha=0.995,
    report_every=200,
    seed=42
)

end_time = time.time()

elapsed = end_time - start_time


# Print results
print("\nBEST COST:", best_cost)
for i, r in enumerate(best_routes):
    print(f"Truck {i+1} route: {r}")

# Plot results
plot_cost_history(history)
plot_final_routes(G, best_routes, TPS_nodes, TPA_nodes)

print("Waktu Eksekusi:", elapsed, "s")

