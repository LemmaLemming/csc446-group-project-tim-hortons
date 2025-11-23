# simulation.py
# --- All simulation classes and logic live here ---

import heapq
import random
import math

# --- IMPORT YOUR CONFIGS ---
from config import ARRIVAL_CONFIG, SERVICE_RATES, ROUTING_PROBS, SIM_PARAMS, ORDER_TYPE_PROBS

# --------------------------------------------------
# Event types
# --------------------------------------------------
ARRIVAL = "arrival"
CHANNEL_DEPARTURE = "channel_departure"
KITCHEN_DEPARTURE = "kitchen_departure"

# --------------------------------------------------
# Customer Object (Encapsulates customer state)
# --------------------------------------------------
class Customer:
    """Encapsulates the state of a single customer."""
    def __init__(self, cid, channel_name):
        self.id = cid
        self.channel_name = channel_name # drive_thru | mobile_order | cashier
        self.stage = "ordering"          # ordering | pickup
        self.item_type = OrderTypeGenerator(channel_name).sample() # food | drink | espresso
        # TODO: customers should be able to order more than one item

# --------------------------------------------------
# Arrival Generator (Encapsulates arrival logic)
# --------------------------------------------------
class ArrivalGenerator:
    """
    (Abstraction)
    Encapsulates the logic for a Non-Homogeneous Poisson Process
    using the thinning method.
    """
    def __init__(self, rate_func, rate_max):
        self.rate_func = rate_func
        self.rate_max = rate_max

    def sample_next(self, t_now, sim_time_end):
        """Returns the next arrival time > t_now, or None."""
        t = t_now
        while True:
            # Propose candidate from the "envelope" process
            t += random.expovariate(self.rate_max)
            if t > sim_time_end:
                return None
            
            # Accept with probability P(t) = λ(t) / λ_max
            if random.random() < self.rate_func(t) / self.rate_max:
                return t

# --------------------------------------------------
# Order Type Generator
# --------------------------------------------------
class OrderTypeGenerator:
    def __init__(self, channel_name):
        self.channel = channel_name
        self.probs = ORDER_TYPE_PROBS[channel_name]

        self.items = list(self.probs.keys())
        self.weights = list(self.probs.values())

    def sample(self):
        """Return one sampled order type."""
        return random.choices(self.items, weights=self.weights, k=1)[0]

# --------------------------------------------------
# Service Station (Encapsulates queue state)
# --------------------------------------------------
class ServiceStation:
    """
    (Encapsulation & Inheritance - Base Class)
    Holds the state for a single-server queue.
    """
    def __init__(self, name, mu):
        self.name = name
        self.mu = mu               # Service rate
        self.server_busy = False
        self.queue = []            # Holds Customer objects
        self.num_waited = 0
        self.num_departures = 0

class Channel(ServiceStation):
    """
    (Inheritance - Child Class)
    A ServiceStation that also has an ArrivalGenerator
    and tracks final system departures.
    """
    def __init__(self, name, mu, arrival_generator):
        super().__init__(name, mu)
        self.arrival_gen = arrival_generator
        self.num_system_departures = 0 # Final exits

class KitchenStation(ServiceStation):
    """
    (Inheritance - Child Class)
    A simple ServiceStation for the kitchen.
    """
    def __init__(self, name, mu):
        super().__init__(name, mu)
        # Inherits all state from ServiceStation

# --------------------------------------------------
# Simulation Engine (Encapsulates global state & logic)
# --------------------------------------------------
class Simulation:
    """
    The main simulation "world."
    It is INITIALIZED with config dictionaries, making it
    independent of the actual parameter values.
    """
    def __init__(self, arrival_config, service_rates, routing_probs, sim_params):
        
        # --- Store params from config ---
        self.clock = 0.0
        self.event_list = []
        self.event_counter = 0
        self.next_customer_id = 0
        
        self.drink_prob = routing_probs["DRINK_PROB"]
        self.sim_time_end = sim_params["SIM_TIME_END"]
        self.max_departures = sim_params["MAX_DEPARTURES"]
        self.random_seed = sim_params["RANDOM_SEED"]
        
        # --- Create Arrival Generators (Abstraction) ---
        self.arrival_gens = {}
        for name, (rate_func, rate_max) in arrival_config.items():
            # This is the line that caused the error, now fixed
            self.arrival_gens[name] = ArrivalGenerator(rate_func, rate_max)
        
        # --- Create Service Stations (Encapsulation) ---
        self.channels = {
            "drive_thru": Channel("drive_thru", 
                                  service_rates["drive_thru"], 
                                  self.arrival_gens["drive_thru"]),
            "mobile_order": Channel("mobile_order", 
                                    service_rates["mobile_order"], 
                                    self.arrival_gens["mobile_order"]),
            "cashier": Channel("cashier", 
                               service_rates["cashier"], 
                               self.arrival_gens["cashier"]),
        }
        self.kitchen = {
            "drinks": KitchenStation("drinks", service_rates["drinks"]),
            "food": KitchenStation("food", service_rates["food"]),
        }

    def schedule_event(self, time, event_type, data):
        """Internal method to push a new event onto the FEL."""
        heapq.heappush(self.event_list, (time, self.event_counter, event_type, data))
        self.event_counter += 1

    def total_finished_customers(self):
        """Helper to check the simulation end condition."""
        return sum(ch.num_system_departures for ch in self.channels.values())

    # --- Event Handlers (Methods of Simulation) ---

    def handle_arrival(self, event_time, channel_name):
        """Arrival to a front-end queue (ordering stage)."""
        self.clock = event_time
        ch = self.channels[channel_name]

        # Schedule next arrival for this channel
        next_t = ch.arrival_gen.sample_next(self.clock, self.sim_time_end)
        if next_t is not None:
            self.schedule_event(next_t, ARRIVAL, {"channel": channel_name})

        # Create new customer
        cust = Customer(self.next_customer_id, channel_name)
        self.next_customer_id += 1

        # Join queue or start service
        if (not ch.server_busy) and (len(ch.queue) == 0):
            self.start_channel_service(channel_name, cust)
        else:
            ch.queue.append(cust)
            ch.num_waited += 1

    def handle_channel_departure(self, event_time, channel_name, customer):
        """Finished service at a front-end channel."""
        self.clock = event_time
        ch = self.channels[channel_name]
        ch.num_departures += 1 # Internal channel departure

        # Decide what happens to THIS customer
        if customer.stage == "ordering":
            # --- ROUTING LOGIC (TUNABLE) ---
            station_name = "drinks" if random.random() < self.drink_prob else "food"
            station = self.kitchen[station_name]

            if (not station.server_busy) and (len(station.queue) == 0):
                self.start_kitchen_service(station_name, customer)
            else:
                station.queue.append(customer)
        else:
            # Pickup complete -> system departure
            ch.num_system_departures += 1

        # See if someone else is waiting at THIS channel
        if ch.queue:
            next_cust = ch.queue.pop(0)
            self.start_channel_service(channel_name, next_cust)
        else:
            ch.server_busy = False

    def handle_kitchen_departure(self, event_time, station_name, customer):
        """Finished at drinks/food station."""
        self.clock = event_time
        st = self.kitchen[station_name]
        st.num_departures += 1

        # Free or continue kitchen server
        if st.queue:
            next_cust = st.queue.pop(0)
            self.start_kitchen_service(station_name, next_cust)
        else:
            st.server_busy = False

        # Send order back to original channel for pickup
        channel_name = customer.channel_name
        ch = self.channels[channel_name]
        customer.stage = "pickup"

        if (not ch.server_busy) and (len(ch.queue) == 0):
            self.start_channel_service(channel_name, customer)
        else:
            ch.queue.append(customer)
            ch.num_waited += 1

    # --- Service Starters (Methods of Simulation) ---

    def start_channel_service(self, channel_name, customer):
        """Start service (either ordering or pickup) at a front-end channel."""
        ch = self.channels[channel_name]
        ch.server_busy = True
        
        service_time = random.expovariate(ch.mu)
        depart_time = self.clock + service_time

        self.schedule_event(
            depart_time,
            CHANNEL_DEPARTURE,
            {"channel": channel_name, "customer": customer},
        )

    def start_kitchen_service(self, station_name, customer):
        """Start service at drinks or food station."""
        st = self.kitchen[station_name]
        st.server_busy = True
        
        service_time = random.expovariate(st.mu)
        depart_time = self.clock + service_time

        self.schedule_event(
            depart_time,
            KITCHEN_DEPARTURE,
            {"station": station_name, "customer": customer},
        )

    # --- Main Simulation Loop ---

    def run(self):
        """Run the simulation from start to end."""
        random.seed(self.random_seed) # Use the configured seed

        # Initial arrivals for each channel
        for channel_name in self.channels.keys():
            first_t = self.channels[channel_name].arrival_gen.sample_next(0.0, self.sim_time_end)
            if first_t is not None:
                self.schedule_event(first_t, ARRIVAL, {"channel": channel_name})

        # Process events
        while (self.event_list
               and self.clock < self.sim_time_end
               and self.total_finished_customers() < self.max_departures):

            event_time, _, event_type, data = heapq.heappop(self.event_list)
            
            # (Ensure we don't process events past the end time,
            #  even if they were scheduled before)
            if event_time > self.sim_time_end:
                break
            
            self.clock = event_time # Advance clock

            if event_type == ARRIVAL:
                self.handle_arrival(event_time, data["channel"])
            elif event_type == CHANNEL_DEPARTURE:
                self.handle_channel_departure(event_time, data["channel"], data["customer"])
            elif event_type == KITCHEN_DEPARTURE:
                self.handle_kitchen_departure(event_time, data["station"], data["customer"])

        self.print_report()

    def print_report(self):
        """Prints a final summary of the simulation."""
        print("=== Simulation finished ===")
        print(f"Final time:           {self.clock:.3f} hours")
        print(f"Total finished custs: {self.total_finished_customers()}")
        print()

        for cname, ch in self.channels.items():
            print(f"--- Channel: {cname} ---")
            print(f"  Num system departures: {ch.num_system_departures}")
            print(f"  Final queue length:    {len(ch.queue)}")
            print(f"  Server busy at end?:   {ch.server_busy}")
            print(f"  Customers who waited:  {ch.num_waited}")
            print()

        for sname, st in self.kitchen.items():
            print(f"--- Kitchen: {sname} ---")
            print(f"  Num departures:        {st.num_departures}")
            print(f"  Final queue length:    {len(st.queue)}")
            print(f"  Server busy at end?:   {st.server_busy}")
            print()

# --------------------------------------------------
# Main execution
# --------------------------------------------------
if __name__ == "__main__":
    # --- This is the "bridge" ---
    # 1. It reads the parameters from the config file.
    # 2. It "injects" them into the Simulation class.
    
    sim = Simulation(
        arrival_config=ARRIVAL_CONFIG,
        service_rates=SERVICE_RATES,
        routing_probs=ROUTING_PROBS,
        sim_params=SIM_PARAMS
    )
    
    # 3. It runs the logic engine.
    sim.run()