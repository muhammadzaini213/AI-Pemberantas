import os
import osmnx as ox
import threading
from window.window_program_summary import ProgramSummaryWindow
from window.window_node_state import NodeStateWindow
from window.window_edges_state import EdgeStateWindow
from window.window_tps_state import TPSStateWindow
from window.window_tpa_state import TPAStateWindow
from window.window_garage_state import GarageStateWindow
from window.window_car_state import CarStateWindow
from .environment import *
from .simulation import run_simulation
from .utils.shared import SharedState

def start_simulation_thread(GRAPH, shared):
    t = threading.Thread(target=lambda: run_simulation(GRAPH, shared), daemon=True)
    t.start()

def main():

    if not os.path.exists(GRAPH_FILE):
        print("Graph file tidak ditemukan:", GRAPH_FILE)
        return

    print("\n" + "="*50)
    print("LOADING GRAPH")
    print("="*50)
    GRAPH = ox.load_graphml(GRAPH_FILE)
    print(f"✓ Graph loaded: {GRAPH.number_of_nodes()} nodes, {GRAPH.number_of_edges()} edges")
    print("="*50 + "\n")

    shared = SharedState()

    # ============================================================
    #  START SIMULATION (akan init node_types dan auto-load data)
    # ============================================================
    start_simulation_thread(GRAPH, shared)

    # ============================================================
    #  SETUP WINDOWS
    # ============================================================
    program_summary = ProgramSummaryWindow()
    program_summary.attach_state(shared)
    program_summary.set_fps(MAX_FPS)

    node_state_window = NodeStateWindow(master=program_summary.root)
    node_state_window.attach_shared(shared)
    
    edge_state_window = EdgeStateWindow(master=program_summary.root)
    edge_state_window.attach_shared(shared)
    
    tps_state_window = TPSStateWindow(master=program_summary.root)
    tps_state_window.attach_shared(shared)

    tpa_state_window = TPAStateWindow(master=program_summary.root)
    tpa_state_window.attach_shared(shared)

    garage_state_window = GarageStateWindow(master=program_summary.root)
    garage_state_window.attach_shared(shared)

    car_state_window = CarStateWindow(master=program_summary.root)
    car_state_window.attach_shared(shared)

    program_summary.run()

if __name__ == "__main__":
    main()