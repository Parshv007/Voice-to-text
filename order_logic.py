"""
Core order-logic layer.

handle_user_utterance(text, current_order) -> (new_order_state, spoken_response)

This is the single entry point the voice pipeline calls. It is stateless
between calls: the caller (teammate's pipeline) is responsible for holding
onto the OrderState and passing it back in on the next turn.
"""

import copy
import json
import os

GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

from groq import Groq

try:
    from .menu import find_menu_item, get_menu_text
    from .models import OrderItem, OrderState
    from .prompts import build_system_prompt, build_user_message
except ImportError:  # allows running this file directly, not just as a package
    from menu import find_menu_item, get_menu_text
    from models import OrderItem, OrderState
    from prompts import build_system_prompt, build_user_message

GROQ_MODEL = "openai/gpt-oss-120b"

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        # Reads GROQ_API_KEY from the environment automatically.
        _client = Groq()
    return _client


# ---------------------------------------------------------------------
# Tool schemas (OpenAI-compatible function-calling format, which Groq's
# client mirrors exactly).
# ---------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_item",
            "description": (
                "Add an item to the order, or increase its quantity if it's "
                "already in the order (e.g. 'add another fries'). Do NOT use "
                "this for corrections that replace a quantity — use "
                "set_item_quantity for that."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "item_name": {
                        "type": "string",
                        "description": "Menu item name, as close to the menu wording as possible.",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Number of this item to add.",
                        "minimum": 1,
                    },
                },
                "required": ["item_name", "quantity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_item_quantity",
            "description": (
                "Set the exact quantity of an item, replacing whatever it was "
                "before. Use this whenever the caller corrects or restates a "
                "quantity, e.g. 'actually make that two', 'no just one', "
                "'change it to three'. Quantity 0 removes the item."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "item_name": {"type": "string"},
                    "quantity": {"type": "integer", "minimum": 0},
                },
                "required": ["item_name", "quantity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_item",
            "description": (
                "Remove an item from the order entirely, or decrease it by a "
                "specific amount if the caller frames it as 'remove'/'take off'. "
                "Omit quantity to remove the item completely."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "item_name": {"type": "string"},
                    "quantity": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Optional — amount to remove. If omitted, removes all of it.",
                    },
                },
                "required": ["item_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_menu",
            "description": "Use when the caller explicitly asks what's available or for recommendations.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_total",
            "description": "Use when the caller asks for the running total or 'how much so far'.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_order",
            "description": "Use only when the caller clearly wants to finalize the order.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


# ---------------------------------------------------------------------
# Tool execution — pure functions over OrderState, no LLM involved.
# Each returns a short human-readable description of what happened,
# which is used to template the spoken response.
# ---------------------------------------------------------------------

def _recompute_total(order: OrderState) -> None:
    order.total = round(sum(i.line_total for i in order.items), 2)


def _find_line(order: OrderState, item_name: str) -> OrderItem | None:
    for line in order.items:
        if line.name.lower() == item_name.lower():
            return line
    return None


def _exec_add_item(order: OrderState, item_name: str, quantity: int) -> str:
    menu_item = find_menu_item(item_name)
    if menu_item is None:
        return f"Sorry, {item_name} isn't on our menu."

    line = _find_line(order, menu_item["name"])
    if line:
        line.quantity += quantity
    else:
        order.items.append(
            OrderItem(name=menu_item["name"], quantity=quantity, price=menu_item["price"])
        )
    _recompute_total(order)
    new_qty = _find_line(order, menu_item["name"]).quantity
    return f"Added {quantity} {menu_item['name']} (now {new_qty} total)."


def _exec_set_item_quantity(order: OrderState, item_name: str, quantity: int) -> str:
    menu_item = find_menu_item(item_name)
    if menu_item is None:
        return f"Sorry, {item_name} isn't on our menu."

    line = _find_line(order, menu_item["name"])
    if quantity <= 0:
        if line:
            order.items.remove(line)
        _recompute_total(order)
        return f"Removed {menu_item['name']} from your order."

    if line:
        line.quantity = quantity
    else:
        order.items.append(
            OrderItem(name=menu_item["name"], quantity=quantity, price=menu_item["price"])
        )
    _recompute_total(order)
    return f"Got it — {quantity} {menu_item['name']}."


def _exec_remove_item(order: OrderState, item_name: str, quantity: int | None) -> str:
    menu_item = find_menu_item(item_name)
    if menu_item is None:
        return f"Sorry, {item_name} isn't on our menu."

    line = _find_line(order, menu_item["name"])
    if not line:
        return f"You don't have {menu_item['name']} in your order."

    if quantity is None or quantity >= line.quantity:
        order.items.remove(line)
        _recompute_total(order)
        return f"Removed {menu_item['name']} from your order."

    line.quantity -= quantity
    _recompute_total(order)
    return f"Removed {quantity} {menu_item['name']} (now {line.quantity} left)."


def _exec_get_menu() -> str:
    return "Here's what we've got: " + get_menu_text().replace("\n", " ")


def _exec_get_total(order: OrderState) -> str:
    return f"Your total so far is ${order.total:.2f}."


def _exec_confirm_order(order: OrderState) -> str:
    if not order.items:
        return "Your order is empty — add something before confirming."
    order.status = "confirmed"
    return f"Confirmed! Your total is ${order.total:.2f}. It'll be right up."


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------

def handle_user_utterance(text: str, current_order: OrderState) -> tuple[OrderState, str]:
    """
    Interpret one caller utterance against the menu and current order,
    apply the resulting changes, and return (new_order_state, spoken_reply).

    Never mutates current_order in place — operates on a deep copy so the
    caller's reference stays untouched unless they take the returned value.
    """
    order = copy.deepcopy(current_order)
    client = _get_client()

    messages = [
        {"role": "system", "content": build_system_prompt()},
        {
            "role": "user",
            "content": build_user_message(json.dumps(order.to_dict()), text),
        },
    ]

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        temperature=0.2,
    )

    message = response.choices[0].message
    tool_calls = getattr(message, "tool_calls", None)

    if not tool_calls:
        # No order change — plain-text reply (chit-chat, clarifying question).
        reply = (message.content or "Sorry, could you say that again?").strip()
        return order, reply

    action_descriptions = []
    for call in tool_calls:
        name = call.function.name
        try:
            args = json.loads(call.function.arguments or "{}")
        except json.JSONDecodeError:
            args = {}

        if name == "add_item":
            desc = _exec_add_item(order, args.get("item_name", ""), int(args.get("quantity", 1)))
        elif name == "set_item_quantity":
            desc = _exec_set_item_quantity(
                order, args.get("item_name", ""), int(args.get("quantity", 0))
            )
        elif name == "remove_item":
            qty = args.get("quantity")
            desc = _exec_remove_item(order, args.get("item_name", ""), int(qty) if qty is not None else None)
        elif name == "get_menu":
            desc = _exec_get_menu()
        elif name == "get_total":
            desc = _exec_get_total(order)
        elif name == "confirm_order":
            desc = _exec_confirm_order(order)
        else:
            desc = ""  # unknown tool name — ignore rather than crash the call

        if desc:
            action_descriptions.append(desc)

    reply = " ".join(action_descriptions) if action_descriptions else "Okay."
    return order, reply
