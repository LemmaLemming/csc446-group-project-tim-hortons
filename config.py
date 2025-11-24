# config.py
# --- All tunable parameters and rate logic live here ---

import math

# --------------------------------------------------
# Arrival Rate Functions & Helpers
# --------------------------------------------------
DAY = 24.0

def bell(t, center, width):
    """Smooth bump (approx Gaussian), max = 1 at 'center'."""
    x = (t - center) / width
    return math.exp(-x * x)

def wrap_day(t):
    return t % DAY

# --- High-volume rates to total ~2200 customers over 16 hours ---
def rate_drive_thru(t):
    t = wrap_day(t)
    base = 11.3
    breakfast_peak = 143.8 * bell(t, center=8.0,  width=1.5)
    lunch_peak     = 129.4 * bell(t, center=13.0, width=1.5)
    return base + breakfast_peak + lunch_peak

def rate_mobile_order(t):
    t = wrap_day(t)
    base = 8.5
    breakfast_peak = 115.0 * bell(t, center=8.0,  width=1.5)
    lunch_peak     = 100.7 * bell(t, center=13.0, width=1.5)
    return base + breakfast_peak + lunch_peak

def rate_cashier(t):
    t = wrap_day(t)
    base = 7.7
    end_of_day_peak = 172.6 * bell(t, center=15.0, width=1.5) 
    return base + end_of_day_peak

# --------------------------------------------------
# --- MASTER CONFIGURATION DICTIONARIES ---
# --------------------------------------------------

# 1. Arrival Config: Maps channel name to its (rate_function, rate_max)
ARRIVAL_CONFIG = {
    "drive_thru": (rate_drive_thru, 160.0), # Peak λ ≈ 160
    "mobile_order": (rate_mobile_order, 125.0), # Peak λ ≈ 125
    "cashier": (rate_cashier, 185.0), # Peak λ ≈ 185
}

# 2. Service Rates (mu): Maps station name to its service rate (customers/hr)
#    --- UPDATED TO HANDLE HIGH-VOLUME ARRIVALS ---
SERVICE_RATES = {
    # Channels (Set μ > Peak λ)
    "drive_thru": 170.0,  # μ (170) > λ (160)
    "mobile_order": 130.0,  # μ (130) > λ (125)
    "cashier": 190.0,  # μ (190) > λ (185)
    
    # Kitchen (μ > Peak λ_kitchen)
    # Peak kitchen load is ~235 arrivals/hr per station
    "drinks": 240.0,  # μ (240) > λ (235)
    "food": 240.0,  # μ (240) > λ (235)
}

# 3. Routing Probabilities: Defines logic for customer flow
ROUTING_PROBS = {
    "DRINK_PROB": 0.5  # P(customer order routes to 'drinks')
}

# 4. Global Sim Params
SIM_PARAMS = {
    "RANDOM_SEED": 42,
    "SIM_TIME_END": 16.0,  # 16-hour operating day
    "MAX_DEPARTURES": 2500, # Set higher than total arrivals
}

# --------------------------------------------
# Order Size Distributions (per customer)
# --------------------------------------------
# Probabilities for the NUMBER OF ITEMS in an order
ORDER_SIZE_PROBS = {
    "drive_thru": {
        1: 0.55,
        2: 0.30,
        3: 0.12,
        4: 0.03,
    },
    "mobile_order": {
        1: 0.40,
        2: 0.35,
        3: 0.20,
        4: 0.05,
    },
    "cashier": {
        1: 0.45,
        2: 0.30,
        3: 0.20,
        4: 0.05,
    }
}

# -----------------------------------------
# Order Type Distributions by Channel
# -----------------------------------------
# Probability of each *item type* each time we generate an item
ITEM_TYPE_PROBS = {
    "drive_thru": {
        "food":    0.45,
        "drink":   0.40,
        "espresso":0.15,
    },
    "mobile_order": {
        "food":     0.25,
        "drink":    0.50,
        "espresso": 0.25,
    },
    "cashier": {
        "food":     0.55,
        "drink":    0.30,
        "espresso": 0.15,
    }
}