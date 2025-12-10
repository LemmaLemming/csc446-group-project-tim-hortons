# --------------------------------------------------
# Service Station (Encapsulates queue state)
# --------------------------------------------------
class ServiceStation:
    """
    (Encapsulation & Inheritance - Base Class)
    Holds the state for a single- or multi-server queue.
    """
    def __init__(self, name, mu, capacity=1):
        self.name = name
        self.mu = mu               # Service rate
        self.capacity = max(1, capacity)
        self.server_busy = False
        self.busy_count = 0
        self.queue = []            # Holds tuples (payload, queued_time, *extras)
        self.num_waited = 0
        self.num_departures = 0
        self.total_wait_time = 0.0
        self.total_service_time = 0.0
        self.busy_time = 0.0
