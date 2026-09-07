from dataclasses import dataclass, field
from typing import List


@dataclass
class OrderItem:
    name: str
    quantity: int
    price: float

    @property
    def line_total(self) -> float:
        return round(self.quantity * self.price, 2)


@dataclass
class OrderState:
    items: List[OrderItem] = field(default_factory=list)
    total: float = 0.0
    status: str = "in_progress"

    def to_dict(self) -> dict:
        return {
            "items": [
                {"name": i.name, "quantity": i.quantity, "price": i.price, "line_total": i.line_total}
                for i in self.items
            ],
            "total": self.total,
            "status": self.status,
        }

    def pretty(self) -> str:
        if not self.items:
            return "  (empty)"
        lines = [f"  {i.quantity}x {i.name} — ${i.line_total:.2f}" for i in self.items]
        lines.append(f"  TOTAL: ${self.total:.2f}  [{self.status}]")
        return "\n".join(lines)