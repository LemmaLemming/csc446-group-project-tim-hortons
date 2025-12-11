# tim_hortons/reporting.py
import numpy as np

class StatsCollector:
    def __init__(self):
        self.dt_wait_times = []
        self.cashier_wait_times = []
        
        self.dt_queue_lengths = []
        self.cashier_queue_lengths = []
        
        self.total_mobile_arrivals = 0
        self.mobile_balks = 0
        
        self.total_dt_arrivals = 0
        self.dt_balks = 0
        
        self.total_cashier_arrivals = 0
        self.cashier_balks = 0
        self.cashier_renages = 0
        
        self.dt_total_times = []
        
        self.mobile_sla_violations = 0
        self.total_mobile_orders_fulfilled = 0
        self.total_cashier_orders_fulfilled = 0
        self.total_dt_orders_fulfilled = 0
        
        self.cashier_idle_time = 0.0
        self.total_sim_time = 0.0
        self.num_cashiers = 0
        
        self.total_cashier_service_time = 0.0
        self.total_dt_ordering_service_time = 0.0
        self.num_dt_ordering_stations = 0

        self.total_counter_attempts = 0
        self.counter_blocked_count = 0

        self.total_revenue = 0.0
        self.gross_profit = 0.0

    def add_dt_wait(self, time):
        self.dt_wait_times.append(time)

    def add_cashier_wait(self, time):
        self.cashier_wait_times.append(time)
        
    def add_dt_total_time(self, time):
        self.dt_total_times.append(time)
        
    def sample_queues(self, dt_len, cashier_len):
        self.dt_queue_lengths.append(dt_len)
        self.cashier_queue_lengths.append(cashier_len)

    def record_counter_attempt(self, blocked: bool):
        self.total_counter_attempts += 1
        if blocked:
            self.counter_blocked_count += 1

    def track_revenue(self, order):
        rev = order.total_price
        self.total_revenue += rev

        profit = 0.0
        import config

        for item in order.items:
            st = item.menu_item.station
            margin = 0.0
            if st == "coffee" or st == "drinks":
                margin = config.MARGIN_COFFEE_DRINKS
            elif st == "espresso":
                margin = config.MARGIN_ESPRESSO
            elif st == "hot_foods":
                margin = config.MARGIN_HOT_FOODS
            else:
                margin = 0.0

            profit += item.price * margin

        self.gross_profit += profit

    def print_report(self, config):
        print("=== Tim Hortons Simulation Report ===")
        print(f"Simulation Duration: {self.total_sim_time/60:.2f} hours")
        
        total_processed = (self.total_mobile_orders_fulfilled +
                           self.total_cashier_orders_fulfilled +
                           self.total_dt_orders_fulfilled)
        print(f"Total Customers Processed: {total_processed}")

        print("\n--- Financials ---")
        num_kitchen_staff = sum(config.STATION_EMPLOYEES.values())
        total_employees = self.num_cashiers + self.num_dt_ordering_stations + num_kitchen_staff
        
        hours_worked = self.total_sim_time / 60.0
        total_wages = total_employees * hours_worked * config.HOURLY_WAGE

        net_profit = self.gross_profit - total_wages

        print(f"Total Revenue: ${self.total_revenue:,.2f}")
        print(f"Gross Profit: ${self.gross_profit:,.2f}")
        print(f"Total Wages ({total_employees} employees): ${total_wages:,.2f}")
        print(f"Net Profit: ${net_profit:,.2f}")

        print("\n--- Tail Latencies ---")
        if self.dt_wait_times:
            avg_dt_wait = np.mean(self.dt_wait_times)
            med_dt_wait = np.median(self.dt_wait_times)
            print(f"Drive-Thru Ordering Wait: Avg={avg_dt_wait:.2f}m, Median={med_dt_wait:.2f}m")
        else:
            print("Drive-Thru Ordering Wait: N/A")
            
        if self.dt_queue_lengths:
            avg_dt_q = np.mean(self.dt_queue_lengths)
            print(f"Drive-Thru Ordering Queue Length (Avg): {avg_dt_q:.2f}")
        
        if self.dt_total_times:
            p90_dt = np.percentile(self.dt_total_times, 90)
            print(f"90th Percentile Drive-Thru Time: {p90_dt:.2f}m (Threshold: {config.SLA_DRIVE_THRU_WAIT_THRESHOLD}m)")
        
        if self.cashier_wait_times:
            avg_cashier_wait = np.mean(self.cashier_wait_times)
            med_cashier_wait = np.median(self.cashier_wait_times)
            p95_cashier_wait = np.percentile(self.cashier_wait_times, 95)
            print(f"Cashier Wait: Avg={avg_cashier_wait:.2f}m, Median={med_cashier_wait:.2f}m")
            print(f"95th Percentile Cashier Wait Time: {p95_cashier_wait:.2f}m")
        
        if self.cashier_queue_lengths:
            avg_cashier_q = np.mean(self.cashier_queue_lengths)
            print(f"Cashier Queue Length (Avg): {avg_cashier_q:.2f}")

        if self.total_mobile_orders_fulfilled > 0:
            sla_rate = (self.mobile_sla_violations / self.total_mobile_orders_fulfilled) * 100
            print(f"Mobile SLA Violation Rate: {sla_rate:.2f}% ({self.mobile_sla_violations}/{self.total_mobile_orders_fulfilled})")
        else:
            print("Mobile SLA Violation Rate: N/A")

        print("\n--- Capacity & Blocking ---")
        if self.total_mobile_arrivals > 0:
            print(f"Mobile Balking Rate (Slots Full): {(self.mobile_balks/self.total_mobile_arrivals)*100:.2f}%")
        
        if self.total_dt_arrivals > 0:
            print(f"Drive-Thru Balking Rate (Queue Full): {(self.dt_balks/self.total_dt_arrivals)*100:.2f}%")
            
        if self.total_cashier_arrivals > 0:
            print(f"Cashier Reneging Rate (Wait too long): {(self.cashier_renages/self.total_cashier_arrivals)*100:.2f}%")

        if self.total_counter_attempts > 0:
            blocked_rate = (self.counter_blocked_count / self.total_counter_attempts) * 100
            print(f"Orders Blocked by Full Counter: {blocked_rate:.2f}% ({self.counter_blocked_count}/{self.total_counter_attempts})")
        else:
            print("Orders Blocked by Full Counter: N/A")

        print("\n--- Resource Efficiency ---")
        total_cashier_capacity = self.num_cashiers * self.total_sim_time
        if total_cashier_capacity > 0:
             cashier_utilization = self.total_cashier_service_time / total_cashier_capacity
             cashier_idle_rate = 1.0 - cashier_utilization
             print(f"Cashier Idle Rate: {cashier_idle_rate*100:.2f}%")
        else:
             print("Cashier Idle Rate: N/A")

        total_dt_capacity = self.num_dt_ordering_stations * self.total_sim_time
        if total_dt_capacity > 0:
             dt_utilization = self.total_dt_ordering_service_time / total_dt_capacity
             dt_idle_rate = 1.0 - dt_utilization
             print(f"Drive-Thru Ordering Staff Idle Rate: {dt_idle_rate*100:.2f}%")
        else:
             print("Drive-Thru Ordering Staff Idle Rate: N/A")

    def get_stats_dict(self):
        """Returns key statistics as a dictionary for aggregation."""
        import config

        # Financials
        num_kitchen_staff = sum(config.STATION_EMPLOYEES.values())
        total_employees = self.num_cashiers + self.num_dt_ordering_stations + num_kitchen_staff
        hours_worked = self.total_sim_time / 60.0
        total_wages = total_employees * hours_worked * config.HOURLY_WAGE
        net_profit = self.gross_profit - total_wages

        # Wait Times
        avg_dt_wait = np.mean(self.dt_wait_times) if self.dt_wait_times else 0.0
        med_dt_wait = np.median(self.dt_wait_times) if self.dt_wait_times else 0.0
        p90_dt_wait = np.percentile(self.dt_wait_times, 90) if self.dt_wait_times else 0.0

        avg_cashier_wait = np.mean(self.cashier_wait_times) if self.cashier_wait_times else 0.0
        med_cashier_wait = np.median(self.cashier_wait_times) if self.cashier_wait_times else 0.0
        p95_cashier_wait = np.percentile(self.cashier_wait_times, 95) if self.cashier_wait_times else 0.0

        # Queues
        avg_dt_q = np.mean(self.dt_queue_lengths) if self.dt_queue_lengths else 0.0
        avg_cashier_q = np.mean(self.cashier_queue_lengths) if self.cashier_queue_lengths else 0.0

        # Total Times
        p90_dt_total = np.percentile(self.dt_total_times, 90) if self.dt_total_times else 0.0

        # Throughput
        total_processed = (self.total_mobile_orders_fulfilled +
                           self.total_cashier_orders_fulfilled +
                           self.total_dt_orders_fulfilled)

        # Violations/Balks
        mobile_sla_rate = (self.mobile_sla_violations / self.total_mobile_orders_fulfilled) * 100 if self.total_mobile_orders_fulfilled > 0 else 0.0
        mobile_balk_rate = (self.mobile_balks / self.total_mobile_arrivals) * 100 if self.total_mobile_arrivals > 0 else 0.0
        dt_balk_rate = (self.dt_balks / self.total_dt_arrivals) * 100 if self.total_dt_arrivals > 0 else 0.0
        cashier_renege_rate = (self.cashier_renages / self.total_cashier_arrivals) * 100 if self.total_cashier_arrivals > 0 else 0.0
        counter_blocked_rate = (self.counter_blocked_count / self.total_counter_attempts) * 100 if self.total_counter_attempts > 0 else 0.0

        # Idle Rates
        total_cashier_capacity = self.num_cashiers * self.total_sim_time
        cashier_idle_rate = 0.0
        if total_cashier_capacity > 0:
             cashier_utilization = self.total_cashier_service_time / total_cashier_capacity
             cashier_idle_rate = (1.0 - cashier_utilization) * 100

        total_dt_capacity = self.num_dt_ordering_stations * self.total_sim_time
        dt_idle_rate = 0.0
        if total_dt_capacity > 0:
             dt_utilization = self.total_dt_ordering_service_time / total_dt_capacity
             dt_idle_rate = (1.0 - dt_utilization) * 100

        return {
            "net_profit": net_profit,
            "avg_dt_wait": avg_dt_wait,
            "med_dt_wait": med_dt_wait,
            "p90_dt_wait": p90_dt_wait,
            "avg_cashier_wait": avg_cashier_wait,
            "med_cashier_wait": med_cashier_wait,
            "p95_cashier_wait": p95_cashier_wait,
            "avg_dt_queue": avg_dt_q,
            "avg_cashier_queue": avg_cashier_q,
            "p90_dt_total_time": p90_dt_total,
            "total_throughput": total_processed,
            "mobile_sla_violation_rate": mobile_sla_rate,
            "mobile_balk_rate": mobile_balk_rate,
            "dt_balk_rate": dt_balk_rate,
            "cashier_renege_rate": cashier_renege_rate,
            "counter_blocked_rate": counter_blocked_rate,
            "cashier_idle_rate": cashier_idle_rate,
            "dt_idle_rate": dt_idle_rate
        }
