# tim_hortons/models.py
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class MenuItem:
    id: int
    name: str
    category: str
    station: str
    frequency: int
    price: Optional[float] = None
    sizes: Optional[List[dict]] = None

@dataclass
class OrderItem:
    menu_item: MenuItem
    size: Optional[str] = None
    # We can add price here if needed, but not critical for flow simulation

@dataclass
class Order:
    items: List[OrderItem]
    is_mobile: bool = False
    is_drive_thru: bool = False
    is_priority: bool = False
    order_time: float = 0.0

    # For Mobile
    pickup_slot_start: Optional[float] = None # Minutes from sim start

@dataclass
class Customer:
    id: int
    arrival_time: float
    channel: str # "cashier", "mobile", "drive_thru"
    order: Order

    # State tracking
    start_wait_time: float = 0.0
    end_wait_time: float = 0.0 # When they finished ordering/queued for pickup
    finish_time: float = 0.0   # When they got their food

    balked: bool = False
    reneged: bool = False
    sla_violated: bool = False # For mobile

    def wait_duration(self):
        return self.end_wait_time - self.start_wait_time

    def total_system_time(self):
        return self.finish_time - self.arrival_time
