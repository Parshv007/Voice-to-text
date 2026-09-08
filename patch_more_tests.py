with open('test_order_logic.py', encoding='utf-8') as f:
    content = f.read()

old = '''TRANSCRIPT = [
    "Hi, can I get a classic cheeseburger?",
    "And a large fries, please.",
    "Actually, make that two cheeseburgers, not one.",
    "What's my total so far?",
    "Take off the fries.",
    "Also give me a chocolate milkshake.",
    "That's everything, go ahead and confirm it.",
]'''

new = '''TRANSCRIPT = [
    "Hi, can I get a classic cheeseburger?",
    "And a large fries, please.",
    "Actually, make that two cheeseburgers, not one.",
    "What's my total so far?",
    "Take off the fries.",
    "Also give me a chocolate milkshake.",
    "That's everything, go ahead and confirm it.",
    "Can I get a cheeseburger, a fries, and a chocolate milkshake?",
    "Add one more fries.",
    "Can I get a cheeseburger and a pizza calzone?",
]'''

if old not in content:
    print("WARNING: TRANSCRIPT block not found as expected — no change made")
else:
    content = content.replace(old, new)
    with open('test_order_logic.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("test_order_logic.py patched with 3 extra turns")