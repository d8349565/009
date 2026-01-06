# 🔬 AI研究报告生成系统 - 完整使用指南

一个基于 DeepSeek AI 的智能信息研究和报告生成系统，能够自动搜索、分析和整理信息，生成专业的研究报告。

---

## 📌 快速开始

### 安装依赖
```bash
pip install -r requirements.txt
```

### 启动方式
```bash
# GUI图形界面（推荐）
双击: 启动GUI.bat
或: python gui_app.py

# 命令行模式
python main.py
```

---

## ✨ 核心特性

- 🤖 **智能需求分析**: 自动解析用户需求，提取关键信息和搜索关键词
- 🔍 **多搜索引擎支持**: 支持 Tavily 和 SearXNG 两种搜索引擎
- 📊 **信息可信度评估**: 自动评估信息源的可信度和相关性（批量优化）
- 📝 **自动报告生成**: 生成结构化的 Markdown 格式研究报告
- ⚡ **快速/完整两种模式**: 根据需求选择快速搜索或多轮迭代优化
- 🎯 **优先搜索源**: 支持优先搜索权威机构信息
- 💾 **自动保存**: 自动保存报告并支持浏览器打开
- 📈 **性能监控**: 详细的执行时间统计
- 📚 **综合报告**: 整合多个历史报告，生成深度综合分析
- 🖥️ **图形界面**: 现代化的 wxPython GUI

---

## 🖥️ GUI使用说明

### 📝 Tab 1: 新建报告

**功能**：生成单个研究报告

**使用步骤**：
1. 输入研究主题（例如："2020-2024年中国船舶涂料产量分析"）
2. 选择搜索模式：
   - **快速模式**：单次搜索，速度快（~30秒）
   - **完整模式**：多轮迭代，质量高（~2分钟）
3. 可选：勾选"跳过评估"以提速70%
4. 点击 **🚀 开始生成** 按钮
5. 实时日志窗口显示进度（包含时间戳和彩色输出）
6. 完成后自动打开报告

**日志说明**：
- `步骤1-4`：4个Agent协作流程
  - 步骤1: 需求分析师 - 解析需求和生成搜索关键词
  - 步骤2: 信息收集员 - 搜索和评估信息
  - 步骤3: 报告撰写员 - 编写专业报告
  - 步骤4: 质量评审员 - 评审报告质量
- `总耗时`：完整执行时间
- 所有输出重定向到GUI，不再显示在终端

**多任务支持**：
- 点击 **➕ 新建任务** 可创建多个独立任务
- 每个任务有独立的日志窗口和进度条
- 支持同时运行多个调研任务

**停止任务**：点击 **🛑 停止** 可中断正在运行的任务

---

### 🔍 Tab 2: 历史报告

**功能**：管理已生成的报告

**操作**：
- **🔍 搜索**：按文件名关键词筛选
- **🔄 刷新**：重新加载报告列表
- **📄 打开**：用默认程序打开选中的报告
- **🗑️ 删除**：删除选中的报告（含元数据文件）

**列表信息**：
- 文件名、主题、创建时间、文件大小
- 按时间倒序排列（最新的在上面）

---

### ⚙️ Tab 3: 系统配置

**功能**：可视化编辑系统配置

#### 子标签1：Agent模型配置

为系统中的5个Agent分别配置LLM模型：

1. **需求分析师** (Requirement Analyzer)
2. **信息收集员** (Information Collector)  
3. **报告撰写员** (Report Writer)
4. **质量评审员** (Quality Judge)
5. **综合报告撰写员** (Comprehensive Writer)

**配置选项**：
- **供应商**：下拉选择（deepseek / glm / zhipu / openrouter）
- **模型**：根据供应商自动显示可用模型列表
- **推理模式**：启用 deepseek-reasoner 或类似推理模型

**模型配置文件**：
- 点击 **📝 编辑模型配置文件** 按钮可以编辑 `model_config.json`
- 添加新的供应商或模型后，点击 **🔄 重新加载** 即可生效

#### 子标签2：环境变量配置

配置API密钥和搜索引擎：

- **API密钥**：
  - DeepSeek API Key
  - Zhipu/GLM API Key
  - OpenRouter API Key
  - Tavily API Key
- **SearXNG**：服务器地址配置

#### 子标签3：搜索配置

**搜索引擎选择**：
- SearXNG（本地部署）
- Tavily（云端服务）

**性能优化选项**：
| 选项 | 效果 | 推荐场景 |
|------|------|---------|
| ✅ 跳过信息评估 | 提速70%，质量↓ | 快速查看初步结果 |
| ✅ 精简报告输入 | 提速30% | 平衡速度和质量 |
| ✅ 优先搜索权威来源 | 提升质量 | 需要高可信度信息 |

**调优参数**：
- **并发评估批数**：1-10（推荐：6）
- **内容提取长度**：500-10000字符（推荐：4000）

**配置方案**：

| 方案 | 模式 | 跳过评估 | 内容长度 | 耗时 | 质量 |
|------|------|----------|----------|------|------|
| 极速 | 快速 | ✅ | 1000 | ~20秒 | ⭐⭐ |
| 推荐 | 完整 | ❌ | 4000 | ~2分钟 | ⭐⭐⭐⭐ |
| 高质 | 完整 | ❌ | 6000 | ~3分钟 | ⭐⭐⭐⭐⭐ |

**按钮**：
- **💾 保存配置**：写入 `.env` 文件（需重启生效）
- **🔄 重新加载**：从文件重新读取配置
- **↩️ 恢复默认**：清空所有配置

---

### 📚 Tab 4: 综合报告

**功能**：整合多个历史报告，生成综合分析

**使用步骤**：
1. 输入综合报告主题（例如："中国船舶涂料行业综合分析"）
2. 在列表中勾选要整合的报告（至少2个）
3. 点击 **🚀 生成综合报告**
4. AI自动执行：
   - 提取关键数据
   - 交叉验证信息
   - 识别矛盾和一致性
   - 生成综合分析
5. 实时日志显示生成过程
6. 完成后自动打开综合报告

**辅助按钮**：
- **☑️ 全选**：选中所有报告
- **❌ 清空**：取消所有选择
- **🔄 刷新列表**：重新加载报告列表

**使用场景**：
- 已完成多个单独主题的调研，想要生成综合分析报告
- 需要对比分析多个相关报告，发现新洞察
- 想要进行数据交叉验证，识别矛盾和一致性

---

## 🛠️ 配置文件说明

### .env 环境变量
```bash
# API密钥
DEEPSEEK_API_KEY="your_key_here"
ZHIPU_API_KEY="your_key_here"
OPENROUTER_API_KEY="your_key_here"
TAVILY_API_KEY="your_key_here"

# SearXNG配置
SEARXNG_BASE_URL="http://localhost:8080"
SEARCH_ENGINE_TYPE="searxng"  # 或 "tavily"

# 性能优化
SKIP_EVALUATION="false"
SIMPLIFY_REPORT_INPUT="false"
USE_PRIORITY_SOURCES="false"
MAX_CONCURRENT_EVALUATIONS="6"
CONTENT_EXTRACT_LENGTH="4000"

# Agent模型配置示例
REQUIREMENT_ANALYZER_PROVIDER="deepseek"
REQUIREMENT_ANALYZER_MODEL="deepseek-chat"
REQUIREMENT_ANALYZER_USE_REASONER="false"
```

### model_config.json 模型配置
```json
{
  "deepseek": {
    "name": "DeepSeek",
    "models": [
      {
        "id": "deepseek-chat",
        "name": "DeepSeek Chat",
        "description": "基础对话模型，快速响应"
      },
      {
        "id": "deepseek-reasoner",
        "name": "DeepSeek Reasoner",
        "description": "推理模型，适合复杂分析"
      }
    ]
  },
  "glm": {
    "name": "智谱AI (GLM)",
    "models": [
      {
        "id": "glm-4-flash",
        "name": "GLM-4-Flash",
        "description": "快速响应模型"
      },
      {
        "id": "glm-4-plus",
        "name": "GLM-4-Plus",
        "description": "高级推理模型"
      }
    ]
  }
}
```

---

## 📂 文件结构

```
009/
├── main.py                    # 主程序入口（命令行模式）
├── gui_app.py                 # GUI界面程序
├── agents.py                  # 4个Agent实现
├── agent_prompts.py           # Agent提示词配置
├── agent_config.py            # Agent配置管理
├── search_engine.py           # 搜索引擎封装
├── config.py                  # 配置管理
├── llm_providers.py           # LLM供应商适配器
├── performance_timer.py       # 性能计时工具
├── report_metadata.py         # 报告元数据管理
├── report_search.py           # 报告搜索工具
├── document_parser.py         # 文档解析工具
├── .env                       # 环境变量配置
├── .env.example               # 配置模板
├── model_config.json          # 模型配置文件
├── requirements.txt           # Python依赖
├── 启动GUI.bat                # Windows启动脚本
├── reports/                   # 报告存储目录
│   ├── *.md                   # Markdown报告
│   └── *.json                 # 报告元数据
└── 项目修改总结文档/          # 技术文档目录
```

---

## 🔧 技术架构

### Agent系统（4个角色的流水线）
```
需求分析师 → 信息收集员 → 报告撰写员 → 质量评审员
  (analyze)    (collect)     (write)      (judge)
```

### 工作流程

**快速模式** (`SEARCH_MODE=quick`)：
1. RequirementAnalyzer.analyze() → 生成搜索关键词
2. SearchEngine.search() → 单次并行搜索
3. 可选跳过：InformationCollector（评估阶段）
4. ReportWriter.write() → 生成报告
5. 可选跳过：QualityJudge（评审阶段）

**完整模式** (`SEARCH_MODE=full`)：
同上，但会多次循环（最多 `MAX_LOOP_COUNT` 轮），每轮收集 → 评审 → 补充搜索

### 性能监控（PerformanceTimer）
```python
timer.start_total()           # 总计时开始
timer.start("步骤X", desc)    # 开始某步
timer.end("步骤X", extra)     # 结束并记录
timer.get_total_duration()    # 获取总秒数
```

---

## 🎯 使用场景示例

### 场景1：快速了解某个行业
```
主题: "2024年中国新能源汽车市场现状"
模式: 快速搜索
配置: 跳过评估 ✅
耗时: ~20秒
结果: 获得基础信息概览
```

### 场景2：深度行业研究
```
主题: "2020-2024年中国船舶涂料行业发展趋势"
模式: 完整搜索
配置: 
  - 跳过评估 ❌
  - 内容长度: 6000
  - 优先权威来源 ✅
耗时: ~3分钟
结果: 高质量深度报告
```

### 场景3：综合多个报告
```
主题: "中国船舶涂料行业综合分析"
选择报告:
  - 产量分析报告
  - 市场规模报告
  - 技术趋势报告
耗时: ~2分钟
结果: 交叉验证的综合分析报告
```

---

## ❓ 常见问题

### Q1: GUI无法启动？
```bash
# 检查Python版本（需要3.8+）
python --version

# 安装GUI依赖
pip install wxpython
```

### Q2: API调用失败？
- 检查 `.env` 文件中的API密钥是否正确
- 确认网络连接正常
- 查看日志窗口的具体错误信息

### Q3: 搜索无结果？
- 尝试切换搜索引擎（Tab 3 → 搜索配置）
- 检查SearXNG服务是否正常运行
- 确认Tavily API密钥是否有效

### Q4: 报告生成失败？
- 查看日志窗口的错误详情
- 确认选择的LLM模型是否可用
- 检查API配额是否充足

### Q5: 配置不生效？
- 点击 **💾 保存配置** 后需要重启应用
- 确认 `.env` 文件的权限正常
- 检查是否有拼写错误

### Q6: 如何添加新的LLM模型？
1. 编辑 `model_config.json` 文件
2. 在对应供应商下添加新模型配置
3. 保存文件
4. 在GUI中点击 **🔄 重新加载**

---

## 📊 性能优化建议

### 如果系统太慢（>30秒）：
1. 设置 `SKIP_EVALUATION=true`（节省60%时间）
2. 降低 `CONTENT_EXTRACT_LENGTH` 到1000
3. 增加 `MAX_CONCURRENT_EVALUATIONS` 到8（如果API额度充足）
4. 使用快速模式

### 如果报告质量不够：
1. 调整 `agent_prompts.py` 中的提示词
2. 启用 `USE_PRIORITY_SOURCES=true` 获取权威源
3. 改为 `SEARCH_MODE=full` 进行多轮迭代
4. 增加 `CONTENT_EXTRACT_LENGTH` 到6000
5. 使用更强大的模型（如 glm-4-plus）

### 如果搜索结果不相关：
1. 优化输入的研究主题，使其更具体
2. 调整搜索引擎（SearXNG vs Tavily）
3. 启用"优先搜索权威来源"
4. 使用完整模式进行多轮搜索

---

## 📋 测试清单

### 基础功能测试
- [ ] GUI成功启动
- [ ] 新建报告功能正常
- [ ] 历史报告管理正常
- [ ] 配置保存和加载正常
- [ ] 综合报告生成正常

### 多任务测试
- [ ] 创建多个任务
- [ ] 任务独立运行
- [ ] 日志不混乱
- [ ] 可以同时运行

### 配置测试
- [ ] 切换LLM供应商
- [ ] 修改模型配置
- [ ] 编辑环境变量
- [ ] 调整搜索参数

### 综合报告测试
- [ ] 选择2+报告
- [ ] 生成综合报告
- [ ] 交叉验证正确
- [ ] 矛盾识别准确

---

## 📚 扩展阅读

项目包含以下技术文档（位于 `项目修改总结文档/` 目录）：

- `ARCHITECTURE.md` - 系统架构说明
- `AGENT_CONFIG_GUIDE.md` - Agent配置指南
- `LLM_PROVIDERS_GUIDE.md` - LLM供应商集成指南
- `COMPREHENSIVE_REPORT_GUIDE.md` - 综合报告功能详解
- `REPORT_METADATA_GUIDE.md` - 报告元数据系统
- `MODEL_SELECTION_GUIDE.md` - 模型选择建议
- `TROUBLESHOOTING.md` - 故障排查指南

---

## 🤝 贡献与反馈

如有问题或建议，欢迎通过以下方式反馈：
- 提交 Issue
- 发送邮件
- 提交 Pull Request

---

## 📝 更新日志

查看 `CHANGELOG.md` 了解详细的版本更新历史。

最新版本特性：
- ✅ 综合报告功能（2026-01-06）
- ✅ 多任务支持（2026-01-06）
- ✅ JSON配置化模型管理（2026-01-06）
- ✅ 实时日志显示（2026-01-06）
- ✅ 窗口尺寸优化（2026-01-06）

---

## 📄 许可证

MIT License

---

**享受智能研究报告生成的乐趣！** 🎉
