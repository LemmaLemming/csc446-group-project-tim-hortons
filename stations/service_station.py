# --------------------------------------------------
# Service Station (Encapsulates queue state)
# --------------------------------------------------
class ServiceStation:
    """
    (Encapsulation & Inheritance - Base Class)
    Holds the state for a single-server queue.
    """
    def __init__(self, name, mu):
        self.name = name
        self.mu = mu               # Service rate
        self.server_busy = False
        self.queue = []            # Holds Customer objects
        self.num_waited = 0
        self.num_departures = 0