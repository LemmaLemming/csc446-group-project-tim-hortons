# tim_hortons/main.py
import simpy
import random
import json
import config
from models import MenuItem, Customer
from kitchen import Kitchen
from arrival import NHPPArrivalGenerator
from stations import StationLogic
from reporting import StatsCollector

def load_menu(filepath="menu.json"):
    with open(filepath, 'r') as f:
        data = json.load(f)
    menu = []
    for item in data:
        # Check for sizes/price structure
        sizes = item.get("sizes")
        price = item.get("price")
        m = MenuItem(
            id=item["id"],
            name=item["name"],
            category=item["category"],
            station=item.get("station", "hot_foods"),
            frequency=item.get("frequency", 10),
            price=price,
            sizes=sizes
        )
        menu.append(m)
    return menu

def customer_arrival(env, stats, station_logic, arrival_id):
    # Determine channel
    r = random.random()
    if r < config.PROB_CASHIER:
        channel = "cashier"
    elif r < config.PROB_CASHIER + config.PROB_MOBILE:
        channel = "mobile"
    else:
        channel = "drive_thru"
        
    cust = Customer(id=arrival_id, arrival_time=env.now, channel=channel, order=None)
    
    if channel == "cashier":
        env.process(station_logic.process_cashier_customer(cust))
    elif channel == "mobile":
        env.process(station_logic.process_mobile_customer(cust))
    else:
        env.process(station_logic.process_drive_thru_customer(cust))

def run_simulation():
    # Setup
    random.seed(config.RANDOM_SEED)
    env = simpy.Environment()
    
    # Components
    menu = load_menu()
    stats = StatsCollector()
    kitchen = Kitchen(env, config.KITCHEN_STATIONS)
    station_logic = StationLogic(env, kitchen, stats, config, menu)
    
    # Set number of cashiers tracking
    stats.num_cashiers = config.NUM_CASHIERS
    stats.num_dt_ordering_stations = config.DRIVE_THRU_NUM_ORDERING_STATIONS
    
    # Generator
    arrival_gen = NHPPArrivalGenerator(env, config)
    
    # Callback for arrival
    cust_id_counter = [0]
    def on_arrival():
        cust_id_counter[0] += 1
        customer_arrival(env, stats, station_logic, cust_id_counter[0])
        
    # Start Generator Process
    env.process(arrival_gen.generate_arrivals(on_arrival))
    
    # Run
    sim_duration_minutes = config.SIM_DURATION_HOURS * 60
    env.run(until=sim_duration_minutes)
    stats.total_sim_time = env.now
    
    # Report
    stats.print_report(config)

if __name__ == "__main__":
    run_simulation()
