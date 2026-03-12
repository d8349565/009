"""
临时修复脚本：清除 agents.py 中残留的 Unicode 弯引号（Python语法错误）
运行方式（在 worktree 目录）：python fix_agents.py
"""
path = 'agents.py'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 删除所有残留的 Unicode 弯引号（U+201C U+201D）
import unicodedata
before = len(content)
# 方法一：直接删除 Unicode 弯引号
content = content.replace('\u201c', '').replace('\u201d', '')
# 方法二：删除单独一行只有弯引号的行
import re
content = re.sub(r'\n\s*[\u201c\u201d]+\s*\n', '\n', content)
after = len(content)
print(f"删除了 {before - after} 个字符")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

import ast
with open(path, 'r', encoding='utf-8') as f:
    src = f.read()
try:
    ast.parse(src)
    print("✓ agents.py 语法检查通过")
except SyntaxError as e:
    print(f"✗ 仍有语法错误: {e}")
