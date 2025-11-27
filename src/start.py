import os
import osmnx as ox
from window.window_program_summary import ProgramSummaryWindow
from .environment import *
import threading
from .simulation import run_simulation
from .shared import SharedState

def start_simulation_thread(GRAPH, shared):
    t = threading.Thread(target=lambda: run_simulation(GRAPH, shared), daemon=True)
    t.start()

def main():

    if not os.path.exists(GRAPH_FILE):
        print("Graph file tidak ditemukan:", GRAPH_FILE)
        return

    GRAPH = ox.load_graphml(GRAPH_FILE)

    # Buat shared state
    shared = SharedState()

    # Jalankan simulasi di thread
    start_simulation_thread(GRAPH, shared)

    # GUI
    program_summary = ProgramSummaryWindow()
    program_summary.attach_state(shared)
    program_summary.set_fps(MAX_FPS)
    program_summary.set_stat("node", GRAPH.number_of_nodes())
    program_summary.set_stat("edge", GRAPH.number_of_edges())
    program_summary.run()

if __name__ == "__main__":
    main()
