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
# e.g. weights = [1, 0.5, 0.25, 0.125, 0.0625]

# --- Cashier / Dine-In Settings ---
DINE_IN_PROB = 0.4  # vs Take-out
NUM_CASHIERS = 2    # Number of servers. "number of cashiers will double the queuing..."
CASHIER_MAX_WAIT_TIME_MINUTES = 10.0 # Time before balking in line
# Service Time (LogNormal) - Minutes
CASHIER_MEAN_TIME = 1.0
CASHIER_STD_DEV = 0.2
# Multiplier per additional item in the order (applied to mean and std)
CASHIER_ITEM_MULTIPLIER = 0.2 # e.g. add 20% time per extra item

# --- Mobile Order Settings ---
MOBILE_ORDER_SLOT_WINDOW_MINUTES = 15
MOBILE_ORDER_SLOT_CAPACITY = 5
MOBILE_ORDER_PREP_BUFFER_MINUTES = 7
MOBILE_ORDER_MAX_SLOT_ATTEMPTS = 2 # Try chosen slot, then next, then next (Total 3 tries? or "try to book the slot after... twice" -> slot, slot+1, slot+2?)
# Prompt says: "if customers cannot book the same slot they will try to book the slot after. they will do this twice until they give up."
# So: Try Preferred. Fail? Try Pref+1. Fail? Try Pref+2. Fail? Give up.

# --- Drive-Thru Settings ---
DRIVE_THRU_NUM_ORDERING_STATIONS = 2
DRIVE_THRU_LINE_LIMIT = 12        # Max cars in line before balking
DRIVE_THRU_PRIORITY_THRESHOLD = 8 # If line > 8, new orders get priority
# Service Time (LogNormal) - Minutes
DT_ORDER_MEAN_TIME = 1.0
DT_ORDER_STD_DEV = 0.2
DT_ITEM_MULTIPLIER = 0.2

# Pickup Window Service Time (LogNormal) - Minutes
DT_PICKUP_MEAN_TIME = 0.5
DT_PICKUP_STD_DEV = 0.1

# --- Kitchen Settings (Black Box) ---
# Service times for kitchen stations (LogNormal)
# These are per ITEM.
KITCHEN_STATIONS = {
    "hot_foods": {"mean": 2.0, "std": 0.5, "capacity": 2},
    "drinks":    {"mean": 1.0, "std": 0.2, "capacity": 2},
    "espresso":  {"mean": 1.5, "std": 0.3, "capacity": 1},
    "coffee":    {"mean": 0.5, "std": 0.1, "capacity": 2},
}

# Thresholds for SLA reporting
SLA_DRIVE_THRU_WAIT_THRESHOLD = 5.0 # Minutes (for 90th percentile check)
