# tim_hortons/arrival.py
import random
import math

class NHPPArrivalGenerator:
    """
    Non-Homogeneous Poisson Process Arrival Generator.
    Uses thinning algorithm.
    """
    def __init__(self, env, config):
        self.env = env
        self.config = config

        # Calculate max rate (lambda_max) for thinning
        # Max of lambda(t) is roughly Base + Peak_B + Peak_L
        # We can just sum them to be safe.
        self.lambda_max = config.ARRIVAL_BASE_RATE + config.ARRIVAL_PEAK_B_AMP + config.ARRIVAL_PEAK_L_AMP
        # Rates are per HOUR. Convert to per MINUTE.
        self.lambda_max_per_min = self.lambda_max / 60.0

    def rate_function(self, t_minutes):
        """
        Returns instantaneous rate (arrivals per minute) at time t (minutes).
        """
        t_hours = (self.config.SIM_START_HOUR * 60 + t_minutes) / 60.0

        lambda_0 = self.config.ARRIVAL_BASE_RATE
        A_b = self.config.ARRIVAL_PEAK_B_AMP
        A_l = self.config.ARRIVAL_PEAK_L_AMP
        sigma = self.config.ARRIVAL_PEAK_WIDTH

        # Peak functions
        peak_b = A_b * math.exp(-0.5 * ((t_hours - self.config.ARRIVAL_PEAK_B_TIME) / sigma)**2)
        peak_l = A_l * math.exp(-0.5 * ((t_hours - self.config.ARRIVAL_PEAK_L_TIME) / sigma)**2)

        rate_per_hour = lambda_0 + peak_b + peak_l
        return rate_per_hour / 60.0

    def generate_arrivals(self, callback):
        """
        Generates arrivals and calls 'callback' for each arrival.
        """
        t = 0.0
        while True:
            # 1. Generate candidate step from homogeneous Poisson(lambda_max)
            # Time to next event = Exponential(lambda_max)
            # random.expovariate(lambda) returns interval.
            dt = random.expovariate(self.lambda_max_per_min)
            t += dt

            if t > self.config.SIM_DURATION_HOURS * 60:
                break

            yield self.env.timeout(dt) # Wait for the interval

            # 2. Thinning: Accept with prob lambda(t) / lambda_max
            current_rate = self.rate_function(self.env.now)
            if random.random() < (current_rate / self.lambda_max_per_min):
                # Accepted
                callback()
