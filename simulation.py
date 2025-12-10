# simulation.py
# Discrete-event simulation of restaurant queueing network

import heapq
import random

from config import (
    ARRIVAL_RATE_FUNC,
    ARRIVAL_RATE_MAX,
    ENTRY_PROBS,
    FINAL_ROUTING_PROBS,
    FINAL_CAPS,
    FINAL_BALK_IF_FULL,
    PREP_PROBS,
    STATION_CAPACITY,
    COFFEE_USES_PER_BREW,
    COFFEE_REBREW_MEAN_HRS,
    COFFEE_REBREW_STD_HRS,
    SERVICE_RATES,
    SERVER_CAPACITY,
    SIM_PARAMS,
    ORDER_SIZE_PROBS,
    ITEM_TYPE_PROBS,
    REVENUE_PER_ORDER,
    STAFF_COST_PER_HOUR,
)
from customers.customer import Customer
from arrivals.arrival_generator import ArrivalGenerator
from stations.channel import Channel
from stations.kitchen_station import KitchenStation
from stations.kitchen_network import KitchenNetwork
from stations.service_station import ServiceStation

# Event types
ARRIVAL = "arrival"
CHANNEL_DEPARTURE = "channel_departure"
KITCHEN_GATE_DEPARTURE = "kitchen_gate_departure"
ITEM_DEPARTURE = "item_departure"
PACK_DEPARTURE = "pack_departure"
FINAL_DEPARTURE = "final_departure"
COFFEE_BREW_COMPLETE = "coffee_brew_complete"


class Simulation:
    def __init__(self):
        self.clock = 0.0
        self.event_list = []
        self.event_counter = 0
        self.next_customer_id = 0
        self.random_seed = SIM_PARAMS["RANDOM_SEED"]
        self.sim_time_end = SIM_PARAMS["SIM_TIME_END"]
        self.max_departures = SIM_PARAMS["MAX_DEPARTURES"]

        # Metrics
        self.time_in_system = []
        self.time_by_final = {
            "seated": {"sum": 0.0, "count": 0},
            "pickup": {"sum": 0.0, "count": 0},
            "drive_thru": {"sum": 0.0, "count": 0},
        }
        self.path_counts = {
            "entry": {"cashier": 0, "app": 0, "order_station": 0},
            "final": {"seated": 0, "pickup": 0, "drive_thru": 0},
            "lost": 0,
        }

        # Single arrival generator
        self.arrival_gen = ArrivalGenerator(ARRIVAL_RATE_FUNC, ARRIVAL_RATE_MAX)

        # Entry/service nodes
        self.channels = {
            "cashier": Channel("cashier", SERVICE_RATES["cashier"], self.arrival_gen, capacity=SERVER_CAPACITY.get("cashier", 1)),
            "app": Channel("app", SERVICE_RATES["app"], self.arrival_gen, capacity=SERVER_CAPACITY.get("app", 1)),
            "order_station": Channel("order_station", SERVICE_RATES["order_station"], self.arrival_gen, capacity=SERVER_CAPACITY.get("order_station", 1)),
        }

        # Kitchen gate before prep splitting
        self.kitchen_gate = ServiceStation("kitchen_gate", SERVICE_RATES["kitchen_gate"], capacity=SERVER_CAPACITY.get("kitchen_gate", 1))

        # Kitchen network module
        self.kitchen_net = KitchenNetwork(
            service_rates=SERVICE_RATES,
            sim_params=SIM_PARAMS,
            channels=self.channels,
            schedule_event=self.schedule_event,
            prep_probs=PREP_PROBS,
            station_capacity=STATION_CAPACITY,
            final_routing_probs=FINAL_ROUTING_PROBS,
            final_caps=FINAL_CAPS,
            final_balk_if_full=FINAL_BALK_IF_FULL,
            coffee_params={
                "uses_per_brew": COFFEE_USES_PER_BREW,
                "brew_mean": COFFEE_REBREW_MEAN_HRS,
                "brew_std": COFFEE_REBREW_STD_HRS,
            },
            pack_capacity=SERVER_CAPACITY.get("pack", 1),
            final_capacities={
                "seated": SERVER_CAPACITY.get("seated", FINAL_CAPS["seated"]),
                "pickup": SERVER_CAPACITY.get("pickup", FINAL_CAPS["pickup"]),
                "drive_thru": SERVER_CAPACITY.get("drive_thru", FINAL_CAPS["drive_thru"]),
            },
        )

    # ---------------------------
    # Utility helpers
    # ---------------------------
    def schedule_event(self, time, event_type, data):
        heapq.heappush(self.event_list, (time, self.event_counter, event_type, data))
        self.event_counter += 1

    def total_finished_customers(self):
        return len(self.time_in_system)

    # ---------------------------
    # Event handlers
    # ---------------------------
    def handle_arrival(self, event_time):
        self.clock = event_time
        # Route to entry channel
        r = random.random()
        if r < ENTRY_PROBS["cashier"]:
            entry = "cashier"
        elif r < ENTRY_PROBS["cashier"] + ENTRY_PROBS["app"]:
            entry = "app"
        else:
            entry = "order_station"
        self.path_counts["entry"][entry] += 1

        cust = Customer(self.next_customer_id, entry)
        cust.arrival_time = event_time
        self.next_customer_id += 1

        self.enqueue_channel(entry, cust, event_time)

        # Schedule next arrival
        next_t = self.arrival_gen.sample_next(self.clock, self.sim_time_end)
        if next_t is not None:
            self.schedule_event(next_t, ARRIVAL, {})

    def handle_channel_departure(self, event_time, channel_name, customer):
        self.clock = event_time
        ch = self.channels[channel_name]
        ch.num_departures += 1
        ch.busy_count = max(0, ch.busy_count - 1)

        # Next routing
        self.enqueue_kitchen_gate(customer, event_time)

        # Start next in channel
        while ch.queue and ch.busy_count < ch.capacity:
            next_cust, queued_t = ch.queue.pop(0)
            self.start_channel_service(channel_name, next_cust, queued_t)
        ch.server_busy = ch.busy_count > 0

    def handle_kitchen_gate_departure(self, event_time, customer):
        self.clock = event_time
        st = self.kitchen_gate
        st.num_departures += 1
        st.busy_count = max(0, st.busy_count - 1)

        # Hand off to kitchen network
        self.kitchen_net.route_order(customer, event_time)

        # Start next waiting
        while st.queue and st.busy_count < st.capacity:
            next_cust, queued_t = st.queue.pop(0)
            self.start_kitchen_gate_service(next_cust, queued_t)
        st.server_busy = st.busy_count > 0

    def handle_item_departure(self, event_time, station_name, customer, item_idx):
        self.clock = event_time
        self.kitchen_net.handle_item_departure(event_time, station_name, customer, item_idx)

    def handle_pack_departure(self, event_time, customer):
        self.clock = event_time
        self.kitchen_net.handle_pack_departure(event_time, customer)

    def handle_coffee_brew_complete(self, event_time):
        self.clock = event_time
        self.kitchen_net.handle_coffee_brew_complete(event_time)

    def handle_final_departure(self, event_time, destination, customer, lost=False):
        self.clock = event_time
        if not lost:
            self.kitchen_net.handle_final_departure(event_time, destination, customer)
        customer.depart_time = event_time
        if lost:
            self.path_counts["lost"] += 1
            return
        duration = customer.depart_time - customer.arrival_time
        self.time_in_system.append(duration)
        if destination in self.path_counts["final"]:
            self.path_counts["final"][destination] += 1
            self.time_by_final[destination]["sum"] += duration
            self.time_by_final[destination]["count"] += 1

    # ---------------------------
    # Service starters
    # ---------------------------
    def enqueue_channel(self, channel_name, customer, now):
        ch = self.channels[channel_name]
        if (ch.busy_count < ch.capacity) and (len(ch.queue) == 0):
            self.start_channel_service(channel_name, customer, now)
        else:
            ch.queue.append((customer, now))
            ch.num_waited += 1

    def start_channel_service(self, channel_name, customer, queued_time):
        ch = self.channels[channel_name]
        ch.busy_count += 1
        ch.server_busy = ch.busy_count > 0
        wait = self.clock - queued_time
        ch.total_wait_time += wait
        service_time = random.expovariate(ch.mu)
        ch.total_service_time += service_time
        ch.busy_time += service_time
        depart_time = self.clock + service_time
        self.schedule_event(
            depart_time,
            CHANNEL_DEPARTURE,
            {"channel": channel_name, "customer": customer},
        )

    def enqueue_kitchen_gate(self, customer, now):
        st = self.kitchen_gate
        if (st.busy_count < st.capacity) and (len(st.queue) == 0):
            self.start_kitchen_gate_service(customer, now)
        else:
            st.queue.append((customer, now))
            st.num_waited += 1

    def start_kitchen_gate_service(self, customer, queued_time):
        st = self.kitchen_gate
        st.busy_count += 1
        st.server_busy = st.busy_count > 0
        wait = self.clock - queued_time
        st.total_wait_time += wait
        service_time = random.expovariate(st.mu)
        st.total_service_time += service_time
        st.busy_time += service_time
        depart_time = self.clock + service_time
        self.schedule_event(
            depart_time,
            KITCHEN_GATE_DEPARTURE,
            {"customer": customer},
        )

    # ---------------------------
    # Main loop
    # ---------------------------
    def run(self):
        random.seed(self.random_seed)

        first_t = self.arrival_gen.sample_next(0.0, self.sim_time_end)
        if first_t is not None:
            self.schedule_event(first_t, ARRIVAL, {})

        while self.event_list and self.total_finished_customers() < self.max_departures:
            event_time, _, event_type, data = heapq.heappop(self.event_list)
            self.clock = event_time

            if event_type == ARRIVAL:
                self.handle_arrival(event_time)
            elif event_type == CHANNEL_DEPARTURE:
                self.handle_channel_departure(event_time, data["channel"], data["customer"])
            elif event_type == KITCHEN_GATE_DEPARTURE:
                self.handle_kitchen_gate_departure(event_time, data["customer"])
            elif event_type == ITEM_DEPARTURE:
                self.handle_item_departure(event_time, data["station"], data["customer"], data["item_idx"])
            elif event_type == PACK_DEPARTURE:
                self.handle_pack_departure(event_time, data["customer"])
            elif event_type == FINAL_DEPARTURE:
                self.handle_final_departure(event_time, data["destination"], data["customer"], data.get("lost", False))
            elif event_type == COFFEE_BREW_COMPLETE:
                self.handle_coffee_brew_complete(event_time)

        self.print_report()

    # ---------------------------
    # Reporting
    # ---------------------------
    def print_report(self):
        print("=== Simulation finished ===")
        print(f"Final time: {self.clock:.3f} hours")
        finished = self.total_finished_customers()
        print(f"Total finished customers: {finished}")
        if self.time_in_system:
            avg_t = sum(self.time_in_system) / len(self.time_in_system)
            print(f"Average time in system: {avg_t:.3f} hours")
        else:
            print("Average time in system: N/A (no completions)")
        print()

        print("--- Average time in system by final destination ---")
        for dest, stats in self.time_by_final.items():
            if stats["count"] > 0:
                avg_d = stats["sum"] / stats["count"]
                print(f"  {dest}: {avg_d:.3f} hours over {stats['count']} customers")
            else:
                print(f"  {dest}: N/A (0 customers)")
        print()

        # Financials
        revenue = finished * REVENUE_PER_ORDER
        staff_cost = 0.0
        horizon = self.clock
        # Channels
        for ch in self.channels.values():
            staff_cost += STAFF_COST_PER_HOUR.get(ch.name, 0.0) * ch.capacity * horizon
        # Kitchen gate
        staff_cost += STAFF_COST_PER_HOUR.get("kitchen_gate", 0.0) * self.kitchen_gate.capacity * horizon
        # Kitchen prep and pack
        rep = self.kitchen_net.report(self.clock)
        for st in rep["prep"].values():
            staff_cost += STAFF_COST_PER_HOUR.get(st.name, 0.0) * getattr(st, "capacity", 1) * horizon
        staff_cost += STAFF_COST_PER_HOUR.get("pack", 0.0) * rep["pack"].capacity * horizon

        profit = revenue - staff_cost
        print("--- Financials ---")
        print(f"  Revenue: ${revenue:,.2f}")
        print(f"  Staff cost: ${staff_cost:,.2f}")
        print(f"  Profit: ${profit:,.2f}")
        print()

        def station_report(st):
            util = st.busy_time / max(1e-9, self.clock * st.capacity)
            print(f"  Num departures: {st.num_departures}")
            print(f"  Queue length (end): {len(st.queue)}")
            print(f"  Wait total: {st.total_wait_time:.3f} hrs")
            print(f"  Service total: {st.total_service_time:.3f} hrs")
            print(f"  Utilization: {util:.3f}")
            print()

        print("--- Entry channels ---")
        for name in ["cashier", "app", "order_station"]:
            print(f"Channel: {name}")
            station_report(self.channels[name])

        print("Kitchen gate")
        station_report(self.kitchen_gate)

        rep = self.kitchen_net.report(self.clock)
        print("--- Kitchen stations ---")
        for name, st in rep["prep"].items():
            print(f"Kitchen: {name}")
            station_report(st)

        print("Packaging")
        station_report(rep["pack"])

        print("--- Final nodes ---")
        for name, st in rep["final"].items():
            cap = st.capacity
            print(f"Final: {name} (cap {cap})")
            station_report(st)
        print(f"Blocked-at-pack: {rep['pack_blocked']}")
        print(f"Lost customers (balk): {rep['lost']}")

        print("--- Path counts ---")
        print(f"Entry: {self.path_counts['entry']}")
        print(f"Final: {self.path_counts['final']}")
        print(f"Lost: {self.path_counts['lost']}")


if __name__ == "__main__":
    sim = Simulation()
    sim.run()
