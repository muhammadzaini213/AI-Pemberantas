import networkx as nx
from multiprocessing import Pool, cpu_count

def _is_safe_to_remove(args):
    n, g, TPS_nodes, GARAGE_nodes, TPA_nodes = args

    important_nodes = set(TPS_nodes) | set(GARAGE_nodes) | set(TPA_nodes)
    if n in important_nodes or g.degree[n] > 2:
        return None

    safe_to_remove = True
    for src in TPS_nodes | GARAGE_nodes:
        for tgt in TPA_nodes:
            if nx.has_path(g, src, tgt):
                temp_g = g.copy()
                temp_g.remove_node(n)
                if not nx.has_path(temp_g, src, tgt):
                    safe_to_remove = False
                    break
        if not safe_to_remove:
            break

    if safe_to_remove or g.degree[n] == 0:
        return n
    return None

def preprocess_graph(graph, TPS_nodes, TPA_nodes, GARAGE_nodes):
    """
    Preprocessing agresif tapi aman dengan multiprocessing
    """
    g = graph.copy()
    removed_total = 0

    while True:
        args = [(n, g, TPS_nodes, GARAGE_nodes, TPA_nodes) for n in g.nodes]
        with Pool(cpu_count()) as pool:
            results = pool.map(_is_safe_to_remove, args)

        nodes_to_remove = [n for n in results if n is not None]

        if not nodes_to_remove:
            break

        g.remove_nodes_from(nodes_to_remove)
        removed_total += len(nodes_to_remove)

    print(f"[Preprocessing Safe Aggressive MP] Preprocessed graph: removed {removed_total} irrelevant nodes")
    return g