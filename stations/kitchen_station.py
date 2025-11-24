from stations.service_station import ServiceStation


class KitchenStation(ServiceStation):
    """
    (Inheritance - Child Class)
    A simple ServiceStation for the kitchen.
    """
    def __init__(self, name, mu):
        super().__init__(name, mu)
        # Inherits all state from ServiceStation