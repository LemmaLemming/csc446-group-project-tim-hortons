import random

from config import ORDER_SIZE_PROBS, ITEM_TYPE_PROBS
from customers.order_item import OrderItem

class OrderGenerator:
    def __init__(self, channel_name):
        self.channel = channel_name

        # Precompute lists for sampling efficiency
        size_probs = ORDER_SIZE_PROBS[channel_name]
        item_probs = ITEM_TYPE_PROBS[channel_name]

        self.sizes   = list(size_probs.keys())
        self.size_w  = list(size_probs.values())

        self.items   = list(item_probs.keys())
        self.item_w  = list(item_probs.values())

    def generate(self):
        """Return a list of OrderItem objects."""

        # 1. Sample how many items this customer orders
        n_items = random.choices(self.sizes, weights=self.size_w)[0]

        # 2. Sample each item's category
        results = []
        for _ in range(n_items):
            item_type = random.choices(self.items, weights=self.item_w)[0]
            results.append(OrderItem(item_type))

        return results