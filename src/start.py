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
from .testing.benchmark import run_benchmark
from .utils.shared import SharedState
import json

_simulation_thread = None
_simulation_active = False
_simulation_lock = threading.Lock()

# ============== THREAD ==============
def start_simulation_thread(GRAPH, shared, isSingleRender):
    global _simulation_thread, _simulation_active
    
    with _simulation_lock:
        print(f"[Main] Starting simulation thread...")
        print(f"[Main] Current active flag: {_simulation_active}")
        
        _simulation_active = True
        shared.simulation_running = True
        
        _simulation_thread = threading.Thread(
            target=lambda: run_simulation(GRAPH, shared, isSingleRender), 
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

# ============== BENCHMARK FUNCTIONS ==============
def run_benchmark_mode(GRAPH, shared):
    print("\n" + "="*70)
    print("BENCHMARK MODE")
    print("="*70)
    
    num_days = int(input("Number of days to simulate (default 7): ") or "7")
    speed = int(input("Speed multiplier (default 20): ") or "20")
    verbose = input("Verbose output? (y/n, default n): ").lower() == 'y'
    
    print("\nConfigure edge slowdowns? (y/n, default n): ", end="")
    if input().lower() == 'y':
        print("\nEnter edge configurations (format: edge_id slowdown start_hour end_hour)")
        print("Example: 1234-5678 20 7 9")
        print("Press Enter without input to finish")
        
        while True:
            config_input = input("Edge config: ").strip()
            if not config_input:
                break
            
            try:
                parts = config_input.split()
                if len(parts) == 4:
                    edge_id, slowdown, start_hour, end_hour = parts
                    shared.edge_type[edge_id] = {
                        "slowdown": int(slowdown),
                        "start_hour": int(start_hour),
                        "end_hour": int(end_hour)
                    }
                    print(f"Added: {edge_id} = {slowdown} km/h ({start_hour}:00-{end_hour}:00)")
                else:
                    print("Invalid format")
            except Exception as e:
                print(f"Error: {e}")
    
    shared.sim_day = 1
    shared.sim_hour = 8
    shared.sim_min = 0
    shared.simulation_running = False
    
    print("\nStarting benchmark...")
    metrics = run_benchmark(GRAPH, shared, num_days, speed, verbose)
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"benchmark_results_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(metrics, f, indent=2, default=str)
    
    print(f"\nResults saved to {filename}")
    
    if input("\nView detailed daily metrics? (y/n): ").lower() == 'y':
        for day_data in metrics['daily_metrics']:
            print(f"\n--- Day {day_data['day']} ---")
            print(f"  Garbage: {day_data['garbage_collected']:.2f} kg")
            print(f"  Trips: {day_data['trips']}")
            print(f"  Reschedules: {day_data['reschedules']}")
            print(f"  Slowdowns: {day_data['known_slowdowns']}")
            print(f"  Time: {day_data['simulation_time']:.2f}s")

def run_quick_test(GRAPH, shared):
    print("\n" + "="*70)
    print("QUICK TEST MODE (1 day, 20x speed)")
    print("="*70)
    
    shared.sim_day = 1
    shared.sim_hour = 8
    shared.sim_min = 0
    shared.simulation_running = False
    
    metrics = run_benchmark(GRAPH, shared, num_days=1, speed_multiplier=20, verbose=True)
    
    print("\nQuick test complete!")
    print(f"  Garbage: {metrics['total_garbage_collected']:.2f} kg")
    print(f"  Trips: {metrics['total_trips']}")
    print(f"  Time: {metrics['simulation_time_seconds']:.2f}s")

def show_benchmark_menu(GRAPH, shared):
    while True:
        print("\n" + "="*70)
        print("BENCHMARK MENU")
        print("="*70)
        print("1. Quick Test (1 day, 20x speed)")
        print("2. Single Benchmark Run")
        print("3. Return to Normal Simulation")
        print("="*70)

        choice = input("\nChoice (1-3): ").strip()

        if choice == "1":
            run_quick_test(GRAPH, shared)
        elif choice == "2":
            run_benchmark_mode(GRAPH, shared)
        elif choice == "3":
            break
        else:
            print("Invalid choice")

        if choice in ["1", "2"]:
            input("\nPress Enter to continue...")


def main():
    if not os.path.exists(GRAPH_FILE):
        print("Graph file tidak ditemukan:", GRAPH_FILE)
        return

    print("\n" + "="*50)
    print("LOADING GRAPH")
    print("="*50)
    GRAPH = ox.load_graphml(GRAPH_FILE)
    print(f"Graph loaded: {GRAPH.number_of_nodes()} nodes, {GRAPH.number_of_edges()} edges")
    print("="*50 + "\n")

    shared = SharedState()
    shared.simulation_running = False

    # ============== MODE SELECTION ==============
    print("="*70)
    print("SELECT MODE")
    print("="*70)
    print("1. Normal Simulation")
    print("2. Simulation Editor")
    print("3. Benchmark Mode (no rendering)")
    mode = input("\nChoice (1-3, default 1): ").strip() or "1"
    
    if mode == "1":
        start_simulation_thread(GRAPH, shared, True)
    elif mode == "2":
        start_simulation_thread(GRAPH, shared, False)
    elif mode == "3":
        show_benchmark_menu(GRAPH, shared)
        return

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