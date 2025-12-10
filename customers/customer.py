from customers.order_generator import OrderGenerator

# --------------------------------------------------
# Customer Object (Encapsulates customer state)
# --------------------------------------------------
class Customer:
    """Encapsulates the state of a single customer."""
    def __init__(self, cid, channel_name):
        self.id = cid
        self.channel_name = channel_name # drive_thru | mobile_order | cashier
        self.stage = "ordering"          # ordering | pickup
        self.order_items = OrderGenerator(channel_name).generate() # list of OrderItems
        self.outstanding_items = len(self.order_items)
        self.destination = None          # shelf | seating | window (drive-thru)
        self.arrival_time = 0.0
        self.depart_time = None
