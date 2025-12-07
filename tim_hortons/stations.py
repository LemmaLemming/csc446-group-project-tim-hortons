# tim_hortons/stations.py
import simpy
import random
import math
from tim_hortons.models import OrderItem

class StationLogic:
    def __init__(self, env, kitchen, stats, config, menu):
        self.env = env
        self.kitchen = kitchen
        self.stats = stats
        self.config = config
        self.menu = menu

        # Resources
        self.cashier_resource = simpy.Resource(env, capacity=config.NUM_CASHIERS)
        self.dt_ordering_resource = simpy.Resource(env, capacity=config.DRIVE_THRU_NUM_ORDERING_STATIONS)
        self.dt_pickup_resource = simpy.Resource(env, capacity=1) # Window

        # Mobile Slot State
        # slots[slot_index] = count
        self.mobile_slots = {}

        # Drive Thru Queue (SimPy resources manage queues, but we need to track length for balking)
        # We'll use len(resource.queue) + len(resource.users) or manual tracking if needed for balking BEFORE queue.
        # Actually SimPy resource queue is infinite capacity by default, so we need to check length before requesting.

        # Menu frequency processing
        self.menu_items = menu
        self.item_weights = [m.frequency for m in menu]
        self.total_weight = sum(self.item_weights)

    def generate_random_order(self, is_mobile=False, is_drive_thru=False):
        """Generates a random order based on menu frequencies and size decay."""
        from tim_hortons.models import Order

        # Determine number of items (1-5), exponential drop off
        # Weights: [1, 0.5, 0.25, 0.125, 0.0625] (example)
        # User said: "probability drops off exponentially for 2,3,4,5 items"
        # Let's normalize 2^(-(k-1))
        size_probs = [1.0 / (2**i) for i in range(5)] # 1, 0.5, 0.25...
        # Normalize to sum to 1
        total_p = sum(size_probs)
        size_probs = [p/total_p for p in size_probs]

        num_items = random.choices(range(1, 6), weights=size_probs, k=1)[0]

        items = []
        for _ in range(num_items):
            # Pick menu item by frequency
            # random.choices is available in Python 3.6+
            chosen_menu = random.choices(self.menu_items, weights=self.item_weights, k=1)[0]

            # Pick size if applicable (uniform for simplicity unless specified)
            size = None
            if chosen_menu.sizes:
                size = random.choice(chosen_menu.sizes)["size"]

            items.append(OrderItem(menu_item=chosen_menu, size=size))

        return Order(items=items, is_mobile=is_mobile, is_drive_thru=is_drive_thru)

    def get_service_duration(self, mean, std, num_items, multiplier):
        """Calculates service time with lognormal distribution and item multiplier."""
        # Multiplier applied to mean and std per additional item (beyond 1?)
        # "multiplier is applied to the mean and std per additional order." (Assuming item)
        extra_items = max(0, num_items - 1)

        adj_mean = mean * (1 + multiplier * extra_items)
        adj_std = std * (1 + multiplier * extra_items)

        # Convert to lognormal params
        if adj_mean <= 0: return 0

        var = adj_std ** 2
        mu_prime = math.log(adj_mean**2 / math.sqrt(var + adj_mean**2))
        sigma_prime = math.sqrt(math.log(var/adj_mean**2 + 1))

        return random.lognormvariate(mu_prime, sigma_prime)

    # --- PROCESSES ---

    def process_cashier_customer(self, customer):
        """Process for a Dine-in/Take-out customer at Cashier."""
        self.stats.total_cashier_arrivals += 1

        # Check balking/reneging logic
        # "customers can only wait dine_in_max_waittime at which point they will balk"
        # This implies reneging (joining queue, then leaving).

        start_wait = self.env.now
        customer.start_wait_time = start_wait

        # Sample queue length
        self.stats.sample_queues(len(self.dt_ordering_resource.queue), len(self.cashier_resource.queue))

        with self.cashier_resource.request() as req:
            # Wait for server or renege
            result = yield req | self.env.timeout(self.config.CASHIER_MAX_WAIT_TIME_MINUTES)

            if req in result:
                # Got server
                customer.end_wait_time = self.env.now
                self.stats.add_cashier_wait(customer.wait_duration())

                # Order Taking
                customer.order = self.generate_random_order()

                # Determine Dine-in vs Take-out
                # "This is determined randomly by dine_in_probability"
                # (Does this affect service time? Not specified. Just attribute.)
                # Assuming no difference in ordering time.

                duration = self.get_service_duration(
                    self.config.CASHIER_MEAN_TIME,
                    self.config.CASHIER_STD_DEV,
                    len(customer.order.items),
                    self.config.CASHIER_ITEM_MULTIPLIER
                )

                self.stats.total_cashier_service_time += duration
                yield self.env.timeout(duration)
            else:
                # Reneged
                self.stats.cashier_renages += 1
                customer.reneged = True

        # Released Cashier Resource here

        # Send to kitchen (only if served)
        if not customer.reneged:
            yield self.env.process(self.kitchen.process_order(customer.order))
            # Finished
            customer.finish_time = self.env.now

    def process_mobile_customer(self, customer):
        """Process for Mobile App customer."""
        self.stats.total_mobile_arrivals += 1

        # 1. Choose Slot
        # "choose a 15 minute slot... available slots has an equal probability... time slots in the past will not be available."
        # "customers cannot book a slot that the current time is in."

        current_time = self.env.now

        # Define slots: 0-15, 15-30, etc. relative to simulation start.
        # Find current slot index.
        slot_dur = self.config.MOBILE_ORDER_SLOT_WINDOW_MINUTES
        current_slot_idx = int(current_time // slot_dur)

        # Available slots start from next slot
        start_slot = current_slot_idx + 1

        # Max slots? Simulation duration.
        total_slots = int((self.config.SIM_DURATION_HOURS * 60) // slot_dur)

        possible_slots = list(range(start_slot, total_slots))

        if not possible_slots:
            self.stats.mobile_balks += 1
            customer.balked = True
            return

        # "available slots has an equal probability of being chosen"
        # Does "available" mean "not full"? Or just "future"?
        # "if customers cannot book the same slot they will try to book the slot after."
        # This implies they pick a slot *first*, then check availability.

        picked_slot = random.choice(possible_slots)

        # Try to book
        booked_slot = -1
        attempts = 0
        max_attempts = self.config.MOBILE_ORDER_MAX_SLOT_ATTEMPTS # e.g. 2 means try chosen, then next, then stop.

        # Logic: "try to book the slot after. they will do this twice until they give up."
        # Interpreted as: Attempt 1 (Picked), Attempt 2 (Picked+1), Attempt 3 (Picked+2).
        # OR: "do this twice" -> Retry 1, Retry 2. Total 3 attempts.

        for i in range(max_attempts + 1):
            check_slot = picked_slot + i
            if check_slot >= total_slots:
                break

            current_count = self.mobile_slots.get(check_slot, 0)
            if current_count < self.config.MOBILE_ORDER_SLOT_CAPACITY:
                # Book it
                self.mobile_slots[check_slot] = current_count + 1
                booked_slot = check_slot
                break

        if booked_slot == -1:
            self.stats.mobile_balks += 1
            customer.balked = True
            return

        # Order success
        customer.order = self.generate_random_order(is_mobile=True)
        slot_time_start = booked_slot * slot_dur
        customer.order.pickup_slot_start = slot_time_start

        # "sent to the kitchen couple minutes before the slot time... defined by mobile_order_prep_buffer"
        kitchen_send_time = slot_time_start - self.config.MOBILE_ORDER_PREP_BUFFER_MINUTES

        # If current time is already past send time (shouldn't happen if slot is in future), send now.
        if kitchen_send_time < current_time:
            kitchen_send_time = current_time

        wait_time = kitchen_send_time - current_time
        yield self.env.timeout(wait_time)

        # Flag priority? "make mobile orders flagged as priority in the kitchen"
        customer.order.is_priority = True

        # Send to kitchen
        yield self.env.process(self.kitchen.process_order(customer.order))

        # Order Ready
        ready_time = self.env.now
        customer.finish_time = ready_time

        self.stats.total_mobile_orders_fulfilled += 1

        # Check SLA
        # "ready by the slot time" (Assuming start of slot? Or end? Usually start of slot for pickup)
        # "promised slot time" usually means start of the 15 min window.
        if ready_time > slot_time_start:
            customer.sla_violated = True
            self.stats.mobile_sla_violations += 1

    def process_drive_thru_customer(self, customer):
        """Process for Drive-Thru customer."""
        self.stats.total_dt_arrivals += 1

        # Check Line Limit (Balking)
        # "drive thru line limit is an integer... beyond that customers will balk"
        # Queue length = waiting for ordering + ordering
        current_line_len = len(self.dt_ordering_resource.queue) + len(self.dt_ordering_resource.users)

        if current_line_len >= self.config.DRIVE_THRU_LINE_LIMIT:
            self.stats.dt_balks += 1
            customer.balked = True
            return

        customer.start_wait_time = self.env.now

        # Check Priority Threshold
        # "When the threshold is exceeded all drive thru orders below the priority threshold gets flagged"
        # "threshold... like 7 customers waiting... these 7 customers... will be sent to kitchen with priority flag"
        # Wait. "below the priority threshold". If threshold is 6, and there are 7.
        # The user example: "let threshold be 6. if threshold gets exceeded, like 7... these 7 customers... get flagged".
        # This implies that IF the line is long, the customers CURRENTLY in line get priority.

        # I need to know if *this* customer triggers the priority condition for *themselves* or others.
        # "When the threshold is exceeded... orders... gets flagged".
        # Let's check condition now.
        is_high_load = current_line_len > self.config.DRIVE_THRU_PRIORITY_THRESHOLD

        with self.dt_ordering_resource.request() as req:
            yield req

            # Ordering
            customer.end_wait_time = self.env.now
            self.stats.add_dt_wait(customer.wait_duration())
            self.stats.sample_queues(current_line_len, len(self.cashier_resource.queue))

            customer.order = self.generate_random_order(is_drive_thru=True)

            # Apply priority flag if condition met
            # "orders below the priority threshold gets flagged".
            # I assume this means "orders *within* the threshold count" or simply "all orders in this batch".
            # The prompt says: "these 7 customers... their orders will be sent... with priority flag".
            # So if line is long, current orders are priority.
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

            # Send to kitchen
            # Kitchen process runs in background while car moves to pickup?
            # "The ordering node will take some time to order before the order is sent to the kitchen."
            # "once the drive thru orders are processed they are sent to the kitchen."

            # "customers... move to the pickup station."
            # We fork the kitchen process. The customer (car) moves to pickup window queue.
            kitchen_process = self.env.process(self.kitchen.process_order(customer.order))

        # Released Ordering Resource here

        # Move to pickup window
        with self.dt_pickup_resource.request() as pickup_req:
            yield pickup_req

            # At window. Wait for kitchen?
            # "Drive-thru customers will get food in drive-thru window... once kitchen processes... sent to drive thru pickup window"
            # If kitchen is not done, we wait at window.
            if not kitchen_process.triggered:
                yield kitchen_process

            # Service at window (handover time)
            # "pickup window itself has a service time"
            # LogNormal
            pickup_dur = self.get_service_duration(
                self.config.DT_PICKUP_MEAN_TIME,
                self.config.DT_PICKUP_STD_DEV,
                1, 0 # Assume no item multiplier for handover? Or maybe yes? Prompt didn't specify multiplier for pickup.
            )
            yield self.env.timeout(pickup_dur)

            customer.finish_time = self.env.now
            self.stats.add_dt_total_time(customer.total_system_time())
