# config.py
# Tunable parameters for the restaurant queueing network

import math

# --------------------------------------------------
# Arrival process (single stream)
# --------------------------------------------------
def base_arrival_rate(t):
    """Example: modest diurnal bump; units: customers per hour."""
    # Simple bell curve around mid-day
    return 80 + 90 * math.exp(-((t - 12.0) / 3.0) ** 2)

ARRIVAL_RATE_FUNC = base_arrival_rate
ARRIVAL_RATE_MAX = 180.0  # envelope for thinning

# Entry routing probabilities
ENTRY_PROBS = {
    "cashier": 0.5,
    "app": 0.2,
    "order_station": 0.3,
}

# Final destination routing probabilities (from packaging)
FINAL_ROUTING_PROBS = {
    "seated": 0.35,
    "pickup": 0.40,
    "drive_thru": 0.25,
}

# Final node capacities and behavior when full
FINAL_CAPS = {
    "seated": 30,
    "pickup": 15,
    "drive_thru": 8,
}
FINAL_BALK_IF_FULL = False  # if True, customer is lost when destination full; else pack blocks

# Preparation requirements (probability an order needs each station)
PREP_PROBS = {
    "coffee_urn": 1.0,         # 1.0 means always required
    "espresso_machine": 0.5,
    "hot_food": 0.8,
}

# Station capacities (parallel servers) and coffee batch behavior
STATION_CAPACITY = {
    "espresso_machine": 2,
    "hot_food": 3,     # max concurrent hot food items
}
COFFEE_USES_PER_BREW = 40
COFFEE_REBREW_MEAN_HRS = 0.07  # ~4.2 minutes
COFFEE_REBREW_STD_HRS = 0.02   # ~1.2 minutes

# Service rates (mu: jobs per hour) per node
SERVICE_RATES = {
    # Entry nodes
    "cashier": 190.0,
    "app": 200.0,           # app confirmation
    "order_station": 170.0,

    # Kitchen entry / prep / packaging
    "kitchen_gate": 220.0,  # admission to kitchen network
    "coffee_urn": 180.0,
    "espresso_machine": 90.0,
    "hot_food": 120.0,
    "pack": 160.0,

    # Final nodes
    "seated": 60.0,         # includes bussing/turn
    "pickup": 200.0,
    "drive_thru": 160.0,
}

# Order size and item-type probabilities per channel
ORDER_SIZE_PROBS = {
    "cashier": {1: 0.45, 2: 0.30, 3: 0.20, 4: 0.05},
    "app":     {1: 0.40, 2: 0.35, 3: 0.20, 4: 0.05},
    "order_station": {1: 0.55, 2: 0.30, 3: 0.12, 4: 0.03},
}

ITEM_TYPE_PROBS = {
    "cashier": {"food": 0.55, "drink": 0.30, "espresso": 0.15},
    "app": {"food": 0.25, "drink": 0.50, "espresso": 0.25},
    "order_station": {"food": 0.45, "drink": 0.40, "espresso": 0.15},
}

# Global sim params
SIM_PARAMS = {
    "RANDOM_SEED": 42,
    "SIM_TIME_END": 16.0,    # hours
    "MAX_DEPARTURES": 2500,
}
