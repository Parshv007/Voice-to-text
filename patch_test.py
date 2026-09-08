with open('test_order_logic.py') as f:
    content = f.read()

content = content.replace(
    '"Hi, can I get a classic cheeseburger?",',
    '"Hi, can I get a classic cheeseburger and a large fries?",'
)

with open('test_order_logic.py', 'w') as f:
    f.write(content)

print('patched')