# 多LLM供应商配置指南

## 概述

本系统现已支持多个LLM供应商，您可以为不同的Agent配置不同的模型，实现性能与成本的最优平衡。

## 支持的供应商

### 1. DeepSeek (默认)
- **优势**: 高性价比，支持推理模型(deepseek-reasoner)
- **模型**: `deepseek-chat`, `deepseek-reasoner`
- **获取密钥**: https://platform.deepseek.com/

### 2. 智谱AI (GLM)
- **优势**: 中文理解能力强，响应速度快
- **模型**: `glm-4-flash` (快速), `glm-4.7` (高级)
- **获取密钥**: https://open.bigmodel.cn/

### 3. OpenRouter
- **优势**: 聚合多个模型，可使用Claude、GPT-4等
- **模型**: 可配置任意OpenRouter支持的模型
- **获取密钥**: https://openrouter.ai/

## 快速配置

### 步骤1: 配置API密钥

在 `.env` 文件中添加您的API密钥：

```env
# DeepSeek (必须)
DEEPSEEK_API_KEY=sk-xxxxx

# 智谱GLM (可选)
ZHIPU_API_KEY=xxxxx.xxxxx

# OpenRouter (可选)
OPENROUTER_API_KEY=sk-or-xxxxx
```

### 步骤2: 配置Agent使用的提供商

在 `.env` 中为每个Agent指定提供商：

```env
# 需求分析师 - 使用GLM（中文理解好）
REQUIREMENT_ANALYZER_PROVIDER=glm

# 信息收集员 - 使用DeepSeek（高性价比）
INFORMATION_COLLECTOR_PROVIDER=deepseek

# 报告撰写员 - 使用DeepSeek推理模型（质量高）
REPORT_WRITER_PROVIDER=deepseek

# 质量评审员 - 使用GLM（快速评估）
QUALITY_JUDGE_PROVIDER=glm

# 综合报告撰写员 - 使用DeepSeek推理模型
COMPREHENSIVE_REPORT_WRITER_PROVIDER=deepseek
```

### 步骤3: 运行系统

```bash
python main.py
```

系统会自动使用配置的提供商，并在运行时显示使用的模型。

## 推荐配置方案

### 方案A: 全DeepSeek (性价比最高)
```env
REQUIREMENT_ANALYZER_PROVIDER=deepseek
INFORMATION_COLLECTOR_PROVIDER=deepseek
REPORT_WRITER_PROVIDER=deepseek
QUALITY_JUDGE_PROVIDER=deepseek
COMPREHENSIVE_REPORT_WRITER_PROVIDER=deepseek
```

**优势**: 
- 成本最低
- 推理模型质量高
- 配置简单

**适用场景**: 预算有限，对中文要求不高

---

### 方案B: 混合配置 (平衡性能与成本)
```env
REQUIREMENT_ANALYZER_PROVIDER=glm          # 中文理解
INFORMATION_COLLECTOR_PROVIDER=deepseek   # 批量处理
REPORT_WRITER_PROVIDER=deepseek           # 推理能力
QUALITY_JUDGE_PROVIDER=glm                # 快速评估
COMPREHENSIVE_REPORT_WRITER_PROVIDER=deepseek  # 深度分析
```

**优势**:
- GLM处理中文需求更准确
- DeepSeek处理复杂推理和数据整合
- 成本适中

**适用场景**: 重视中文质量，预算充足

---

### 方案C: 高端配置 (使用OpenRouter)
```env
REQUIREMENT_ANALYZER_PROVIDER=glm
INFORMATION_COLLECTOR_PROVIDER=deepseek
REPORT_WRITER_PROVIDER=openrouter
QUALITY_JUDGE_PROVIDER=glm
COMPREHENSIVE_REPORT_WRITER_PROVIDER=openrouter

# 指定OpenRouter使用的模型
OPENROUTER_DEFAULT_MODEL=xiaomi/mimo-v2-flash:free
OPENROUTER_REASONER_MODEL=openai/o1-preview
```

**优势**:
- Claude 3.5写作质量最高
- O1推理能力顶级
- 适合关键报告

**适用场景**: 重要项目，对质量要求极高

## 成本对比

基于1000次调用的估算成本（仅供参考）：

| 供应商 | 输入成本 | 输出成本 | 总成本估算 |
|--------|---------|---------|-----------|
| DeepSeek Chat | ¥0.14 | ¥0.28 | ¥5-15 |
| DeepSeek Reasoner | ¥0.56 | ¥2.8 | ¥20-50 |
| glm-4.7| ¥0.1 | ¥0.1 | ¥3-10 |
| glm-4.7 | ¥5 | ¥5 | ¥150-300 |
| Claude 3.5 | ¥15 | ¥75 | ¥500-1500 |

**建议**: 
- 日常使用：方案A或B
- 重要报告：方案C（仅报告撰写员用高端模型）

## 高级配置

### 指定具体模型

您也可以在代码中直接指定模型：

```python
from agents import RequirementAnalyzer

# 使用智谱GLM的plus版本
analyzer = RequirementAnalyzer(provider="glm")

# 使用OpenRouter的特定模型
analyzer = RequirementAnalyzer(
    provider="openrouter",
    model="xiaomi/mimo-v2-flash:free"
)
```

### 动态切换提供商

系统会自动检测配置的API密钥，如果某个提供商不可用，会自动回退到DeepSeek。

### 查看可用提供商

```python
from llm_providers import get_llm_manager

manager = get_llm_manager()
print("可用的提供商:", manager.get_available_providers())
```

## 故障排除

### 问题1: 提示"提供商不可用"

**原因**: 未配置对应的API密钥

**解决**: 
1. 检查 `.env` 文件中是否配置了API密钥
2. 确认密钥格式正确（无多余空格）
3. 重启程序以重新加载环境变量

### 问题2: API调用失败

**原因**: 密钥无效或额度不足

**解决**:
1. 验证密钥是否正确
2. 检查账户余额
3. 查看API调用限制

### 问题3: 响应速度慢

**建议**:
1. 调整 `CONTENT_EXTRACT_LENGTH` 减少输入长度
2. 使用 `glm-4-flash` 等快速模型
3. 启用 `SIMPLIFY_REPORT_INPUT=true`

## 监控与日志

系统在运行时会显示：
- 使用的提供商名称
- 使用的模型名称
- API调用耗时

示例输出：
```
[需求分析师] 提供商: GLM, 模型: glm-4-flash
[需求分析师] API调用耗时: 2.34秒
```

## 更新日志

- **2026-01-06**: 
  - ✅ 支持多LLM供应商
  - ✅ 添加智谱GLM支持
  - ✅ 添加OpenRouter支持
  - ✅ 为每个Agent单独配置提供商
  - ✅ 自动回退机制

## 反馈与支持

如有问题，请查看 `llm_providers.py` 中的实现细节。
