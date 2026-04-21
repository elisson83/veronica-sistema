with open("app.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Remove primeira linha se for 'python' ou ```python
if lines[0].strip() in ["python", "```python", "```"]:
    lines = lines[1:]

# Remove ultima linha se for ```
if lines[-1].strip() == "```":
    lines = lines[:-1]

with open("app.py", "w", encoding="utf-8") as f:
    f.writelines(lines)

print("Corrigido!")