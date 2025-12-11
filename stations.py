# tim_hortons/stations.py
import simpy
import random
import math
from models import OrderItem

class StationLogic:
    def __init__(self, env, kitchen, stats, config, menu):
        self.env = env
        self.kitchen = kitchen
        self.stats = stats
        self.config = config
        self.menu = menu
        
        self.cashier_resource = simpy.Resource(env, capacity=config.NUM_CASHIERS)
        self.dt_ordering_resource = simpy.Resource(env, capacity=config.DRIVE_THRU_NUM_ORDERING_STATIONS)
        self.dt_pickup_resource = simpy.Resource(env, capacity=1)
        
        self.mobile_slots = {} 
        
        self.menu_items = menu
        self.item_weights = [m.frequency for m in menu]
        self.total_weight = sum(self.item_weights)

    def generate_random_order(self, is_mobile=False, is_drive_thru=False):
        from models import Order
        
        size_probs = [1.0 / (2**i) for i in range(5)]
        total_p = sum(size_probs)
        size_probs = [p/total_p for p in size_probs]
        
        num_items = random.choices(range(1, 6), weights=size_probs, k=1)[0]
        
        items = []
        for _ in range(num_items):
            chosen_menu = random.choices(self.menu_items, weights=self.item_weights, k=1)[0]
            
            size = None
            price = 0.0
            if chosen_menu.sizes:
                picked_size_dict = random.choice(chosen_menu.sizes)
                size = picked_size_dict["size"]
                price = picked_size_dict.get("price", 0.0)
            elif chosen_menu.price is not None:
                price = chosen_menu.price
                
            items.append(OrderItem(menu_item=chosen_menu, size=size, price=price))
            
        return Order(items=items, is_mobile=is_mobile, is_drive_thru=is_drive_thru)

    def get_service_duration(self, mean, std, num_items, multiplier):
        extra_items = max(0, num_items - 1)
        
        adj_mean = mean * (1 + multiplier * extra_items)
        adj_std = std * (1 + multiplier * extra_items)
        
        if adj_mean <= 0: return 0
        
        var = adj_std ** 2
        mu_prime = math.log(adj_mean**2 / math.sqrt(var + adj_mean**2))
        sigma_prime = math.sqrt(math.log(var/adj_mean**2 + 1))
        
        return random.lognormvariate(mu_prime, sigma_prime)

    def process_cashier_customer(self, customer):
        self.stats.total_cashier_arrivals += 1
        
        start_wait = self.env.now
        customer.start_wait_time = start_wait
        
        self.stats.sample_queues(len(self.dt_ordering_resource.queue), len(self.cashier_resource.queue))

        with self.cashier_resource.request() as req:
            result = yield req | self.env.timeout(self.config.CASHIER_MAX_WAIT_TIME_MINUTES)
            
            if req in result:
                customer.end_wait_time = self.env.now
                self.stats.add_cashier_wait(customer.wait_duration())
                
                customer.order = self.generate_random_order()
                
                duration = self.get_service_duration(
                    self.config.CASHIER_MEAN_TIME, 
                    self.config.CASHIER_STD_DEV, 
                    len(customer.order.items), 
                    self.config.CASHIER_ITEM_MULTIPLIER
                )
                
                self.stats.total_cashier_service_time += duration
                yield self.env.timeout(duration)
            else:
                self.stats.cashier_renages += 1
                customer.reneged = True
            
        if not customer.reneged:
            yield self.env.process(self.kitchen.process_order(customer.order))

            if getattr(customer.order, 'blocked_by_counter', False):
                 self.stats.record_counter_attempt(True)
            else:
                 self.stats.record_counter_attempt(False)

            self.stats.track_revenue(customer.order)

            customer.finish_time = self.env.now
            self.stats.total_cashier_orders_fulfilled += 1

    def process_mobile_customer(self, customer):
        self.stats.total_mobile_arrivals += 1
        
        current_time = self.env.now
        slot_dur = self.config.MOBILE_ORDER_SLOT_WINDOW_MINUTES
        current_slot_idx = int(current_time // slot_dur)
        start_slot = current_slot_idx + 1
        total_slots = int((self.config.SIM_DURATION_HOURS * 60) // slot_dur)
        possible_slots = list(range(start_slot, total_slots))
        
        if not possible_slots:
            self.stats.mobile_balks += 1
            customer.balked = True
            return

        picked_slot = random.choice(possible_slots)
        booked_slot = -1
        max_attempts = self.config.MOBILE_ORDER_MAX_SLOT_ATTEMPTS
        
        for i in range(max_attempts + 1):
            check_slot = picked_slot + i
            if check_slot >= total_slots:
                break
            current_count = self.mobile_slots.get(check_slot, 0)
            if current_count < self.config.MOBILE_ORDER_SLOT_CAPACITY:
                self.mobile_slots[check_slot] = current_count + 1
                booked_slot = check_slot
                break
        
        if booked_slot == -1:
            self.stats.mobile_balks += 1
            customer.balked = True
            return

        customer.order = self.generate_random_order(is_mobile=True)
        slot_time_start = booked_slot * slot_dur
        customer.order.pickup_slot_start = slot_time_start
        
        kitchen_send_time = slot_time_start - self.config.MOBILE_ORDER_PREP_BUFFER_MINUTES
        if kitchen_send_time < current_time:
            kitchen_send_time = current_time
            
        wait_time = kitchen_send_time - current_time
        yield self.env.timeout(wait_time)
        
        customer.order.is_priority = True
        
        yield self.env.process(self.kitchen.process_order(customer.order))
        
        if getattr(customer.order, 'blocked_by_counter', False):
             self.stats.record_counter_attempt(True)
        else:
             self.stats.record_counter_attempt(False)

        self.stats.track_revenue(customer.order)

        ready_time = self.env.now
        customer.finish_time = ready_time
        self.stats.total_mobile_orders_fulfilled += 1
        
        if ready_time > slot_time_start:
            customer.sla_violated = True
            self.stats.mobile_sla_violations += 1

    def process_drive_thru_customer(self, customer):
        self.stats.total_dt_arrivals += 1
        
        current_line_len = len(self.dt_ordering_resource.queue) + len(self.dt_ordering_resource.users)
        
        if current_line_len >= self.config.DRIVE_THRU_LINE_LIMIT:
            self.stats.dt_balks += 1
            customer.balked = True
            return

        customer.start_wait_time = self.env.now
        
        is_high_load = current_line_len > self.config.DRIVE_THRU_PRIORITY_THRESHOLD
        
        with self.dt_ordering_resource.request() as req:
            yield req
            
            customer.end_wait_time = self.env.now
            self.stats.add_dt_wait(customer.wait_duration())
            self.stats.sample_queues(current_line_len, len(self.cashier_resource.queue))
            
            customer.order = self.generate_random_order(is_drive_thru=True)
            
            if is_high_load:
                customer.order.is_priority = True
                
            duration = self.get_service_duration(
                self.config.DT_ORDER_MEAN_TIME, 
                self.config.DT_ORDER_STD_DEV, 
                len(customer.order.items), 
                self.config.DT_ITEM_MULTIPLIER
            )
            
            self.stats.total_dt_ordering_service_time += duration
            yield self.env.timeout(duration)
            
            kitchen_process = self.env.process(self.kitchen.process_order(customer.order))
            
        with self.dt_pickup_resource.request() as pickup_req:
            yield pickup_req
            
            if not kitchen_process.triggered:
                yield kitchen_process
            
            pickup_dur = self.get_service_duration(
                self.config.DT_PICKUP_MEAN_TIME,
                self.config.DT_PICKUP_STD_DEV,
                1, 0
            )
            yield self.env.timeout(pickup_dur)
            
            self.stats.track_revenue(customer.order)

            customer.finish_time = self.env.now
            self.stats.total_dt_orders_fulfilled += 1
            self.stats.add_dt_total_time(customer.total_system_time())
