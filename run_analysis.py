import simpy
import random
import config
import main
import numpy as np
import scipy.stats as st
from contextlib import contextmanager

# --- Configuration Definitions ---

def get_no_surge_config():
    return {
        "ARRIVAL_BASE_RATE": 50.0,
        "ARRIVAL_PEAK_B_AMP": 0.0,
        "ARRIVAL_PEAK_L_AMP": 0.0,
        "description": "Steady State (Baseline)"
    }

def get_medium_surge_config():
    return {
        "ARRIVAL_BASE_RATE": 50.0,
        "ARRIVAL_PEAK_B_AMP": 100.0,
        "ARRIVAL_PEAK_L_AMP": 100.0,
        "description": "Normal Operations (Medium Surge)"
    }

def get_high_surge_config():
    return {
        "ARRIVAL_BASE_RATE": 50.0,
        "ARRIVAL_PEAK_B_AMP": 250.0,
        "ARRIVAL_PEAK_L_AMP": 250.0,
        "description": "Stress Test (High Surge)"
    }

def get_less_staffing_config():
    return {
        "NUM_CASHIERS": 1,
        "DRIVE_THRU_NUM_ORDERING_STATIONS": 1,
        "STATION_EMPLOYEES": {
            "hot_foods": 3,
            "drinks": 1,
            "coffee": 1,
            "espresso": 1
        },
        "description": "Less Staffing"
    }

def get_regular_staffing_config():
    return {
        "NUM_CASHIERS": 2,
        "DRIVE_THRU_NUM_ORDERING_STATIONS": 2,
        "STATION_EMPLOYEES": {
            "hot_foods": 4,
            "drinks": 2,
            "coffee": 1,
            "espresso": 2
        },
        "description": "Regular Staffing"
    }

def get_more_staffing_config():
    return {
        "NUM_CASHIERS": 3,
        "DRIVE_THRU_NUM_ORDERING_STATIONS": 2,
        "STATION_EMPLOYEES": {
            "hot_foods": 5,
            "drinks": 3,
            "coffee": 2,
            "espresso": 3
        },
        "description": "More Staffing"
    }

# --- Analysis Logic ---

def run_simulation_with_override(config_overrides, seed):
    # Apply overrides
    original_values = {}
    for key, value in config_overrides.items():
        if hasattr(config, key):
            original_values[key] = getattr(config, key)
            setattr(config, key, value)

    setattr(config, "RANDOM_SEED", seed)

    # Need to override this for safety, although main.run_simulation sets it

    # Run simulation
    # We need to capture the stats object. main.run_simulation creates it internally.
    # We will modify main.run_simulation to return stats or we can copy the logic here.
    # Copying logic is safer to avoid changing main.py too much if not needed,
    # but reusing main.py ensures consistency.
    # Let's inspect main.py again. It prints report but doesn't return stats.
    # We should probably modify main.py to return stats.
    # For now, I will replicate the setup logic here to ensure I get the stats object.

    env = simpy.Environment()
    random.seed(config.RANDOM_SEED)

    menu = main.load_menu()
    stats = main.StatsCollector()
    kitchen = main.Kitchen(env, config.KITCHEN_STATIONS)
    station_logic = main.StationLogic(env, kitchen, stats, config, menu)

    stats.num_cashiers = config.NUM_CASHIERS
    stats.num_dt_ordering_stations = config.DRIVE_THRU_NUM_ORDERING_STATIONS

    arrival_gen = main.NHPPArrivalGenerator(env, config)

    cust_id_counter = [0]
    def on_arrival():
        cust_id_counter[0] += 1
        main.customer_arrival(env, stats, station_logic, cust_id_counter[0])

    env.process(arrival_gen.generate_arrivals(on_arrival))

    sim_duration_minutes = config.SIM_DURATION_HOURS * 60
    env.run(until=sim_duration_minutes)
    stats.total_sim_time = env.now

    # Restore config
    for key, value in original_values.items():
        setattr(config, key, value)

    return stats.get_stats_dict()

def compute_ci(data, confidence=0.95):
    n = len(data)
    if n < 2: return np.mean(data), 0.0

    m, se = np.mean(data), st.sem(data)
    h = se * st.t.ppf((1 + confidence) / 2., n-1)
    return m, h

def run_experiments(scenarios, num_replications=5):
    results = {}

    for sc_name, sc_config in scenarios.items():
        print(f"Running Scenario: {sc_name} ...")

        aggregated_stats = {}

        for i in range(num_replications):
            seed = 42 + i * 123 # Deterministic different seeds
            stats = run_simulation_with_override(sc_config, seed)

            for key, val in stats.items():
                if key not in aggregated_stats:
                    aggregated_stats[key] = []
                aggregated_stats[key].append(val)

        # Compute Statistics
        scenario_results = {}
        for key, values in aggregated_stats.items():
            mean, margin = compute_ci(values)
            scenario_results[key] = {
                "mean": mean,
                "ci_margin": margin,
                "ci_lower": mean - margin,
                "ci_upper": mean + margin,
                "raw_values": values
            }
        results[sc_name] = scenario_results

    return results

def print_results(results, title):
    print(f"\n{'='*80}")
    print(f"RESULTS: {title}")
    print(f"{'='*80}")

    for sc_name, metrics in results.items():
        print(f"\nScenario: {sc_name}")
        print(f"{'-'*40}")
        # Select key metrics to display
        keys = ["net_profit", "total_throughput",
                "avg_dt_wait", "p90_dt_wait",
                "avg_cashier_wait", "p95_cashier_wait",
                "mobile_sla_violation_rate",
                "dt_balk_rate", "mobile_balk_rate"]

        for k in keys:
            if k in metrics:
                m = metrics[k]
                print(f"{k:<30}: {m['mean']:10.2f} +/- {m['ci_margin']:6.2f} (95% CI: [{m['ci_lower']:10.2f}, {m['ci_upper']:10.2f}])")

if __name__ == "__main__":

    # --- Part 1: Arrival x Staffing Combinations ---
    print("\nStarting Part 1: Arrival x Staffing Combinations (9 Combinations)")

    arrival_scenarios = [
        ("NoSurge", get_no_surge_config()),
        ("MediumSurge", get_medium_surge_config()),
        ("HighSurge", get_high_surge_config())
    ]

    staffing_scenarios = [
        ("LessStaff", get_less_staffing_config()),
        ("RegularStaff", get_regular_staffing_config()),
        ("MoreStaff", get_more_staffing_config())
    ]

    scenarios_part1 = {}
    for arr_name, arr_conf in arrival_scenarios:
        for stf_name, stf_conf in staffing_scenarios:
            name = f"{arr_name} x {stf_name}"
            # Merge configs
            merged = arr_conf.copy()
            merged.update(stf_conf)
            # Remove description for cleaner merging if needed, but it's fine
            scenarios_part1[name] = merged

    results_part1 = run_experiments(scenarios_part1, num_replications=5)
    print_results(results_part1, "Arrival Rate x Staffing Level Analysis")


    # --- Part 2: Priority Queue Analysis ---
    print("\nStarting Part 2: Priority Queue Analysis")

    regular_staff = get_regular_staffing_config()

    priority_scenarios = {}

    # For each arrival scenario
    for arr_name, arr_conf in arrival_scenarios:
        # With Priority (Default)
        name_with = f"{arr_name} - Priority ON"
        conf_with = arr_conf.copy()
        conf_with.update(regular_staff)
        conf_with["ENABLE_PRIORITY"] = True
        priority_scenarios[name_with] = conf_with

        # Without Priority
        name_without = f"{arr_name} - Priority OFF"
        conf_without = arr_conf.copy()
        conf_without.update(regular_staff)
        conf_without["ENABLE_PRIORITY"] = False
        priority_scenarios[name_without] = conf_without

    results_part2 = run_experiments(priority_scenarios, num_replications=5)
    print_results(results_part2, "Priority Queue Impact Analysis")

    # Export all data to json for records
    import json
    class NpEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return super(NpEncoder, self).default(obj)

    with open("analysis_results.json", "w") as f:
        json.dump({"part1": results_part1, "part2": results_part2}, f, cls=NpEncoder, indent=2)
    print("\nFull results saved to 'analysis_results.json'")
