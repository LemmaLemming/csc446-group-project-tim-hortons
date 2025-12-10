# config.py

import math

# --------------------------------------------------
# Arrival process (single stream)
# --------------------------------------------------
def base_arrival_rate(t):
    """
    Time-varying arrival rate λ(t) in customers/hour.
    t is simulation time in hours since opening.

    Shape:
    - Baseline traffic
    - Breakfast peak (~8:30–9:00)
    - Lunch peak (~12:30–13:00)
    - Smaller late-afternoon bump (~17:30)
    """
    baseline = 45.0

    morning_peak = 120.0 * math.exp(-((t - 2.5) / 1.2) ** 2)
    lunch_peak   = 170.0 * math.exp(-((t - 6.5) / 1.4) ** 2)
    late_peak    = 60.0  * math.exp(-((t - 11.5) / 1.8) ** 2)

    return baseline + morning_peak + lunch_peak + late_peak

ARRIVAL_RATE_FUNC = base_arrival_rate
ARRIVAL_RATE_MAX = 230.0  # envelope for thinning


# --------------------------------------------------
# Entry routing probabilities (from global arrival stream)
# --------------------------------------------------
ENTRY_PROBS = {
    "cashier":       0.45,
    "app":           0.25,
    "order_station": 0.30,
}

# --------------------------------------------------
# Final destination routing probabilities
# --------------------------------------------------
FINAL_ROUTING_PROBS = {
    "seated":     0.30,
    "pickup":     0.45,
    "drive_thru": 0.25,
}

FINAL_CAPS = {
    "seated":     32,
    "pickup":     20,
    "drive_thru": 10,
}

FINAL_BALK_IF_FULL = True  # customers lost if destination full


# --------------------------------------------------
# Preparation requirements
# --------------------------------------------------
PREP_PROBS = {
    "coffee_urn":       0.75,
    "espresso_machine": 0.25,
    "hot_food":         0.55,
}

# --------------------------------------------------
# Kitchen station capacities & coffee behavior
# --------------------------------------------------
STATION_CAPACITY = {
    "espresso_machine": 1,
    "hot_food":         2,
}

COFFEE_USES_PER_BREW = 32
COFFEE_REBREW_MEAN_HRS = 0.05   # ~3 minutes
COFFEE_REBREW_STD_HRS  = 0.015  # ~0.9 minutes


# --------------------------------------------------
# Service rates (mu: jobs/hour)
# --------------------------------------------------
SERVICE_RATES = {
    "cashier":         110.0,  # ~33 s
    "app":             400.0,
    "order_station":   110.0,

    "kitchen_gate":    300.0,
    "coffee_urn":      160.0,  # ~22.5 s
    "espresso_machine": 80.0,  # ~45 s
    "hot_food":         70.0,  # ~51 s
    "pack":            130.0,  # ~28 s

    "seated":           4.0,   # ~15 min turnover
    "pickup":          300.0,
    "drive_thru":      220.0,
}

# --------------------------------------------------
# Server capacities per queueing node
# --------------------------------------------------
SERVER_CAPACITY = {
    "cashier":       1,
    "app":           1,
    "order_station": 1,
    "kitchen_gate":  1,
    "pack":          1,

    "seated":        FINAL_CAPS["seated"],
    "pickup":        FINAL_CAPS["pickup"],
    "drive_thru":    FINAL_CAPS["drive_thru"],
}


# --------------------------------------------------
# Order size and item-type probabilities
# --------------------------------------------------
ORDER_SIZE_PROBS = {
    "cashier": {
        1: 0.40, 2: 0.35, 3: 0.20, 4: 0.05
    },
    "app": {
        1: 0.35, 2: 0.35, 3: 0.20, 4: 0.10
    },
    "order_station": {
        1: 0.50, 2: 0.30, 3: 0.15, 4: 0.05
    },
}

ITEM_TYPE_PROBS = {
    "cashier":       {"food": 0.50, "drink": 0.35, "espresso": 0.15},
    "app":           {"food": 0.30, "drink": 0.45, "espresso": 0.25},
    "order_station": {"food": 0.45, "drink": 0.35, "espresso": 0.20},
}


# --------------------------------------------------
# Global simulation parameters
# --------------------------------------------------
SIM_PARAMS = {
    "RANDOM_SEED":     12345,
    "SIM_TIME_END":    16.0,   # hours
    "MAX_DEPARTURES":  4000,
}


# --------------------------------------------------
# Financial parameters
# --------------------------------------------------
# Revenue model
REVENUE_PER_ORDER = 8.0  # dollars per completed customer

# Labor cost per staffed station per hour
# These stations incur cost if modeled as "staffed servers".
STAFF_COST_PER_HOUR = {
    "cashier":          15.0,  # human cashier
    "app":               0.0,  # no labor cost
    "order_station":     0.0,  # drive-thru order speaker is not labor
    "kitchen_gate":      0.0,  # routing is not labor
    "coffee_urn":       14.0,  # brewed coffee prep employee
    "espresso_machine": 15.0,  # barista
    "hot_food":         15.0,  # cook
    "pack":             15.0,  # packer / assembler
}
