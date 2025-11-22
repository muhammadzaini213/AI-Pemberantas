import osmnx as ox
from shapely.geometry import Point
from geopy.distance import geodesic

lat_manggar = -1.2081484
lon_manggar = 116.9516328

# Load graph
G = ox.load_graphml("data/balikpapan_drive.graphml")

G_proj = ox.project_graph(G)

nearest_node = ox.distance.nearest_nodes(G_proj, X=lon_manggar, Y=lat_manggar)

node_data = G.nodes[nearest_node]
node_lat = node_data.get("y")  
node_lon = node_data.get("x")  

jarak = geodesic((lat_manggar, lon_manggar), (node_lat, node_lon)).meters

print("Node terdekat Manggar:", nearest_node)
print("Koordinat node terdekat:", node_lat, node_lon)
print(f"Jarak ke node terdekat: {jarak:.2f} meter")
