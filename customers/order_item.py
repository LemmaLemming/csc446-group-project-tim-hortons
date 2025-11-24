class OrderItem:
    def __init__(self, item_type):
        self.type = item_type # food | drink | espresso
        # in the future we can add:
        # self.prep_time
        # self.station
        # or whatever
    
    def __repr__(self):
        return f"OrderItem(type={self.type})"