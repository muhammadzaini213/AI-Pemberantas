import os
import osmnx as ox
import threading
import pygame
import time
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

_simulation_thread = None
_simulation_active = False
_simulation_lock = threading.Lock()

# ============== THREAD ==============
def start_simulation_thread(GRAPH, shared):
    global _simulation_thread, _simulation_active
    
    with _simulation_lock:
        print(f"[Main] Starting simulation thread...")
        print(f"[Main] Current active flag: {_simulation_active}")
        
        _simulation_active = True
        shared.simulation_running = True
        
        _simulation_thread = threading.Thread(
            target=lambda: run_simulation(GRAPH, shared), 
            daemon=True
        )
        _simulation_thread.start()
        print(f"[Main] Thread started with ID: {_simulation_thread.ident}")

def stop_simulation_thread():
    global _simulation_active, _simulation_thread
    
    with _simulation_lock:
        print(f"[Main] Stopping simulation thread...")
        
        _simulation_active = False
        
        if _simulation_thread and _simulation_thread.is_alive():
            print(f"[Main] Waiting for thread {_simulation_thread.ident} to stop...")
            _simulation_thread.join(timeout=2.0)
            
            if _simulation_thread.is_alive():
                print(f"[WARNING] Thread {_simulation_thread.ident} still alive after timeout!")
            else:
                print(f"[Main] Thread stopped successfully")
        
        try:
            pygame.quit()
        except:
            pass

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
    shared.simulation_running = False

    start_simulation_thread(GRAPH, shared)


    # ============== SETUP ==============
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

    # ============== REFRESH ==============
    def on_refresh_simulation():
        print("\n" + "="*60)
        print("REFRESH SIMULATION")
        print("="*60)
        
        print("[1/5] Stopping old simulation...")
        print(f"      Vehicles before stop: {len(shared.vehicles)}")
        stop_simulation_thread()
        shared.simulation_running = False
        time.sleep(1.5) 
        
        print("[2/5] Resetting vehicles...")
        print(f"      Vehicles before reset: {len(shared.vehicles)}")
        shared.reset_vehicles()
        print(f"      Vehicles after reset: {len(shared.vehicles)}")
        
        if len(shared.vehicles) != 0:
            print(f"[ERROR] Vehicles not cleared! Still have {len(shared.vehicles)} vehicles!")
        
        print("[3/5] Reloading graph...")
        GRAPH = ox.load_graphml(GRAPH_FILE)
        print(f"      Graph: {GRAPH.number_of_nodes()} nodes")
        
        print("[4/5] Clearing pygame...")
        try:
            pygame.quit()
            time.sleep(0.5)
        except Exception as e:
            print(f"      pygame.quit() error: {e}")
        
        print("[5/5] Starting new simulation...")
        start_simulation_thread(GRAPH, shared)
        
        time.sleep(1.0)
        print(f"\n[VERIFY] Vehicles after refresh: {len(shared.vehicles)}")
        print("="*60 + "\n")

    program_summary.set_refresh_callback(on_refresh_simulation)
    program_summary.run()

if __name__ == "__main__":
    main()