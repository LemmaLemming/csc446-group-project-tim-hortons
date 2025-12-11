# config.py
# Simulation Configuration Parameters

# --- Simulation Time Settings ---
SIM_DURATION_HOURS = 16
SIM_START_HOUR = 6
RANDOM_SEED = 42

# --- Arrival Process ---
ARRIVAL_BASE_RATE = 2.0
ARRIVAL_PEAK_B_AMP = 15.0
ARRIVAL_PEAK_L_AMP = 20.0
ARRIVAL_PEAK_WIDTH = 1.0
ARRIVAL_PEAK_B_TIME = 8.0
ARRIVAL_PEAK_L_TIME = 12.0

# --- Routing ---
PROB_CASHIER = 0.5
PROB_MOBILE = 0.2
PROB_DRIVE_THRU = 0.3

# --- Order Logic ---
MAX_ITEMS_PER_ORDER = 5

# --- Cashier ---
DINE_IN_PROB = 0.4
NUM_CASHIERS = 2
CASHIER_MAX_WAIT_TIME_MINUTES = 10.0
CASHIER_MEAN_TIME = 1.0 
CASHIER_STD_DEV = 0.2
CASHIER_ITEM_MULTIPLIER = 0.2

# --- Mobile ---
MOBILE_ORDER_SLOT_WINDOW_MINUTES = 15
MOBILE_ORDER_SLOT_CAPACITY = 5
MOBILE_ORDER_PREP_BUFFER_MINUTES = 7
MOBILE_ORDER_MAX_SLOT_ATTEMPTS = 2

# --- Drive-Thru ---
DRIVE_THRU_NUM_ORDERING_STATIONS = 2
DRIVE_THRU_LINE_LIMIT = 12
DRIVE_THRU_PRIORITY_THRESHOLD = 8
DT_ORDER_MEAN_TIME = 1.0
DT_ORDER_STD_DEV = 0.2
DT_ITEM_MULTIPLIER = 0.2

# Pickup
DT_PICKUP_MEAN_TIME = 10.0 / 60.0 # 10 seconds
DT_PICKUP_STD_DEV = 0.1

# --- Financials ---
HOURLY_WAGE = 17.85
MARGIN_COFFEE_DRINKS = 0.50
MARGIN_ESPRESSO = 0.30
MARGIN_HOT_FOODS = 0.20

# --- Kitchen Staffing & Stations ---
STATION_EMPLOYEES = {
    "hot_foods": 4,
    "drinks": 2,
    "coffee": 1,
    "espresso": 2
}

EFFICIENCY_BASE = 0.85

# Station Configuration
KITCHEN_STATIONS = {
    "hot_foods": {
        "type": "simple",
        "mean": 1.0,
        "std": 0.5,
    },
    "drinks": {
        "type": "simple",
        "mean": 0.75,
        "std": 0.25,
    },
    "espresso": {
        "type": "espresso",
        "mean": 1.0,
        "std": 0.35,
        "capacity": 1
    },
    "coffee": {
        "type": "coffee",
        "mean": 0.5,
        "std": 0.15,
        "capacity": 2
    },
}

COFFEE_URN_CAPACITY = 12
COFFEE_URN_REFILL_TIME = 2.0

ESPRESSO_FAILURE_T = 1.0
ESPRESSO_FAILURE_K = 1.5
ESPRESSO_REPAIR_TIME = 2.0

# Counter
COUNTER_CAPACITY = 24
PICKUP_DIST_MU = 1.11
PICKUP_DIST_SIGMA = 1.0

# SLA
SLA_DRIVE_THRU_WAIT_THRESHOLD = 5.0
