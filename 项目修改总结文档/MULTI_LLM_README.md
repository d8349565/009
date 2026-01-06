# 🎉 多LLM供应商功能 - 新特性说明

## ✨ 新增功能

本次更新为系统添加了**多LLM供应商支持**，您现在可以：

1. ✅ 同时配置多个LLM供应商（DeepSeek、智谱GLM、OpenRouter）
2. ✅ 为每个Agent独立配置使用的模型
3. ✅ 根据任务类型优化成本和性能
4. ✅ 自动回退机制保证系统稳定性

---

## 🚀 快速开始

### 1. 配置API密钥

在 `.env` 文件中添加您的API密钥（至少一个）：

```env
# DeepSeek（默认，推荐）
DEEPSEEK_API_KEY=sk-xxxxx

# 智谱GLM（中文理解强）
ZHIPU_API_KEY=xxxxx.xxxxx

# OpenRouter（聚合多模型）
OPENROUTER_API_KEY=sk-or-xxxxx
```

### 2. 配置Agent使用的提供商

```env
# 推荐混合配置
REQUIREMENT_ANALYZER_PROVIDER=glm        # 中文理解
INFORMATION_COLLECTOR_PROVIDER=deepseek  # 批量处理
REPORT_WRITER_PROVIDER=deepseek          # 推理能力
QUALITY_JUDGE_PROVIDER=glm               # 快速评估
```

### 3. 运行测试

```bash
python test_llm_providers.py
```

### 4. 开始使用

```bash
python main.py
```

系统会自动显示每个Agent使用的提供商和模型。

---

## 📊 配置方案推荐

### 方案A：经济型（全DeepSeek）

**成本**: ¥3-6 / 100次  
**适合**: 个人用户、预算有限

```env
REQUIREMENT_ANALYZER_PROVIDER=deepseek
INFORMATION_COLLECTOR_PROVIDER=deepseek
REPORT_WRITER_PROVIDER=deepseek
QUALITY_JUDGE_PROVIDER=deepseek
```

---

### 方案B：混合型（推荐）⭐

**成本**: ¥6-10 / 100次  
**适合**: 商业用户、追求性价比

```env
REQUIREMENT_ANALYZER_PROVIDER=glm
INFORMATION_COLLECTOR_PROVIDER=deepseek
REPORT_WRITER_PROVIDER=deepseek
QUALITY_JUDGE_PROVIDER=glm
```

**优势**:
- GLM处理中文需求更准确
- DeepSeek推理质量高
- 成本仅增加一倍但质量提升明显

---

### 方案C：高端型

**成本**: ¥20-50 / 100次  
**适合**: 关键报告、最高质量要求

```env
REQUIREMENT_ANALYZER_PROVIDER=glm
INFORMATION_COLLECTOR_PROVIDER=deepseek
REPORT_WRITER_PROVIDER=openrouter
QUALITY_JUDGE_PROVIDER=glm

OPENROUTER_DEFAULT_MODEL=xiaomi/mimo-v2-flash:free
```

---

## 📖 文档清单

| 文档 | 说明 |
|------|------|
| `LLM_PROVIDERS_GUIDE.md` | 详细使用指南（2000+字） |
| `IMPLEMENTATION_SUMMARY.md` | 实现总结和技术细节 |
| `ARCHITECTURE.md` | 系统架构图 |
| `test_llm_providers.py` | 自动化测试脚本 |
| `demo_llm_providers.py` | 功能演示脚本 |

---

## 🎯 功能亮点

### 1. 灵活配置

三级配置层次：
```
环境变量 (.env)
    ↓
配置文件 (config.py)
    ↓
代码级别 (agents.py)
```

### 2. 智能回退

```python
# 如果GLM不可用，自动使用DeepSeek
analyzer = RequirementAnalyzer(provider="glm")
# 实际使用: deepseek（如果GLM未配置）
```

### 3. 成本优化

```
混合配置 vs 全Reasoner
¥6-10    vs  ¥20-30
节省: 60-70%
```

### 4. 向后兼容

- ✅ 不破坏现有代码
- ✅ 默认使用DeepSeek
- ✅ 渐进式升级

---

## 🔧 技术实现

### 核心文件

1. **llm_providers.py** (新建)
   - 统一的LLM提供商管理
   - 支持3个主流供应商
   - 自动加载和管理

2. **agents.py** (更新)
   - 所有Agent支持多提供商
   - 新增 `provider` 和 `model` 参数
   - 显示使用的提供商和模型

3. **config.py** (更新)
   - 添加多供应商配置
   - 每个Agent独立配置

---

## 📊 运行示例

```bash
$ python main.py

============================================================
信息整理Agent系统已启动（搜索引擎: SEARXNG）
============================================================

[步骤1] 需求分析师正在分析需求...
  [需求分析师] 提供商: GLM, 模型: glm-4-flash
  [需求分析师] API调用耗时: 1.23秒
✓ 需求分析完成

[步骤4] 信息收集员正在评估数据...
  [信息收集员] 提供商: DEEPSEEK, 模型: deepseek-chat
  [信息收集员] API调用耗时: 8.45秒
✓ 数据评估完成

[步骤5] 报告撰写员正在生成报告...
  [报告撰写员] 使用思考模式进行深度分析...
  [报告撰写员] 提供商: DEEPSEEK, 模型: deepseek-reasoner
  [报告撰写员] API调用耗时: 45.67秒
✓ 报告生成完成
```

---

## 🆘 故障排除

### 问题：提示"提供商不可用"

**解决方案**:
1. 检查 `.env` 文件中的API密钥
2. 确认密钥格式正确（无空格）
3. 重启程序以重新加载环境变量

### 问题：API调用失败

**解决方案**:
1. 验证API密钥是否正确
2. 检查账户余额
3. 查看API调用限制

### 问题：响应速度慢

**建议**:
1. 使用 `glm-4-flash` 等快速模型
2. 降低 `CONTENT_EXTRACT_LENGTH`
3. 启用 `SIMPLIFY_REPORT_INPUT=true`

---

## 🎓 获取API密钥

| 供应商 | 注册地址 | 特点 |
|--------|---------|------|
| DeepSeek | https://platform.deepseek.com/ | 高性价比，推理能力强 |
| 智谱GLM | https://open.bigmodel.cn/ | 中文理解好，响应快 |
| OpenRouter | https://openrouter.ai/ | 聚合多模型，Claude/GPT-4 |

---

## 📝 更新日志

### 2026-01-06 - v2.0

**新增**:
- ✅ 多LLM供应商支持
- ✅ 智谱GLM集成
- ✅ OpenRouter集成
- ✅ Agent级别配置
- ✅ 自动回退机制

**文档**:
- ✅ 详细使用指南
- ✅ 架构设计文档
- ✅ 测试和演示脚本

**兼容性**:
- ✅ 向后兼容
- ✅ 不破坏现有代码
- ✅ 默认使用DeepSeek

---

## 💡 下一步

1. **配置API密钥** - 在 `.env` 中添加
2. **选择配置方案** - 参考上面的推荐方案
3. **运行测试** - `python test_llm_providers.py`
4. **开始使用** - `python main.py`
5. **阅读文档** - 查看 `LLM_PROVIDERS_GUIDE.md`

---

## 🤝 反馈与支持

遇到问题？
1. 查看 `LLM_PROVIDERS_GUIDE.md` 详细文档
2. 运行 `python test_llm_providers.py` 诊断
3. 运行 `python demo_llm_providers.py` 查看示例

---

**实现完成**: 2026-01-06  
**版本**: v2.0  
**状态**: ✅ 生产就绪
