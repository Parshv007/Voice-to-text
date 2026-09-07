"""
Standalone test — no voice pipeline required.

Feeds a scripted sequence of fake transcripts through handle_user_utterance,
printing the resulting OrderState after every turn. Requires GROQ_API_KEY
to be set (via .env or the environment) since it calls the real Groq API.

Run: python test_order_logic.py
"""

from dotenv import load_dotenv

load_dotenv()

try:
    from .models import OrderState
    from .order_logic import handle_user_utterance
except ImportError:  # allows running this file directly, not just as a package
    from models import OrderState
    from order_logic import handle_user_utterance

# Scripted "call" — turn 3 is the correction case: the caller already has
# one burger in the order and corrects it to two, in the same breath as
# confirming they don't want a duplicate line item.
TRANSCRIPT = [
    "Hi, can I get a classic cheeseburger?",
    "And a large fries, please.",
    "Actually, make that two cheeseburgers, not one.",
    "What's my total so far?",
    "Take off the fries.",
    "Also give me a chocolate milkshake.",
    "That's everything, go ahead and confirm it.",
<<<<<<< HEAD
    "Can I get a cheeseburger, a fries, and a chocolate milkshake?",
    "Add one more fries.",
    "Can I get a cheeseburger and a pizza calzone?",
]

=======
]


>>>>>>> 7043dd02d1037cb4fc85f75e666be62c8b33b06a
def run():
    order = OrderState()

    for turn_num, utterance in enumerate(TRANSCRIPT, start=1):
        print(f"\n{'=' * 60}")
        print(f"Turn {turn_num} — Caller: \"{utterance}\"")
        print("-" * 60)

        order, reply = handle_user_utterance(utterance, order)

        print(f"Agent says: {reply}")
        print("\nOrder state:")
        print(order.pretty())

    print(f"\n{'=' * 60}")
    print("Final order state (dict):")
    print(order.to_dict())


if __name__ == "__main__":
    run()
