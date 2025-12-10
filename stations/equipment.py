from stations.kitchen_station import KitchenStation
from stations.service_station import ServiceStation
import random


class ParallelStation(KitchenStation):
    """
    A kitchen station with parallel capacity (busy_count <= capacity).
    """
    def __init__(self, name, mu, capacity=1):
        super().__init__(name, mu)
        self.capacity = max(1, capacity)
        self.busy_count = 0
        self.queue = []  # (customer, item_idx, queued_time)

    # --- Queueing helpers ---
    def can_start(self):
        return self.busy_count < self.capacity

    def enqueue(self, customer, item_idx, now, schedule_event):
        if self.can_start():
            self.start_service(customer, item_idx, now, now, schedule_event)
        else:
            self.queue.append((customer, item_idx, now))
            self.num_waited += 1

    def start_service(self, customer, item_idx, now, queued_time, schedule_event):
        self.busy_count += 1
        self.server_busy = True
        wait = now - queued_time
        self.total_wait_time += wait
        service_time = random.expovariate(self.mu)
        self.total_service_time += service_time
        self.busy_time += service_time
        depart_time = now + service_time
        schedule_event(
            depart_time,
            "item_departure",
            {"station": self.name, "customer": customer, "item_idx": item_idx},
        )

    def on_departure(self, now, schedule_event):
        self.num_departures += 1
        self.busy_count = max(0, self.busy_count - 1)
        # Try to start more work if queued
        while self.queue and self.can_start():
            next_cust, next_idx, queued_t = self.queue.pop(0)
            self.start_service(next_cust, next_idx, now, queued_t, schedule_event)
        self.server_busy = self.busy_count > 0


class CoffeeStation(ParallelStation):
    """
    Coffee urn with batch depletion and rebrew downtime.
    """
    def __init__(self, name, mu, uses_per_brew, brew_mean, brew_std):
        super().__init__(name, mu, capacity=1)
        self.uses_per_brew = uses_per_brew
        self.uses_left = uses_per_brew
        self.brew_mean = brew_mean
        self.brew_std = brew_std
        self.brewing = False

    def can_start(self):
        return (not self.brewing) and super().can_start()

    def on_departure(self, now, schedule_event):
        self.num_departures += 1
        self.busy_count = max(0, self.busy_count - 1)

        # Deplete and maybe trigger brew
        self.uses_left -= 1
        brew_duration = None
        if self.uses_left <= 0:
            self.uses_left = self.uses_per_brew
            self.brewing = True
            brew_duration = max(0.0, random.gauss(self.brew_mean, self.brew_std))

        # Try to start more work if queued and not brewing
        if not self.brewing:
            while self.queue and self.can_start():
                next_cust, next_idx, queued_t = self.queue.pop(0)
                self.start_service(next_cust, next_idx, now, queued_t, schedule_event)
        self.server_busy = self.busy_count > 0
        return brew_duration

    def complete_brew(self, now, schedule_event):
        self.brewing = False
        while self.queue and self.can_start():
            next_cust, next_idx, queued_t = self.queue.pop(0)
            self.start_service(next_cust, next_idx, now, queued_t, schedule_event)
        self.server_busy = self.busy_count > 0


class FinalNode:
    """
    Final destination node with capacity and single server.
    """
    def __init__(self, name, mu, capacity):
        self.station = ServiceStation(name, mu)
        self.capacity = capacity

    def occupancy(self):
        in_service = 1 if self.station.server_busy else 0
        return len(self.station.queue) + in_service

    def has_capacity(self):
        return self.occupancy() < self.capacity

    def enqueue(self, customer, now, schedule_event):
        st = self.station
        if (not st.server_busy) and (len(st.queue) == 0):
            self.start_service(customer, now, now, schedule_event)
        else:
            st.queue.append((customer, now))
            st.num_waited += 1

    def start_service(self, customer, now, queued_time, schedule_event):
        st = self.station
        st.server_busy = True
        wait = now - queued_time
        st.total_wait_time += wait
        service_time = random.expovariate(st.mu)
        st.total_service_time += service_time
        st.busy_time += service_time
        depart_time = now + service_time
        schedule_event(
            depart_time,
            "final_departure",
            {"destination": st.name, "customer": customer},
        )

    def handle_departure(self, now, schedule_event):
        st = self.station
        st.num_departures += 1
        if st.queue:
            next_cust, queued_t = st.queue.pop(0)
            self.start_service(next_cust, now, queued_t, schedule_event)
        else:
            st.server_busy = False


class PackStation(KitchenStation):
    """
    Packaging station that can block on downstream capacity. It exposes enqueue,
    start, complete, and release_blocked helpers so the KitchenNetwork can
    coordinate without managing raw queues directly.
    """
    def __init__(self, name, mu):
        super().__init__(name, mu)
        self.blocked_order = None
        self.blocked_since = None

    def enqueue(self, customer, now, schedule_event):
        if self.blocked_order:
            self.queue.append((customer, now))
            self.num_waited += 1
            return
        if (not self.server_busy) and (len(self.queue) == 0):
            self.start_service(customer, now, now, schedule_event)
        else:
            self.queue.append((customer, now))
            self.num_waited += 1

    def start_service(self, customer, now, queued_time, schedule_event):
        self.server_busy = True
        wait = now - queued_time
        self.total_wait_time += wait
        service_time = random.expovariate(self.mu)
        self.total_service_time += service_time
        self.busy_time += service_time
        depart_time = now + service_time
        schedule_event(
            depart_time,
            "pack_departure",
            {"customer": customer},
        )

    def complete(self, now):
        self.num_departures += 1

    def release_blocked(self, now, schedule_event):
        self.blocked_order = None
        self.blocked_since = None
        if self.queue:
            next_cust, queued_t = self.queue.pop(0)
            self.start_service(next_cust, now, queued_t, schedule_event)
        else:
            self.server_busy = False
