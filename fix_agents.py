"""
临时修复脚本：删除 agents.py 中第667行的孤立字符（Python语法错误）
运行方式：python fix_agents.py
"""
import re

path = 'agents.py'

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"总行数: {len(lines)}")

# 找到并删除第667行（或任何类似内容的孤立行）
# 孤立行特征：非缩进（不以空格开头）且只包含引号/特殊符号字符，不是合法Python代码
new_lines = []
removed_count = 0
for i, line in enumerate(lines):
    stripped = line.strip()
    # 检测无缩进的非法表达式行（以数字或非ASCII非字母字符开头）
    if not line.startswith(' ') and not line.startswith('\t') and not line.startswith('#') and stripped:
        # 检查是否是函数/类定义或其他合法顶级结构
        valid_starts = ('def ', 'class ', 'import ', 'from ', '@', '#', 'if ', 'for ', 'while ', 
                        'try:', 'except', 'finally:', 'with ', 'return ', 'raise ', 'pass', 'break',
                        'continue', 'yield ', 'async ', 'elif ', 'else:')
        is_valid = any(stripped.startswith(v) for v in valid_starts)
        # Also valid if it's all ASCII (could be a number, name, etc.)
        is_all_ascii = all(ord(c) < 128 for c in stripped)
        if not is_valid and not is_all_ascii:
            print(f"  删除第 {i+1} 行: {repr(line[:80])}")
            removed_count += 1
            continue
    new_lines.append(line)

print(f"已删除 {removed_count} 行")

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("修复完成！")

# 验证文件可以被Python解析
import ast
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
try:
    ast.parse(content)
    print("✓ agents.py 语法检查通过")
except SyntaxError as e:
    print(f"✗ 仍有语法错误: {e}")
