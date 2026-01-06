# 模型选择指南

## 🎯 快速选择

### 我该用哪个供应商？

| 场景 | 推荐供应商 | 推荐模型 | 理由 |
|------|-----------|---------|------|
| **日常使用** | DeepSeek | deepseek-chat | 性价比最高，速度快 |
| **复杂任务** | DeepSeek | deepseek-reasoner | 推理能力强，适合写报告 |
| **中文理解** | 智谱GLM | glm-4.7| 中文理解最好，速度快 |
| **高质量输出** | 智谱GLM | glm-4.7 | 质量最高，适合关键任务 |
| **国际模型** | OpenRouter | xiaomi/mimo-v2-flash:free | Claude写作质量好 |
| **深度推理** | OpenRouter | o1-preview | OpenAI最强推理模型 |

---

## 📊 各供应商模型详解

### 1️⃣ DeepSeek (最推荐，性价比最高)

**deepseek-chat**（基础模型）
- **特点**：速度快，成本低
- **适合**：需求分析、信息评估、快速响应
- **成本**：¥0.001/千tokens（输入），¥0.002/千tokens（输出）
- **配置**：
  ```env
  REQUIREMENT_ANALYZER_PROVIDER=deepseek
  REQUIREMENT_ANALYZER_MODEL=deepseek-chat
  ```

**deepseek-reasoner**（推理模型）
- **特点**：推理能力强，适合复杂任务
- **适合**：报告撰写、质量评审、深度分析
- **成本**：¥0.014/千tokens（缓存输入），¥0.28/千tokens（非缓存输入），¥1.12/千tokens（输出）
- **配置**：
  ```env
  REPORT_WRITER_PROVIDER=deepseek
  REPORT_WRITER_MODEL=deepseek-reasoner
  ```

---

### 2️⃣ 智谱AI GLM-4 (中文理解最好)

**glm-4-flash**（快速模型）
- **特点**：速度快，中文理解好，成本适中
- **适合**：中文需求分析、快速评估
- **成本**：¥0.001/千tokens（输入），¥0.001/千tokens（输出）
- **配置**：
  ```env
  REQUIREMENT_ANALYZER_PROVIDER=glm
  REQUIREMENT_ANALYZER_MODEL=glm-4-flash
  ```

**glm-4.7**（高级模型）
- **特点**：质量高，中文表达自然
- **适合**：高质量报告、关键决策
- **成本**：¥0.05/千tokens（输入），¥0.05/千tokens（输出）
- **配置**：
  ```env
  REPORT_WRITER_PROVIDER=glm
  REPORT_WRITER_MODEL=glm-4.7
  ```

---

### 3️⃣ OpenRouter (聚合多个国际模型)

**xiaomi/mimo-v2-flash:free**
- **特点**：写作质量极高，逻辑清晰
- **适合**：专业报告撰写
- **成本**：$3/M tokens（输入），$15/M tokens（输出）
- **配置**：
  ```env
  REPORT_WRITER_PROVIDER=openrouter
  REPORT_WRITER_MODEL=xiaomi/mimo-v2-flash:free
  ```

**openai/o1-preview**
- **特点**：OpenAI最强推理模型
- **适合**：复杂推理、质量评审
- **成本**：$15/M tokens（输入），$60/M tokens（输出）
- **配置**：
  ```env
  QUALITY_JUDGE_PROVIDER=openrouter
  QUALITY_JUDGE_MODEL=openai/o1-preview
  ```

更多OpenRouter模型：https://openrouter.ai/models

---

## 🎨 推荐配置方案

### 方案A：经济型（¥3-6/100次）

**适合**：日常使用、快速测试、个人学习

```env
# 全部使用 DeepSeek 基础模型
REQUIREMENT_ANALYZER_PROVIDER=deepseek
REQUIREMENT_ANALYZER_MODEL=deepseek-chat

INFORMATION_COLLECTOR_PROVIDER=deepseek
INFORMATION_COLLECTOR_MODEL=deepseek-chat

REPORT_WRITER_PROVIDER=deepseek
REPORT_WRITER_MODEL=deepseek-chat

QUALITY_JUDGE_PROVIDER=deepseek
QUALITY_JUDGE_MODEL=deepseek-chat
```

或者在 `agent_config.py` 中设置：
```python
AGENT_CONFIG_PRESET = "economy"
```

---

### 方案B：均衡型（¥6-10/100次）⭐ 推荐

**适合**：正式使用、追求性价比、商业项目

```env
# 快速任务用 GLM Flash，复杂任务用 DeepSeek Reasoner
REQUIREMENT_ANALYZER_PROVIDER=glm
REQUIREMENT_ANALYZER_MODEL=glm-4-flash

INFORMATION_COLLECTOR_PROVIDER=deepseek
INFORMATION_COLLECTOR_MODEL=deepseek-chat

REPORT_WRITER_PROVIDER=deepseek
REPORT_WRITER_MODEL=deepseek-reasoner

QUALITY_JUDGE_PROVIDER=glm
QUALITY_JUDGE_MODEL=glm-4-flash

COMPREHENSIVE_REPORT_WRITER_PROVIDER=deepseek
COMPREHENSIVE_REPORT_WRITER_MODEL=deepseek-reasoner
```

或者在 `agent_config.py` 中设置：
```python
AGENT_CONFIG_PRESET = "balanced"
```

---

### 方案C：高端型（¥20-50/100次）

**适合**：关键报告、高质量要求、对外展示

```env
# 使用最高质量的模型
REQUIREMENT_ANALYZER_PROVIDER=glm
REQUIREMENT_ANALYZER_MODEL=glm-4.7

INFORMATION_COLLECTOR_PROVIDER=deepseek
INFORMATION_COLLECTOR_MODEL=deepseek-chat

REPORT_WRITER_PROVIDER=openrouter
REPORT_WRITER_MODEL=xiaomi/mimo-v2-flash:free

QUALITY_JUDGE_PROVIDER=openrouter
QUALITY_JUDGE_MODEL=openai/o1-preview

COMPREHENSIVE_REPORT_WRITER_PROVIDER=openrouter
COMPREHENSIVE_REPORT_WRITER_MODEL=openai/o1-preview
```

或者在 `agent_config.py` 中设置：
```python
AGENT_CONFIG_PRESET = "premium"
```

---

## 🔧 配置优先级

系统按以下优先级读取配置（高到低）：

1. **环境变量 *_MODEL**（最高优先级）
   ```env
   REQUIREMENT_ANALYZER_MODEL=glm-4.7
   ```

2. **环境变量 *_PROVIDER**
   ```env
   REQUIREMENT_ANALYZER_PROVIDER=glm
   ```

3. **agent_config.py 配置方案**
   ```python
   AGENT_CONFIG_PRESET = "balanced"
   ```

4. **系统默认值**
   - 默认供应商：deepseek
   - 默认模型：deepseek-chat

---

## 💡 配置技巧

### 1. 只指定供应商（推荐新手）

```env
REQUIREMENT_ANALYZER_PROVIDER=glm
```

系统会自动选择该供应商的合适模型（如 glm-4-flash）

### 2. 同时指定供应商和模型（精确控制）

```env
REQUIREMENT_ANALYZER_PROVIDER=glm
REQUIREMENT_ANALYZER_MODEL=glm-4.7  # 使用高级模型
```

### 3. 混合配置（灵活组合）

```env
# 快速任务用 GLM Flash（便宜快速）
REQUIREMENT_ANALYZER_PROVIDER=glm
REQUIREMENT_ANALYZER_MODEL=glm-4-flash

# 核心任务用 DeepSeek Reasoner（推理能力强）
REPORT_WRITER_PROVIDER=deepseek
REPORT_WRITER_MODEL=deepseek-reasoner

# 评审用 Claude（质量高）
QUALITY_JUDGE_PROVIDER=openrouter
QUALITY_JUDGE_MODEL=xiaomi/mimo-v2-flash:free
```

---

## 🚀 快速开始

### 步骤1：选择配置方式

**方式A：使用预设方案**（最简单）
1. 编辑 `agent_config.py`
2. 修改 `AGENT_CONFIG_PRESET = "balanced"`
3. 保存即可

**方式B：使用环境变量**（更灵活）
1. 复制 `.env.example` 为 `.env`
2. 取消注释并修改 `*_PROVIDER` 和 `*_MODEL` 变量
3. 保存即可

### 步骤2：验证配置

```bash
python agent_config.py
```

会显示当前配置的详细信息，包括：
- 每个Agent使用的供应商
- 每个Agent使用的具体模型
- 是否启用推理模式
- 配置来源（预设方案 or 环境变量）

### 步骤3：运行系统

```bash
python main.py
```

---

## ❓ 常见问题

### Q1：我应该用哪个供应商？

**新手建议**：全部用 DeepSeek（性价比最高）
**进阶建议**：混合使用（快速任务用GLM，复杂任务用DeepSeek Reasoner）
**高端需求**：关键任务用OpenRouter的Claude或o1

### Q2：为什么显示 "(自动选择)"？

表示你只指定了供应商，没有指定具体模型。系统会自动选择该供应商的默认模型：
- DeepSeek → deepseek-chat
- GLM → glm-4-flash
- OpenRouter → OPENROUTER_DEFAULT_MODEL 环境变量中的值

如需明确控制，请同时指定 `*_MODEL` 环境变量。

### Q3：配置不生效怎么办？

1. 检查 `.env` 文件是否存在（不是 `.env.example`）
2. 检查环境变量名称是否正确（大写，下划线连接）
3. 运行 `python agent_config.py` 查看实际配置
4. 检查 API 密钥是否正确配置

### Q4：如何降低成本？

1. 设置 `AGENT_CONFIG_PRESET = "economy"`
2. 或者手动配置全部使用 `deepseek-chat`
3. 启用 `SKIP_EVALUATION=true`（跳过信息评估）
4. 启用 `SIMPLIFY_REPORT_INPUT=true`（精简输入数据）

### Q5：如何提高质量？

1. 设置 `AGENT_CONFIG_PRESET = "premium"`
2. 报告撰写员使用 `deepseek-reasoner` 或 `xiaomi/mimo-v2-flash:free`
3. 质量评审员使用 `o1-preview` 或 `glm-4.7`
4. 设置 `SKIP_EVALUATION=false`（启用信息评估）

---

## 📞 获取帮助

- **查看当前配置**：`python agent_config.py`
- **查看所有环境变量**：查看 `.env.example` 文件
- **查看详细文档**：
  - `AGENT_CONFIG_GUIDE.md` - 配置系统详解
  - `LLM_PROVIDERS_GUIDE.md` - 多模型供应商详解
  - `QUICK_REFERENCE.txt` - 快速参考

---

## 🔄 版本更新

**v2.0**（当前版本）
- ✅ 支持 *_MODEL 环境变量，可指定具体模型
- ✅ 改进配置显示，显示实际模型名称
- ✅ 所有预设方案使用明确的模型名称
- ✅ 更清晰的配置优先级说明

**v1.0**
- ✅ 支持多个LLM供应商（DeepSeek、GLM、OpenRouter）
- ✅ 集中配置系统（agent_config.py）
- ✅ 4个预设配置方案
- ✅ 环境变量覆盖支持
