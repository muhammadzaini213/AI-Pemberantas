import random
import math
import time
import networkx as nx
from collections import defaultdict

w1 = 0.0000001     # total distance
w2 = 0.1    # avg overtime penalty
w3 = 0.0001   # unserved TPS penalty
w4 = 0.00003    # workload imbalance penalty

# ------------------ shortest path cache ------------------
def make_sp_len_dict(graph):
    """Precompute shortest path lengths between all nodes (faster than lru_cache for repeated queries)"""
    sp_len = dict(nx.all_pairs_dijkstra_path_length(graph, weight='length'))
    return sp_len

# ------------------ split trips ------------------
def split_into_trips(tps_sequence, demand_per_tps, capacity, garage_node):
    route = [garage_node]
    curr_load = 0
    for t in tps_sequence:
        demand = demand_per_tps.get(t, 1)
        if curr_load + demand > capacity:
            route.append(garage_node)
            route.append(garage_node)  # start new trip
            curr_load = 0
        route.append(t)
        curr_load += demand
    if route[-1] != garage_node:
        route.append(garage_node)
    return route

# ------------------ evaluate ------------------
def evaluate_solution(graph, routes_per_vehicle, TPS_nodes, demand_per_tps,
                      vehicle_speeds, operational_time, sp_len_dict):
    distances_per_vehicle = []
    total_distance = 0.0
    unserved = set(TPS_nodes)

    for vidx, tps_seq in enumerate(routes_per_vehicle):
        garage_node = evaluate_solution.garage_choice[vidx]
        capacity = evaluate_solution.capacities[vidx]
        speed = vehicle_speeds[vidx] if vidx < len(vehicle_speeds) else vehicle_speeds[-1]

        trip_route = split_into_trips(tps_seq, demand_per_tps, capacity, garage_node)

        dist = 0.0
        for i in range(len(trip_route)-1):
            u, v = trip_route[i], trip_route[i+1]
            dist += sp_len_dict.get(u, {}).get(v, 1e8)
            if u in unserved:
                unserved.discard(u)

        distances_per_vehicle.append(dist)
        total_distance += dist

    # overtime
    overtime_list = []
    for vidx, dist in enumerate(distances_per_vehicle):
        speed = vehicle_speeds[vidx] if vidx < len(vehicle_speeds) else vehicle_speeds[-1]
        time_spent = dist / max(speed, 1e-6)
        overtime_list.append(max(0.0, time_spent - operational_time))
    avg_overtime = sum(overtime_list)/len(overtime_list)

    # workload std dev
    mean_load = sum(distances_per_vehicle)/len(distances_per_vehicle)
    std_dev = math.sqrt(sum((d-mean_load)**2 for d in distances_per_vehicle)/len(distances_per_vehicle))

    distance_penalty = (w1*total_distance)
    overtime_penalty = (w2*avg_overtime)
    unserved_penalty = (w3*len(unserved))
    imbalance_penalty = (w4*std_dev)

    print("Distance Penalty:", distance_penalty)
    print("Overtime Penalty:", overtime_penalty)
    print("Unserved Penalty:", unserved_penalty)
    print("Imbalance Penalty:", imbalance_penalty)

    cost = (w1*total_distance) + (w2*avg_overtime) + (w3*len(unserved)) + (w4*std_dev)

    breakdown = {
        "total_distance": total_distance,
        "avg_overtime": avg_overtime,
        "unserved_tps": len(unserved),
        "std_dev": std_dev
    }

    return cost, breakdown, distances_per_vehicle

# attributes
evaluate_solution.garage_choice = []
evaluate_solution.capacities = []

# ------------------ neighbor ------------------
def random_neighbor(routes):
    new_routes = [r.copy() for r in routes]
    nonempty = [i for i,r in enumerate(new_routes) if len(r)>0]
    if len(nonempty) < 1:
        return new_routes

    op = random.random()
    if op < 0.5 and len(nonempty)>=2:  # swap
        r1,r2 = random.sample(nonempty,2)
        i,j = random.randrange(len(new_routes[r1])), random.randrange(len(new_routes[r2]))
        new_routes[r1][i], new_routes[r2][j] = new_routes[r2][j], new_routes[r1][i]
    else:  # relocate
        src = random.choice(nonempty)
        dst_candidates = [i for i in range(len(new_routes)) if i != src]
        if not dst_candidates:
            return new_routes
        dst = random.choice(dst_candidates)
        idx = random.randrange(len(new_routes[src]))
        node = new_routes[src].pop(idx)
        pos = random.randrange(len(new_routes[dst])+1)
        new_routes[dst].insert(pos, node)
    return new_routes

# ------------------ initial ------------------
def initial_assignment_round_robin(TPS_nodes, num_vehicle):
    routes = [[] for _ in range(num_vehicle)]
    for i,t in enumerate(TPS_nodes):
        routes[i % num_vehicle].append(t)
    return routes

def simulated_annealing_vrp(graph, TPS_nodes, GARAGE_nodes,
                            vehicle_capacities, vehicle_speeds,
                            demand_per_tps=None,
                            operational_time=5000.0,
                            max_iter=5000,
                            T_start=1000.0, T_end=1e-3, alpha=0.995,
                            report_every=200, seed=None):
    if seed is not None:
        random.seed(seed)

    num_vehicle = len(vehicle_capacities)
    if demand_per_tps is None:
        demand_per_tps = {t:1 for t in TPS_nodes}

    # assign garage to each vehicle (round-robin)
    # jika GARAGE_nodes = [TPA_node], assign semua ke node yang sama
    evaluate_solution.garage_choice = [GARAGE_nodes[0]] * num_vehicle
    evaluate_solution.capacities = vehicle_capacities

    sp_len_dict = make_sp_len_dict(graph)

    # initial solution: distribute TPS round-robin
    current_routes = initial_assignment_round_robin(TPS_nodes[:], num_vehicle)
    best_routes = [r.copy() for r in current_routes]
    best_cost, _, _ = evaluate_solution(graph, best_routes, TPS_nodes, demand_per_tps, vehicle_speeds, operational_time, sp_len_dict)
    current_cost = best_cost
    cost_history = [best_cost]

    T = T_start
    start_time = time.time()
    last_report = 0

    print(f"[SA START] vehicles={num_vehicle} TPS={len(TPS_nodes)} initial_cost={best_cost:.2f}")

    for it in range(1,max_iter+1):
        new_routes = random_neighbor(current_routes)
        new_cost, _, _ = evaluate_solution(graph, new_routes, TPS_nodes, demand_per_tps, vehicle_speeds, operational_time, sp_len_dict)

        if new_cost < current_cost or math.exp((current_cost-new_cost)/max(T,1e-12)) > random.random():
            current_routes = new_routes
            current_cost = new_cost
            if new_cost < best_cost:
                best_cost = new_cost
                best_routes = [r.copy() for r in current_routes]

        cost_history.append(best_cost)
        T *= alpha

        if it - last_report >= report_every:
            elapsed = time.time()-start_time
            percent = (it/max_iter)*100
            eta = (elapsed/it)*(max_iter-it)
            print(f"[{percent:6.2f}%] Iter {it}/{max_iter} | BestCost {best_cost:.2f} | ETA {eta:.1f}s")
            last_report = it

        if T <= T_end:
            break

        # ---------------- expand routes with real shortest paths ----------------
    expanded_best_routes = []
    for vidx, seq in enumerate(best_routes):
        garage_node = evaluate_solution.garage_choice[vidx]
        capacity = evaluate_solution.capacities[vidx]

        # Jika truk idle
        if not seq:
            expanded_best_routes.append([garage_node, garage_node])
            continue

        # Pertama: split trip berdasarkan kapasitas
        trip_route = split_into_trips(seq, demand_per_tps, capacity, garage_node)

        # Kedua: ekspansi path graf agar mengikuti jalan sesungguhnya
        real_route = []
        for i in range(len(trip_route) - 1):
            u, v = trip_route[i], trip_route[i+1]
            try:
                sp = nx.dijkstra_path(graph, u, v, weight='length')
            except Exception:
                sp = [u, v]  # fallback jika path tidak ditemukan
            if real_route:
                sp = sp[1:]  # hindari node duplikat
            real_route.extend(sp)

        expanded_best_routes.append(real_route)

    print("[SA DONE] BestCost:", best_cost)
    return expanded_best_routes, best_cost, cost_history


            

    print("[SA DONE] BestCost:", best_cost)
    return expanded_best_routes, best_cost, cost_history
