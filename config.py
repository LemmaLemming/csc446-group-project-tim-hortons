# config.py
# Simulation Configuration Parameters

# --- Simulation Time Settings ---
# The simulation clock is in MINUTES.
# However, arrival patterns are defined in HOURS (peaks at 8am, 12pm).
SIM_DURATION_HOURS = 16  # Run for 16 hours (e.g. 6am to 10pm)
SIM_START_HOUR = 6
RANDOM_SEED = 42

# --- Arrival Process (NHPP) ---
# Lambda(t) = Base + Ab * exp(...) + Al * exp(...)
# Rates are in Arrivals PER HOUR
ARRIVAL_BASE_RATE = 2.0       # lambda_0
ARRIVAL_PEAK_B_AMP = 15.0     # A_b (Breakfast peak amplitude)
ARRIVAL_PEAK_L_AMP = 20.0     # A_l (Lunch peak amplitude)
ARRIVAL_PEAK_WIDTH = 1.0      # sigma
ARRIVAL_PEAK_B_TIME = 8.0     # Breakfast peak time (hour of day)
ARRIVAL_PEAK_L_TIME = 12.0    # Lunch peak time (hour of day)

# --- Routing Probabilities ---
PROB_CASHIER = 0.5
PROB_MOBILE = 0.2
PROB_DRIVE_THRU = 0.3

# --- Order Logic ---
MAX_ITEMS_PER_ORDER = 5
# Probability of order size drops off exponentially.
# We will normalize weights for 1..5 items.

# --- Cashier / Dine-In Settings ---
DINE_IN_PROB = 0.4  # vs Take-out
NUM_CASHIERS = 2    # Number of servers.
CASHIER_MAX_WAIT_TIME_MINUTES = 10.0 # Time before balking in line
# Service Time (LogNormal) - Minutes
CASHIER_MEAN_TIME = 1.0 
CASHIER_STD_DEV = 0.2
# Multiplier per additional item in the order (applied to mean and std)
CASHIER_ITEM_MULTIPLIER = 0.2

# --- Mobile Order Settings ---
MOBILE_ORDER_SLOT_WINDOW_MINUTES = 15
MOBILE_ORDER_SLOT_CAPACITY = 5
MOBILE_ORDER_PREP_BUFFER_MINUTES = 7
MOBILE_ORDER_MAX_SLOT_ATTEMPTS = 2

# --- Drive-Thru Settings ---
DRIVE_THRU_NUM_ORDERING_STATIONS = 2
DRIVE_THRU_LINE_LIMIT = 12        # Max cars in line before balking
DRIVE_THRU_PRIORITY_THRESHOLD = 8 # If line > 8, new orders get priority
# Service Time (LogNormal) - Minutes
DT_ORDER_MEAN_TIME = 1.0
DT_ORDER_STD_DEV = 0.2
DT_ITEM_MULTIPLIER = 0.2

# Pickup Window Service Time (LogNormal) - Minutes
# Updated: 10 seconds = 0.1666... minutes
DT_PICKUP_MEAN_TIME = 10.0 / 60.0
DT_PICKUP_STD_DEV = 0.1 # Keeping original std dev as it wasn't specified to change, or maybe scale it?
# Let's assume the std dev scales or stays small. 0.1 min = 6s. Seems reasonable for 10s mean.

# --- Kitchen Settings ---
# Station Configuration
# Types: "simple", "coffee", "espresso"
KITCHEN_STATIONS = {
    "hot_foods": {
        "type": "simple",
        "mean": 1.0,
        "std": 0.5,
        "capacity": 2 # Assuming original capacity, user didn't specify change
    },
    "drinks": { # Beverage Station
        "type": "simple",
        "mean": 0.75,
        "std": 0.25,
        "capacity": 2 # Assuming original capacity
    },
    "espresso": {
        "type": "espresso",
        "mean": 1.0,
        "std": 0.35,
        "capacity": 1 # "The espresso machine" implies 1
    },
    "coffee": {
        "type": "coffee",
        "mean": 0.5,
        "std": 0.15,
        "capacity": 2 # "Two coffee urns" - handled by internal logic of CoffeeStation
    },
}

# Coffee Station Specifics
COFFEE_URN_CAPACITY = 12 # cups
COFFEE_URN_REFILL_TIME = 2.0 # minutes

# Espresso Station Specifics
ESPRESSO_FAILURE_T = 1.0
ESPRESSO_FAILURE_K = 1.5
ESPRESSO_REPAIR_TIME = 2.0 # minutes

# Counter / Pickup Settings
COUNTER_CAPACITY = 24 # orders
# Pickup Time Distribution (LogNormal params for underlying Normal)
# t = exp(mu + sigma * Z)
PICKUP_DIST_MU = 1.11
PICKUP_DIST_SIGMA = 1.0

# Thresholds for SLA reporting
SLA_DRIVE_THRU_WAIT_THRESHOLD = 5.0 # Minutes
