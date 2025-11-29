"""
Integration Helpers
Helper functions untuk integrasi AI System dengan existing viewer structure
"""


def initialize_node_data(shared, graph, tps_nodes, tpa_nodes, garage_nodes):
    """
    Initialize node_type data structure untuk semua nodes.
    Sesuai dengan struktur yang diharapkan viewer.
    
    Args:
        shared: Shared state object
        graph: NetworkX graph
        tps_nodes: Set of TPS node IDs
        tpa_nodes: Set of TPA node IDs
        garage_nodes: Set of Garage node IDs
    """
    for node in graph.nodes():
        if node not in shared.node_type:
            is_tps = node in tps_nodes
            is_tpa = node in tpa_nodes
            is_garage = node in garage_nodes
            
            shared.node_type[node] = {
                "tps": is_tps,
                "tpa": is_tpa,
                "garage": is_garage,
                "tps_data": {
                    "nama": f"TPS-{node}" if is_tps else "",
                    "sampah_kg": 50000 if is_tps else 0,  # Initial: 50 ton
                    "sampah_hari_ini": 0,
                    "dilayanin": False
                } if is_tps else {},
                "tpa_data": {
                    "nama": f"TPA-{node}" if is_tpa else "TPA",
                    "total_sampah": 0
                } if is_tpa else {},
                "garage_data": {
                    "nama": f"Garage-{node}" if is_garage else "Garage",
                    "total_armada": 0,
                    "armada_bertugas": 0,
                    "armada_standby": 0
                } if is_garage else {}
            }


def initialize_edge_data(shared, graph):
    """
    Initialize edge_type data structure untuk semua edges.
    
    Args:
        shared: Shared state object
        graph: NetworkX graph
    """
    for u, v in graph.edges():
        edge_id = f"{u}-{v}"
        if edge_id not in shared.edge_type:
            shared.edge_type[edge_id] = {
                "delay": 0,
                "slowdown": 0
            }


def sync_tps_waste(shared, tps_node, waste_ton):
    """
    Sync waste amount dari simulasi ke shared.node_type.
    
    Args:
        shared: Shared state object
        tps_node: TPS node ID
        waste_ton: Waste amount in tons
    """
    if tps_node in shared.node_type:
        shared.node_type[tps_node]["tps_data"]["sampah_kg"] = int(waste_ton * 1000)


def get_tps_waste(shared, tps_node):
    """
    Get waste amount dari shared.node_type.
    
    Args:
        shared: Shared state object
        tps_node: TPS node ID
    
    Returns:
        float: Waste amount in tons
    """
    if tps_node in shared.node_type:
        tps_data = shared.node_type[tps_node].get("tps_data", {})
        return tps_data.get("sampah_kg", 0) / 1000.0
    return 0.0


def sync_traffic(shared, edge, congestion_factor):
    """
    Sync traffic congestion dari simulasi ke shared.edge_type.
    
    HANYA dipanggil saat:
    - Initial setup (jika perlu)
    - TIDAK dipanggil saat stuck event (biarkan user manual)
    
    Args:
        shared: Shared state object
        edge: Tuple (u, v) representing edge
        congestion_factor: Float 0.0-1.0 (1.0 = clear, 0.0 = fully congested)
    """
    edge_id = f"{edge[0]}-{edge[1]}"
    
    if edge_id not in shared.edge_type:
        shared.edge_type[edge_id] = {"delay": 0, "slowdown": 0}
    
    # Convert factor to delay/slowdown
    if congestion_factor < 0.3:
        # Severe congestion
        shared.edge_type[edge_id]["delay"] = int((1.0 - congestion_factor) * 100)
        shared.edge_type[edge_id]["slowdown"] = 0
    elif congestion_factor < 0.7:
        # Medium congestion
        shared.edge_type[edge_id]["delay"] = 0
        shared.edge_type[edge_id]["slowdown"] = int((1.0 - congestion_factor) * 50)
    else:
        # Clear
        shared.edge_type[edge_id]["delay"] = 0
        shared.edge_type[edge_id]["slowdown"] = 0


def get_traffic_factor(shared, edge):
    """
    Get traffic factor dari shared.edge_type.
    
    Args:
        shared: Shared state object
        edge: Tuple (u, v) representing edge
    
    Returns:
        float: Traffic factor 0.0-1.0 (1.0 = clear)
    """
    edge_id = f"{edge[0]}-{edge[1]}"
    edge_data = shared.edge_type.get(edge_id, {})
    
    delay = edge_data.get("delay", 0)
    slowdown = edge_data.get("slowdown", 0)
    
    # Convert delay/slowdown to factor
    if delay > 0:
        return max(0.1, 1.0 - (delay / 100.0))
    elif slowdown > 0:
        return max(0.3, 1.0 - (slowdown / 100.0))
    return 1.0


def update_garage_stats(shared, garage_node, vehicles):
    """
    Update garage statistics.
    
    Args:
        shared: Shared state object
        garage_node: Garage node ID
        vehicles: List of Vehicle objects
    """
    if garage_node not in shared.node_type:
        return
    
    armada_standby = sum(
        1 for v in vehicles 
        if v.current == garage_node and v.state in ["Idle", "Standby"]
    )
    
    armada_bertugas = sum(
        1 for v in vehicles 
        if v.state in ["Moving", "Loading", "Unloading"]
    )
    
    shared.node_type[garage_node]["garage_data"]["total_armada"] = len(vehicles)
    shared.node_type[garage_node]["garage_data"]["armada_standby"] = armada_standby
    shared.node_type[garage_node]["garage_data"]["armada_bertugas"] = armada_bertugas


def mark_tps_serviced(shared, tps_node, is_serviced):
    """
    Mark TPS as being serviced or not.
    
    Args:
        shared: Shared state object
        tps_node: TPS node ID
        is_serviced: Boolean
    """
    if tps_node in shared.node_type:
        shared.node_type[tps_node]["tps_data"]["dilayanin"] = is_serviced


def add_tpa_waste(shared, tpa_node, amount_ton):
    """
    Add waste to TPA total.
    
    Args:
        shared: Shared state object
        tpa_node: TPA node ID
        amount_ton: Amount in tons
    """
    if tpa_node in shared.node_type:
        current = shared.node_type[tpa_node]["tpa_data"].get("total_sampah", 0)
        shared.node_type[tpa_node]["tpa_data"]["total_sampah"] = current + int(amount_ton * 1000)


def add_tps_daily_waste(shared, tps_node, amount_ton):
    """
    Add to TPS daily waste counter.
    
    Args:
        shared: Shared state object
        tps_node: TPS node ID
        amount_ton: Amount in tons
    """
    if tps_node in shared.node_type:
        current = shared.node_type[tps_node]["tps_data"].get("sampah_hari_ini", 0)
        shared.node_type[tps_node]["tps_data"]["sampah_hari_ini"] = current + int(amount_ton * 1000)


def reset_daily_stats(shared, tps_nodes):
    """
    Reset daily statistics (call at end of day).
    
    Args:
        shared: Shared state object
        tps_nodes: List of TPS node IDs
    """
    for tps in tps_nodes:
        if tps in shared.node_type:
            shared.node_type[tps]["tps_data"]["sampah_hari_ini"] = 0