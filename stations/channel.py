from stations.service_station import ServiceStation

class Channel(ServiceStation):
    """
    (Inheritance - Child Class)
    A ServiceStation that also has an ArrivalGenerator
    and tracks final system departures.
    """
    def __init__(self, name, mu, arrival_generator):
        super().__init__(name, mu)
        self.arrival_gen = arrival_generator
        self.num_system_departures = 0 # Final exits