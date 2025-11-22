import random

def generate_nodes(graph, num_tps=4, num_tpa=1):
    nodes = list(graph.nodes)

    TPS_nodes = random.sample(nodes, num_tps)
    TPA_nodes = random.sample([n for n in nodes if n not in TPS_nodes], num_tpa)

    return TPS_nodes, TPA_nodes
