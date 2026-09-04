"""
Static menu for the food-ordering agent.

Each item: name, price (float, USD), description (short — this may get
read aloud, so keep it speakable).
"""

from typing import Optional, TypedDict


class MenuItem(TypedDict):
    name: str
    price: float
    description: str


MENU: list[MenuItem] = [
    {
        "name": "Classic Cheeseburger",
        "price": 8.99,
        "description": "Beef patty, cheddar, lettuce, tomato, house sauce",
    },
    {
        "name": "Bacon Burger",
        "price": 10.49,
        "description": "Beef patty, bacon, cheddar, caramelized onions",
    },
    {
        "name": "Veggie Burger",
        "price": 8.49,
        "description": "Black bean patty, avocado, lettuce, chipotle mayo",
    },
    {
        "name": "Crispy Chicken Tenders",
        "price": 7.99,
        "description": "Four tenders, choice of dipping sauce",
    },
    {
        "name": "Margherita Pizza Slice",
        "price": 4.99,
        "description": "Tomato, fresh mozzarella, basil",
    },
    {
        "name": "Caesar Salad",
        "price": 6.99,
        "description": "Romaine, parmesan, croutons, caesar dressing",
    },
    {
        "name": "French Fries",
        "price": 3.49,
        "description": "Crispy fries, salted",
    },
    {
        "name": "Onion Rings",
        "price": 3.99,
        "description": "Beer-battered, served with ranch",
    },
    {
        "name": "Chocolate Milkshake",
        "price": 4.49,
        "description": "Classic hand-spun shake",
    },
    {
        "name": "Fountain Soda",
        "price": 1.99,
        "description": "Free refills, ask your server",
    },
]


def find_menu_item(name: str) -> Optional[MenuItem]:
    """
    Fuzzy-match a spoken/LLM-interpreted item name against the menu.

    Tries, in order: exact case-insensitive match, then substring match
    in either direction. Returns None if nothing reasonable is found —
    callers must handle that (tell the caller it's not on the menu,
    don't silently guess).
    """
    if not name:
        return None

    needle = name.strip().lower()

    # 1. exact match
    for item in MENU:
        if item["name"].lower() == needle:
            return item

    # 2. substring match (either direction) — e.g. "burger" -> first
    #    burger-ish item, "classic cheeseburger with bacon" -> still
    #    matches "Classic Cheeseburger"
    for item in MENU:
        item_name = item["name"].lower()
        if needle in item_name or item_name in needle:
            return item

    return None


def get_menu_text() -> str:
    """Human-readable menu listing, used both in the system prompt and
    when the caller explicitly asks 'what do you have'."""
    lines = []
    for item in MENU:
        lines.append(f"- {item['name']} (${item['price']:.2f}): {item['description']}")
    return "\n".join(lines)
