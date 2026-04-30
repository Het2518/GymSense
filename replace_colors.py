import os
import glob

def replace_colors(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replacements for Light Warm Theme
    replacements = {
        'teal-': 'orange-',
        'emerald-': 'rose-',
        'blue-': 'amber-'
    }

    new_content = content
    for old, new in replacements.items():
        new_content = new_content.replace(old, new)

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {filepath}")

frontend_dir = os.path.join(os.path.dirname(__file__), 'frontend', 'src')
for root, dirs, files in os.walk(frontend_dir):
    for file in files:
        if file.endswith('.jsx') or file.endswith('.js'):
            replace_colors(os.path.join(root, file))

print("Color replacement complete.")
