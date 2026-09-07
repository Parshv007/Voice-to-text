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

from groq import Groq

try:
    from .menu import find_menu_item, get_menu_text
    from .models import OrderItem, OrderState
    from .prompts import build_system_prompt, build_user_message
except ImportError:  # allows running this file directly, not just as a package
    from menu import find_menu_item, get_menu_text
    from models import OrderItem, OrderState
    from prompts import build_system_prompt, build_user_message

GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

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
# Language-aware response templates
# ---------------------------------------------------------------------

TEMPLATES = {
    "en": {
        "not_on_menu": "Sorry, {item} isn't on our menu.",
        "added": "Added {qty} {item}, now {total} total.",
        "removed_all": "Removed {item} from your order.",
        "set_qty": "Got it — {qty} {item}.",
        "removed_partial": "Removed {qty} {item}, {left} left.",
        "not_in_order": "You don't have {item} in your order.",
        "menu_intro": "Here's what we've got: {menu}",
        "total": "Your total so far is ${total:.2f}.",
        "empty_order": "Your order is empty — add something before confirming.",
        "confirmed": "Confirmed! Your total is ${total:.2f}. It'll be right up.",
        "fallback": "Sorry, I'm having trouble right now — could you repeat that?",
        "unclear": "Sorry, could you say that again?",
        "default_ok": "Okay.",
    },
    "hi": {
        "not_on_menu": "माफ़ कीजिए, {item} हमारे मेन्यू में नहीं है।",
        "added": "{qty} {item} जोड़ दिए, अब कुल {total} हो गए।",
        "removed_all": "{item} आपके ऑर्डर से हटा दिया गया।",
        "set_qty": "ठीक है — {qty} {item}।",
        "removed_partial": "{qty} {item} हटा दिए, अब {left} बचे हैं।",
        "not_in_order": "आपके ऑर्डर में {item} है ही नहीं।",
        "menu_intro": "हमारे पास ये है: {menu}",
        "total": "आपका कुल अभी तक ${total:.2f} है।",
        "empty_order": "आपका ऑर्डर खाली है — कन्फर्म करने से पहले कुछ जोड़ें।",
        "confirmed": "कन्फर्म हो गया! आपका कुल ${total:.2f} है। जल्द ही तैयार होगा।",
        "fallback": "माफ़ कीजिए, अभी थोड़ी दिक्कत हो रही है — क्या आप दोबारा बोल सकते हैं?",
        "unclear": "माफ़ कीजिए, क्या आप दोबारा बोल सकते हैं?",
        "default_ok": "ठीक है।",
    },
}


def _t(lang: str, key: str, **kwargs) -> str:
    lang = lang if lang in TEMPLATES else "en"
    return TEMPLATES[lang][key].format(**kwargs)


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


def _exec_add_item(order: OrderState, item_name: str, quantity: int, lang: str) -> str:
    menu_item = find_menu_item(item_name)
    if menu_item is None:
        return _t(lang, "not_on_menu", item=item_name)

    line = _find_line(order, menu_item["name"])
    if line:
        line.quantity += quantity
    else:
        order.items.append(
            OrderItem(name=menu_item["name"], quantity=quantity, price=menu_item["price"])
        )
    _recompute_total(order)
    new_qty = _find_line(order, menu_item["name"]).quantity
    return _t(lang, "added", qty=quantity, item=menu_item["name"], total=new_qty)


def _exec_set_item_quantity(order: OrderState, item_name: str, quantity: int, lang: str) -> str:
    menu_item = find_menu_item(item_name)
    if menu_item is None:
        return _t(lang, "not_on_menu", item=item_name)

    line = _find_line(order, menu_item["name"])
    if quantity <= 0:
        if line:
            order.items.remove(line)
        _recompute_total(order)
        return _t(lang, "removed_all", item=menu_item["name"])

    if line:
        line.quantity = quantity
    else:
        order.items.append(
            OrderItem(name=menu_item["name"], quantity=quantity, price=menu_item["price"])
        )
    _recompute_total(order)
    return _t(lang, "set_qty", qty=quantity, item=menu_item["name"])


def _exec_remove_item(order: OrderState, item_name: str, quantity: int | None, lang: str) -> str:
    menu_item = find_menu_item(item_name)
    if menu_item is None:
        return _t(lang, "not_on_menu", item=item_name)

    line = _find_line(order, menu_item["name"])
    if not line:
        return _t(lang, "not_in_order", item=menu_item["name"])

    if quantity is None or quantity >= line.quantity:
        order.items.remove(line)
        _recompute_total(order)
        return _t(lang, "removed_all", item=menu_item["name"])

    line.quantity -= quantity
    _recompute_total(order)
    return _t(lang, "removed_partial", qty=quantity, item=menu_item["name"], left=line.quantity)


def _exec_get_menu(lang: str) -> str:
    return _t(lang, "menu_intro", menu=get_menu_text().replace("\n", " "))


def _exec_get_total(order: OrderState, lang: str) -> str:
    return _t(lang, "total", total=order.total)


def _exec_confirm_order(order: OrderState, lang: str) -> str:
    if not order.items:
        return _t(lang, "empty_order")
    order.status = "confirmed"
    return _t(lang, "confirmed", total=order.total)


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------

def handle_user_utterance(
    text: str, current_order: OrderState, detected_language: str = "en"
) -> tuple[OrderState, str]:
    """
    Interpret one caller utterance against the menu and current order,
    apply the resulting changes, and return (new_order_state, spoken_reply).

    Never mutates current_order in place — operates on a deep copy so the
    caller's reference stays untouched unless they take the returned value.

    detected_language should be "en" or "hi" (falls back to "en" for
    anything else); it is passed both to the LLM (so it replies/tool-calls
    in the right language context) and used to pick the template language
    for the deterministic tool-result strings below.
    """
    order = copy.deepcopy(current_order)
    lang = detected_language if detected_language in TEMPLATES else "en"
    client = _get_client()

    messages = [
        {"role": "system", "content": build_system_prompt()},
        {
            "role": "user",
            "content": build_user_message(
                json.dumps(order.to_dict()), text, lang
            ),
        },
    ]

    # Wrap the Groq call so a dependency failure (timeout, rate limit,
    # outage) degrades gracefully instead of crashing the turn.
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.2,
        )
    except Exception:
        return order, _t(lang, "fallback")

    message = response.choices[0].message
    tool_calls = getattr(message, "tool_calls", None)

    if not tool_calls:
        # No order change — plain-text reply (chit-chat, clarifying question).
        # This comes straight from the model, which we've instructed (via
        # build_user_message) to answer in the detected language already.
        reply = (message.content or _t(lang, "unclear")).strip()
        return order, reply

    action_descriptions = []
    for call in tool_calls:
        name = call.function.name
        try:
            args = json.loads(call.function.arguments or "{}")
        except json.JSONDecodeError:
            args = {}

        if name == "add_item":
            desc = _exec_add_item(
                order, args.get("item_name", ""), int(args.get("quantity", 1)), lang
            )
        elif name == "set_item_quantity":
            desc = _exec_set_item_quantity(
                order, args.get("item_name", ""), int(args.get("quantity", 0)), lang
            )
        elif name == "remove_item":
            qty = args.get("quantity")
            desc = _exec_remove_item(
                order, args.get("item_name", ""), int(qty) if qty is not None else None, lang
            )
        elif name == "get_menu":
            desc = _exec_get_menu(lang)
        elif name == "get_total":
            desc = _exec_get_total(order, lang)
        elif name == "confirm_order":
            desc = _exec_confirm_order(order, lang)
        else:
            desc = ""  # unknown tool name — ignore rather than crash the call

        if desc:
            action_descriptions.append(desc)

    reply = " ".join(action_descriptions) if action_descriptions else _t(lang, "default_ok")
    return order, reply