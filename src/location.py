import random

def generate_tps_tpa_garage_nodes(GRAPH, num_tps=3, num_tpa=1, num_garage = 1):
    TPS_nodes = random.sample(list(GRAPH.nodes()), num_tps)
    TPA_nodes = random.sample(list(GRAPH.nodes()), num_tpa)
    GARAGE_nodes = random.sample(list(GRAPH.nodes()), num_garage)
    return TPS_nodes, TPA_nodes, GARAGE_nodes 

