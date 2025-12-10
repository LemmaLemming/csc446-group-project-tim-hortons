class OrderItem:
    def __init__(self, item_type):
        self.type = item_type # food | drink | espresso
        self.ready = False
    
    def __repr__(self):
        return f"OrderItem(type={self.type})"
