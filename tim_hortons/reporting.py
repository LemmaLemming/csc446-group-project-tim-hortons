# tim_hortons/reporting.py
import numpy as np

class StatsCollector:
    def __init__(self):
        # Wait times at ordering stations (arrival to finish ordering)
        self.dt_wait_times = []
        self.cashier_wait_times = []

        # Queue lengths (sampled periodically or on change)
        self.dt_queue_lengths = []
        self.cashier_queue_lengths = []

        # Balking/Reneging counts
        self.total_mobile_arrivals = 0
        self.mobile_balks = 0 # Slots full

        self.total_dt_arrivals = 0
        self.dt_balks = 0 # Line limit

        self.total_cashier_arrivals = 0
        self.cashier_balks = 0 # (Not really used in standard logic unless line limit, but maybe "reneged" is better)
        self.cashier_renages = 0 # Waited too long

        # Service times / Latencies
        self.dt_total_times = [] # Arrival to exit

        # SLA
        self.mobile_sla_violations = 0
        self.total_mobile_orders_fulfilled = 0

        # Staff Idle tracking (manual update or sampling)
        self.cashier_idle_time = 0.0
        self.total_sim_time = 0.0
        self.num_cashiers = 0

        self.total_cashier_service_time = 0.0
        self.total_dt_ordering_service_time = 0.0
        self.num_dt_ordering_stations = 0

    def add_dt_wait(self, time):
        self.dt_wait_times.append(time)

    def add_cashier_wait(self, time):
        self.cashier_wait_times.append(time)

    def add_dt_total_time(self, time):
        self.dt_total_times.append(time)

    def sample_queues(self, dt_len, cashier_len):
        self.dt_queue_lengths.append(dt_len)
        self.cashier_queue_lengths.append(cashier_len)

    def print_report(self, config):
        print("=== Tim Hortons Simulation Report ===")
        print(f"Simulation Duration: {self.total_sim_time/60:.2f} hours")

        # --- Tail Latencies ---
        print("\n--- Tail Latencies ---")

        # DT Waiting
        if self.dt_wait_times:
            avg_dt_wait = np.mean(self.dt_wait_times)
            med_dt_wait = np.median(self.dt_wait_times)
            print(f"Drive-Thru Ordering Wait: Avg={avg_dt_wait:.2f}m, Median={med_dt_wait:.2f}m")
        else:
            print("Drive-Thru Ordering Wait: N/A")

        # DT Queue
        if self.dt_queue_lengths:
            avg_dt_q = np.mean(self.dt_queue_lengths)
            print(f"Drive-Thru Ordering Queue Length (Avg): {avg_dt_q:.2f}")

        # DT Total Time 90th Percentile
        if self.dt_total_times:
            p90_dt = np.percentile(self.dt_total_times, 90)
            print(f"90th Percentile Drive-Thru Time: {p90_dt:.2f}m (Threshold: {config.SLA_DRIVE_THRU_WAIT_THRESHOLD}m)")

        # Cashier Wait
        if self.cashier_wait_times:
            avg_cashier_wait = np.mean(self.cashier_wait_times)
            med_cashier_wait = np.median(self.cashier_wait_times)
            p95_cashier_wait = np.percentile(self.cashier_wait_times, 95)
            print(f"Cashier Wait: Avg={avg_cashier_wait:.2f}m, Median={med_cashier_wait:.2f}m")
            print(f"95th Percentile Cashier Wait Time: {p95_cashier_wait:.2f}m")

        # Cashier Queue
        if self.cashier_queue_lengths:
            avg_cashier_q = np.mean(self.cashier_queue_lengths)
            print(f"Cashier Queue Length (Avg): {avg_cashier_q:.2f}")

        # Mobile SLA
        if self.total_mobile_orders_fulfilled > 0:
            sla_rate = (self.mobile_sla_violations / self.total_mobile_orders_fulfilled) * 100
            print(f"Mobile SLA Violation Rate: {sla_rate:.2f}% ({self.mobile_sla_violations}/{self.total_mobile_orders_fulfilled})")
        else:
            print("Mobile SLA Violation Rate: N/A")

        # --- Capacity & Blocking ---
        print("\n--- Capacity & Blocking ---")
        if self.total_mobile_arrivals > 0:
            print(f"Mobile Balking Rate (Slots Full): {(self.mobile_balks/self.total_mobile_arrivals)*100:.2f}%")

        if self.total_dt_arrivals > 0:
            print(f"Drive-Thru Balking Rate (Queue Full): {(self.dt_balks/self.total_dt_arrivals)*100:.2f}%")

        if self.total_cashier_arrivals > 0:
            # "balking rate of dine in customers waiting for cashier" (Wait, user asked for balking AND reneging)
            # Reneging is usually leaving AFTER joining queue. Balking is refusing to join.
            # Code implements reneging (max wait time).
            # If line limit existed for cashier, we'd have balks. But user only specified max wait time -> reneging.
            # I'll report Reneging as "Balking/Reneging" or separate if I had explicit balking.
            print(f"Cashier Reneging Rate (Wait too long): {(self.cashier_renages/self.total_cashier_arrivals)*100:.2f}%")

        # --- Resource Efficiency ---
        print("\n--- Resource Efficiency ---")
        # Staff Idle Rate per Role

        # Cashier Idle Rate
        total_cashier_capacity = self.num_cashiers * self.total_sim_time
        if total_cashier_capacity > 0:
             cashier_utilization = self.total_cashier_service_time / total_cashier_capacity
             cashier_idle_rate = 1.0 - cashier_utilization
             print(f"Cashier Idle Rate: {cashier_idle_rate*100:.2f}%")
        else:
             print("Cashier Idle Rate: N/A")

        # Drive Thru Ordering Idle Rate
        total_dt_capacity = self.num_dt_ordering_stations * self.total_sim_time
        if total_dt_capacity > 0:
             dt_utilization = self.total_dt_ordering_service_time / total_dt_capacity
             dt_idle_rate = 1.0 - dt_utilization
             print(f"Drive-Thru Ordering Staff Idle Rate: {dt_idle_rate*100:.2f}%")
        else:
             print("Drive-Thru Ordering Staff Idle Rate: N/A")
