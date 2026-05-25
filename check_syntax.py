import ast
import sys

with open('key_generator_bot.py', 'r') as f:
    source = f.read()

try:
    ast.parse(source)
    print("Sintaxe OK")
except SyntaxError as e:
    print(f"Erro de sintaxe: {e}")
    sys.exit(1)
