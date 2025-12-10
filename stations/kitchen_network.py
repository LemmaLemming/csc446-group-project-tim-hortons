import random

from stations.equipment import CoffeeStation, ParallelStation, FinalNode, PackStation


class KitchenNetwork:
    """
    Encapsulates kitchen prep, packaging, and final destination logic.
    Uses the simulation's scheduler to post events.
    """

    def __init__(
        self,
        service_rates,
        sim_params,
        channels,
        schedule_event,
        prep_probs,
        station_capacity,
        final_routing_probs,
        final_caps,
        final_balk_if_full,
        coffee_params,
        pack_capacity=1,
        final_capacities=None,
    ):
        self.channels = channels
        self.schedule_event = schedule_event

        # Routing and capacities
        self.final_routing_probs = final_routing_probs
        self.final_caps = final_caps
        self.final_balk_if_full = final_balk_if_full
        self.lost_customers = 0
        self.final_capacities = final_capacities or final_caps

        self.prep_probs = prep_probs

        # Prep stations
        self.kitchen = {
            "coffee_urn": CoffeeStation(
                "coffee_urn",
                service_rates["coffee_urn"],
                uses_per_brew=coffee_params["uses_per_brew"],
                brew_mean=coffee_params["brew_mean"],
                brew_std=coffee_params["brew_std"],
            ),
            "espresso_machine": ParallelStation(
                "espresso_machine",
                service_rates["espresso_machine"],
                capacity=station_capacity.get("espresso_machine", 1),
            ),
            "hot_food": ParallelStation(
                "hot_food",
                service_rates["hot_food"],
                capacity=station_capacity.get("hot_food", 1),
            ),
        }
        self.pack_station = PackStation("pack", service_rates["pack"], capacity=pack_capacity)

        # Final nodes with capacity and single server
        self.final_nodes = {
            "seated": FinalNode("seated", service_rates["seated"], capacity=self.final_capacities.get("seated", final_caps["seated"])),
            "pickup": FinalNode("pickup", service_rates["pickup"], capacity=self.final_capacities.get("pickup", final_caps["pickup"])),
            "drive_thru": FinalNode("drive_thru", service_rates["drive_thru"], capacity=self.final_capacities.get("drive_thru", final_caps["drive_thru"])),
        }

    # ---------------------------
    # Public entry point from Simulation
    # ---------------------------
    def route_order(self, customer, now):
        """Assign destination and push all items to their stations."""
        # Sample final destination once
        r = random.random()
        if r < self.final_routing_probs["seated"]:
            customer.destination = "seated"
        elif r < self.final_routing_probs["seated"] + self.final_routing_probs["pickup"]:
            customer.destination = "pickup"
        else:
            customer.destination = "drive_thru"

        # Reset outstanding; enqueue items that are required
        customer.outstanding_items = 0
        for idx, item in enumerate(customer.order_items):
            station_name = self.route_item_to_station(item.type)
            if station_name is None:
                continue
            need_prob = self.prep_probs.get(station_name, 1.0)
            if random.random() > need_prob:
                continue
            customer.outstanding_items += 1
            self.enqueue_item(station_name, customer, idx, now)

        # If nothing to prep, go straight to pack
        if customer.outstanding_items == 0:
            self.enqueue_pack(customer, now)

    # ---------------------------
    # Event handlers for Simulation
    # ---------------------------
    def handle_item_departure(self, now, station_name, customer, item_idx):
        st = self.kitchen[station_name]
        brew_duration = None
        if isinstance(st, CoffeeStation):
            brew_duration = st.on_departure(now, self.schedule_event)
        else:
            st.on_departure(now, self.schedule_event)

        # Mark item ready
        customer.order_items[item_idx].ready = True
        customer.outstanding_items -= 1

        if brew_duration:
            self.schedule_event(
                now + brew_duration,
                "coffee_brew_complete",
                {},
            )

        # If all items done, go to pack
        if customer.outstanding_items == 0:
            self.enqueue_pack(customer, now)

        # Station classes handle their own queue refill

    def handle_pack_departure(self, now, customer):
        self.pack_station.complete(now)
        placed = self.try_place_pack_output(customer, now)
        if not placed:
            self.pack_station.blocked_order = customer
            self.pack_station.blocked_since = now
            return
        self.start_next_pack(now)

    def handle_coffee_brew_complete(self, now):
        st = self.kitchen["coffee_urn"]
        st.complete_brew(now, self.schedule_event)

    def handle_final_departure(self, now, destination, customer):
        node = self.final_nodes[destination]
        node.handle_departure(now, self.schedule_event)

        # If pack was blocked, try to move it now that capacity freed
        self.release_blocked_pack(now)

    # ---------------------------
    # Internal helpers: Prep
    # ---------------------------
    def route_item_to_station(self, item_type):
        if item_type == "drink":
            return "coffee_urn"
        if item_type == "espresso":
            return "espresso_machine"
        if item_type == "food":
            return "hot_food"
        return None

    def enqueue_item(self, station_name, customer, item_idx, now):
        st = self.kitchen[station_name]
        st.enqueue(customer, item_idx, now, self.schedule_event)

    # ---------------------------
    # Packaging
    # ---------------------------
    def enqueue_pack(self, customer, now):
        self.pack_station.enqueue(customer, now, self.schedule_event)

    def start_next_pack(self, now):
        st = self.pack_station
        while st.queue and st.busy_count < st.capacity:
            next_cust, queued_t = st.queue.pop(0)
            st.start_service(next_cust, now, queued_t, self.schedule_event)
        st.server_busy = st.busy_count > 0

    def try_place_pack_output(self, customer, now):
        dest = customer.destination
        node = self.final_nodes[dest]
        if not node.has_capacity():
            if self.final_balk_if_full:
                self.lost_customers += 1
                # lost customer exits immediately
                self.schedule_event(
                    now,
                    "final_departure",
                    {"destination": dest, "customer": customer, "lost": True},
                )
                return True  # treated as departed/lost; do not block
            return False  # block pack

        # Enqueue or start final service
        node.enqueue(customer, now, self.schedule_event)
        return True

    def release_blocked_pack(self, now):
        st = self.pack_station
        blocked = getattr(st, "blocked_order", None)
        if not blocked:
            return
        if not self.try_place_pack_output(blocked, now):
            return
        st.release_blocked(now, self.schedule_event)

    # ---------------------------
    # Reporting
    # ---------------------------
    def report(self, sim_clock):
        return {
            "prep": self.kitchen,
            "pack": self.pack_station,
            "final": {name: node.station for name, node in self.final_nodes.items()},
            "pack_blocked": getattr(self.pack_station, "blocked_order", None) is not None,
            "lost": self.lost_customers,
        }
