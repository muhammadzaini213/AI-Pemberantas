import osmnx as ox

filename = "./data/roadData.graphml"
place_name = "Balikpapan Kota, Balikpapan, Kalimantan Timur, Indonesia"

G = ox.graph_from_place(
    place_name,
    network_type="drive",
    simplify=False,
    retain_all=False
)

ox.save_graphml(G, filename)

print("Graph saved as:", filename)
print("Nodes:", len(G.nodes()))
print("Edges:", len(G.edges()))
