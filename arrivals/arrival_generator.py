import random

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