import random
from environment import NUM_TPA

def generate_tps_tpa_nodes(GRAPH, num_tps=3, num_tpa=1):
    TPS_nodes = random.sample(list(GRAPH.nodes()), num_tps)
    TPA_nodes = [random.choice(list(GRAPH.nodes())) for _ in range(num_tpa)]
    return TPS_nodes, TPA_nodes[NUM_TPA]

