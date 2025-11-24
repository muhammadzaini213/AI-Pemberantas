import matplotlib.pyplot as plt
import networkx as nx


def plot_cost_history(cost_history):
    plt.figure(figsize=(8, 5))
    plt.plot(cost_history, linewidth=2, color="purple")
    plt.xlabel("Iteration")
    plt.ylabel("Cost")
    plt.title("SA Convergence Curve")
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def plot_final_routes(graph, best_routes, TPS_nodes, TPA_nodes):
    pos = {n: (data['x'], data['y']) for n, data in graph.nodes(data=True)}

    plt.figure(figsize=(12, 10))

    # ===== Dasar Map: Jalan =====
    nx.draw_networkx_edges(graph, pos, alpha=0.25, width=0.6, edge_color="gray")

    # ===== TPS (kuning) =====
    nx.draw_networkx_nodes(
        graph, pos,
        nodelist=TPS_nodes,
        node_size=80,
        node_color="yellow",
        label="TPS"
    )

    # ===== TPA / Garage (biru tua) =====
    nx.draw_networkx_nodes(
        graph, pos,
        nodelist=TPA_nodes,
        node_size=220,
        node_color="black",
        label="TPA / Garage"
    )

    # ===== Warna Untuk Rute Kendaraan =====
    colors = [
        "lime", "red", "cyan", "magenta", "orange", "purple", "blue",
        "green", "brown", "pink", "olive", "gold"
    ]

    # Gambar semua rute per kendaraan
    for i, route in enumerate(best_routes):
        if len(route) < 2:
            continue
        
        edges = list(zip(route[:-1], route[1:]))
        color = colors[i % len(colors)]

        # Edge route per truk
        nx.draw_networkx_edges(
            graph, pos,
            edgelist=edges,
            width=3,
            edge_color=color,
            label=f"Truck {i+1}"
        )

        # Node route per truk
        nx.draw_networkx_nodes(
            graph, pos,
            nodelist=route,
            node_size=40,
            node_color=color
        )

    plt.title("Simulated Annealing VRP Final Routes", fontsize=14)
    plt.axis("equal")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.show()
