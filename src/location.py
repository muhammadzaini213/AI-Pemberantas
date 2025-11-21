import random

def generate_tps_tpa_nodes(G, num_tps=3, num_tpa=1):
    TPS_nodes = random.sample(list(G.nodes()), num_tps)
    TPA_nodes = [random.choice(list(G.nodes())) for _ in range(num_tpa)]
    # Biasanya 1 TPA saja
    return TPS_nodes, TPA_nodes[0]

