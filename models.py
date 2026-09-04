from dataclasses import dataclass, field
from typing import List

@dataclass
class OrderState:
    items: List[str] = field(default_factory=list)
    total: float = 0.0
    status: str = "in_progress"

