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
    price: float = 0.0

@dataclass
class Order:
    items: List[OrderItem]
    is_mobile: bool = False
    is_drive_thru: bool = False
    is_priority: bool = False
    order_time: float = 0.0
    
    pickup_slot_start: Optional[float] = None

    on_counter: bool = False
    blocked_by_counter: bool = False
    limbo_event: object = None

    @property
    def total_price(self) -> float:
        return sum(item.price for item in self.items)

@dataclass
class Customer:
    id: int
    arrival_time: float
    channel: str
    order: Optional[Order] = None
    
    start_wait_time: float = 0.0
    end_wait_time: float = 0.0
    finish_time: float = 0.0
    
    balked: bool = False
    reneged: bool = False
    sla_violated: bool = False
    
    def wait_duration(self):
        return self.end_wait_time - self.start_wait_time

    def total_system_time(self):
        return self.finish_time - self.arrival_time
