# 🎯 Agent配置快速指南

## 📍 配置文件位置

所有Agent的模型配置**集中在一个文件中**：

```
📁 009/
  └── 📄 agent_config.py  👈 所有Agent配置都在这里！
```

---

## 🚀 快速切换配置方案

### 方法1：修改预设方案（推荐）⭐

**步骤**：
1. 打开 `agent_config.py` 文件
2. 找到第 17-32 行的配置方案选择
3. 取消注释你想要的方案

**示例**：

```python
# 经济型（当前激活）
AGENT_CONFIG_PRESET = "economy"  # ✓ 激活

# 混合型（推荐）
# AGENT_CONFIG_PRESET = "balanced"  # 取消注释激活

# 高端型
# AGENT_CONFIG_PRESET = "premium"

# 自定义
# AGENT_CONFIG_PRESET = "custom"
```

**保存后立即生效！**

---

### 方法2：通过 .env 文件

**优先级更高**，会覆盖 `agent_config.py` 的配置

在 `.env` 文件中添加：

```env
# 只配置你想覆盖的Agent
REQUIREMENT_ANALYZER_PROVIDER=glm
REPORT_WRITER_PROVIDER=openrouter
```

---

## 📊 配置方案对比

### 方案A：经济型（默认）

```python
AGENT_CONFIG_PRESET = "economy"
```

| Agent | 供应商 | 模型 | 成本 |
|-------|--------|------|------|
| 需求分析师 | DeepSeek | chat | ¥0.1 |
| 信息收集员 | DeepSeek | chat | ¥2.0 |
| 报告撰写员 | DeepSeek | reasoner | ¥4.0 |
| 质量评审员 | DeepSeek | chat | ¥0.3 |

**总成本**: ¥3-6 / 100次  
**适合**: 个人用户、日常使用

---

### 方案B：混合型（推荐）⭐

```python
AGENT_CONFIG_PRESET = "balanced"
```

| Agent | 供应商 | 模型 | 成本 |
|-------|--------|------|------|
| 需求分析师 | GLM | flash | ¥0.05 |
| 信息收集员 | DeepSeek | chat | ¥2.0 |
| 报告撰写员 | DeepSeek | reasoner | ¥4.0 |
| 质量评审员 | GLM | flash | ¥0.15 |

**总成本**: ¥6-10 / 100次  
**适合**: 商业用户、中文报告  
**优势**: GLM中文理解好，DeepSeek推理强

---

### 方案C：高端型

```python
AGENT_CONFIG_PRESET = "premium"
```

| Agent | 供应商 | 模型 | 成本 |
|-------|--------|------|------|
| 需求分析师 | GLM | plus | ¥1.5 |
| 信息收集员 | DeepSeek | chat | ¥2.0 |
| 报告撰写员 | OpenRouter | Claude 3.5 | ¥20 |
| 质量评审员 | GLM | plus | ¥1.0 |

**总成本**: ¥20-50 / 100次  
**适合**: 关键报告、最高质量  
**优势**: Claude写作顶级，O1推理最强

---

### 方案D：自定义

```python
AGENT_CONFIG_PRESET = "custom"
```

编辑 `agent_config.py` 中的 `AGENT_CONFIG_CUSTOM` 字典，自由组合。

---

## 🔍 查看当前配置

随时查看当前使用的配置：

```bash
python agent_config.py
```

输出示例：
```
🎨 Agent模型配置管理器

当前Agent配置方案: ECONOMY
======================================================================
🤖 Requirement Analyzer
   供应商: DEEPSEEK
   模型: default
   推理模式: ✗
   说明: 快速分析用户需求
...
```

---

## ⚙️ 配置优先级

```
环境变量 (.env)       最高优先级 ⭐⭐⭐
    ↓
agent_config.py      推荐使用 ⭐⭐
    ↓
config.py 默认值     兜底配置 ⭐
```

**建议**：
- 日常使用：修改 `agent_config.py` 的预设方案
- 临时测试：使用 `.env` 覆盖个别Agent
- 不要修改：`config.py`（自动读取上面两个）

---

## 💡 实用技巧

### 技巧1：快速测试不同方案

```bash
# 1. 编辑 agent_config.py，改为 balanced
AGENT_CONFIG_PRESET = "balanced"

# 2. 查看配置
python agent_config.py

# 3. 运行系统
python main.py
```

### 技巧2：只为关键Agent升级

在 `.env` 中：
```env
# 其他用经济型，只升级报告撰写员
REPORT_WRITER_PROVIDER=openrouter
```

### 技巧3：临时切换供应商

```bash
# Windows PowerShell
$env:REPORT_WRITER_PROVIDER="glm"
python main.py

# Linux/Mac
REPORT_WRITER_PROVIDER=glm python main.py
```

---

## 📋 配置检查清单

使用前检查：

- [ ] 已配置至少一个API密钥（`.env`）
- [ ] 运行 `python agent_config.py` 查看配置
- [ ] 运行 `python test_llm_providers.py` 测试
- [ ] 选择合适的预设方案
- [ ] 保存并重启程序

---

## 🆘 常见问题

### Q: 修改 agent_config.py 后不生效？

**A**: 重启程序，Python会重新加载配置。

### Q: 想要只修改一个Agent怎么办？

**A**: 在 `.env` 中只配置那个Agent的环境变量：
```env
REPORT_WRITER_PROVIDER=openrouter
```

### Q: 如何知道哪个方案适合我？

**A**: 参考这个：
- 预算有限 → economy
- 追求性价比 → balanced（推荐）
- 重要报告 → premium

### Q: 不同方案能混用吗？

**A**: 可以！使用 custom 方案或直接在 `.env` 中配置。

---

## 📚 相关文档

- `agent_config.py` - 集中配置文件（主要修改这个）
- `.env` - 环境变量配置（覆盖用）
- `LLM_PROVIDERS_GUIDE.md` - 详细使用指南
- `MULTI_LLM_README.md` - 快速开始

---

**最后修改**: 2026-01-06  
**配置文件**: `agent_config.py`  
**快速命令**: `python agent_config.py`
