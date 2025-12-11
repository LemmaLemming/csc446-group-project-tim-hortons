# tim_hortons/kitchen.py
import simpy
import random
import math
import config
from models import Order

def get_normal_duration(mean, std):
    """Calculates duration from normal distribution, ensuring non-negative."""
    val = random.normalvariate(mean, std)
    return max(0.0, val)

class BaseStation:
    """Base station logic using PriorityResource."""
    def __init__(self, env, name, params):
        self.env = env
        self.name = name
        self.params = params
        # PriorityResource: smaller integer = higher priority
        self.resource = simpy.PriorityResource(env, capacity=params.get("capacity", 1))

    def process_item(self, item, is_priority):
        """Standard processing with normal delay."""
        priority = 0 if is_priority else 1
        with self.resource.request(priority=priority) as req:
            yield req
            duration = get_normal_duration(self.params["mean"], self.params["std"])
            yield self.env.timeout(duration)

class CoffeeStation(BaseStation):
    """
    Coffee Station with 2 Urns.
    - Capacity: 2 Urns (resources).
    - Logic: Use urn, decrement cup count.
    - If empty, refill (block). Refill takes fixed time.
    """
    def __init__(self, env, name, params):
        self.env = env
        self.name = name
        self.params = params
        # Resource represents the Urns themselves. Capacity = number of urns (2).
        self.resource = simpy.PriorityResource(env, capacity=params.get("capacity", 2))
        self.urns = [CoffeeUrn(env, i) for i in range(params.get("capacity", 2))]

    def process_item(self, item, is_priority):
        priority = 0 if is_priority else 1
        reqs = [urn.resource.request(priority=priority) for urn in self.urns]
        req_map = {req: urn for req, urn in zip(reqs, self.urns)}

        try:
            results = yield simpy.AnyOf(self.env, reqs)
            winner_req = list(results.keys())[0]
            winner_urn = req_map[winner_req]

            for req in reqs:
                if req != winner_req:
                    req.cancel()

            yield self.env.process(winner_urn.serve_cup(winner_req, self.params))

        finally:
            if 'winner_req' in locals():
                 winner_urn.resource.release(winner_req)

class CoffeeUrn:
    def __init__(self, env, id):
        self.env = env
        self.id = id
        self.resource = simpy.PriorityResource(env, capacity=1)
        self.cups_left = config.COFFEE_URN_CAPACITY

    def serve_cup(self, req, params):
        if self.cups_left <= 0:
            yield self.env.timeout(config.COFFEE_URN_REFILL_TIME)
            self.cups_left = config.COFFEE_URN_CAPACITY

        duration = get_normal_duration(params["mean"], params["std"])
        yield self.env.timeout(duration)
        self.cups_left -= 1


class EspressoStation(BaseStation):
    """
    Espresso Station.
    - Capacity: 1.
    - Failure Logic: Weibull failure.
    - Repair: 2 min.
    - Interruption: Resets order.
    """
    def __init__(self, env, name, params):
        super().__init__(env, name, params)
        self.env.process(self.failure_loop())
        self.broken = False
        self.current_process = None

    def failure_loop(self):
        while True:
            time_to_fail = random.weibullvariate(config.ESPRESSO_FAILURE_T, config.ESPRESSO_FAILURE_K)
            yield self.env.timeout(time_to_fail)

            self.broken = True

            if self.current_process and self.current_process.is_alive:
                try:
                    self.current_process.interrupt("broken")
                except RuntimeError:
                    pass

            req = self.resource.request(priority=-1)
            yield req

            yield self.env.timeout(config.ESPRESSO_REPAIR_TIME)
            self.resource.release(req)
            self.broken = False

    def process_item(self, item, is_priority):
        while True:
            try:
                priority = 0 if is_priority else 1
                with self.resource.request(priority=priority) as req:
                    yield req
                    if self.broken:
                        yield self.env.timeout(0.1)
                        continue

                    self.current_process = self.env.process(self._make_espresso(self.params))
                    success = yield self.current_process
                    if success:
                        break # Success
                    # else continue loop (restart)
            except simpy.Interrupt:
                pass

    def _make_espresso(self, params):
        try:
            duration = get_normal_duration(params["mean"], params["std"])
            yield self.env.timeout(duration)
            return True
        except simpy.Interrupt:
            # Interrupted (broken). Return False to signal restart.
            return False

class Counter:
    """
    Counter Queue Logic.
    - Capacity: N orders.
    - Limbo: Infinite.
    """
    def __init__(self, env, capacity):
        self.env = env
        self.capacity = capacity
        self.active_count = 0
        self.limbo_queue = []
        self.limbo_event = simpy.Event(env)

    def request_slot(self, order):
        if getattr(order, 'on_counter', False):
            return True

        if self.active_count < self.capacity:
            self.active_count += 1
            order.on_counter = True
            return True
        else:
            if order not in self.limbo_queue:
                self.limbo_queue.append(order)
            return False

    def free_slot(self):
        self.active_count -= 1
        if self.limbo_queue:
            next_order = self.limbo_queue.pop(0)
            self.active_count += 1
            next_order.on_counter = True
            if hasattr(next_order, 'limbo_event'):
                next_order.limbo_event.succeed()

class Kitchen:
    def __init__(self, env, stations_config):
        self.env = env
        self.stations = {}

        for name, params in stations_config.items():
            st_type = params.get("type", "simple")
            if st_type == "coffee":
                self.stations[name] = CoffeeStation(env, name, params)
            elif st_type == "espresso":
                self.stations[name] = EspressoStation(env, name, params)
            else:
                self.stations[name] = BaseStation(env, name, params)

        self.counter = Counter(env, config.COUNTER_CAPACITY)

    def process_order(self, order: Order):
        events = []
        for item in order.items:
            station_name = item.menu_item.station
            if station_name in self.stations:
                st = self.stations[station_name]
                events.append(self.env.process(st.process_item(item, order.is_priority)))
            else:
                pass
        
        if events:
            yield simpy.AllOf(self.env, events)
        
        if order.is_drive_thru:
            return

        if not self.counter.request_slot(order):
            order.blocked_by_counter = True
            order.limbo_event = simpy.Event(self.env)
            yield order.limbo_event
        
        z = random.gauss(0, 1)
        pickup_time = math.exp(config.PICKUP_DIST_MU + config.PICKUP_DIST_SIGMA * z)
        pickup_time_min = pickup_time / 60.0
        
        yield self.env.timeout(pickup_time_min)
        
        self.counter.free_slot()
