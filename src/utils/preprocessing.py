import networkx as nx

def preprocess_graph(graph, TPS_nodes, TPA_nodes, GARAGE_nodes):
    """
    Preprocessing graph:
    - Hapus node terisolasi yang tidak terkait node penting
    - Hapus node biasa degree 1
    - Hapus node bolak-balik buntu (degree 2 dengan edge bolak-balik)
    - Rekursif sampai tidak ada node baru dihapus
    - Node di exclude_nodes akan ditarget untuk dihapus
    """
    g = graph.copy()
    important_nodes = set(TPS_nodes) | set(TPA_nodes) | set(GARAGE_nodes)
    removed_total = 0

    # 1️⃣ Hapus node terisolasi (tidak terkait node penting)
    if g.is_directed():
        components = list(nx.weakly_connected_components(g))
    else:
        components = list(nx.connected_components(g))

    for comp in components:
        # Hapus semua node di komponen yang tidak terkait node penting
        if not important_nodes.intersection(comp):
            g.remove_nodes_from(comp)
            removed_total += len(comp)

    # 2️⃣ Hapus node biasa degree 1
    nodes_to_remove = [n for n in g.nodes if n not in important_nodes and g.degree[n] == 1]
    g.remove_nodes_from(nodes_to_remove)
    removed_total += len(nodes_to_remove)

    # 3️⃣ Hapus node bolak-balik buntu (degree 2 dan 2 edge bolak-balik)
    if g.is_directed():
        for n in list(g.nodes):
            if n in important_nodes:
                continue
            if g.degree[n] == 2:
                succ = set(g.successors(n))
                pred = set(g.predecessors(n))
                # cek edge bolak-balik
                if succ == pred and len(succ) == 1:
                    target = list(succ)[0]
                    # cek jalannya buntu: tidak ada path ke node penting
                    if not any(nx.has_path(g, target, imp) for imp in important_nodes):
                        g.remove_node(n)
                        removed_total += 1


    print(f"[Preprocessing Safe Aggressive] Removed {removed_total} irrelevant nodes in this pass")

    # 5️⃣ Rekursi jika ada node yang dihapus
    if removed_total > 0:
        return preprocess_graph(g, TPS_nodes, TPA_nodes, GARAGE_nodes)
    else:
        return g
