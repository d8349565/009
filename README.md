# 信息整理Agent系统

一个基于 DeepSeek AI 的智能信息研究和报告生成系统，能够自动搜索、分析和整理信息，生成专业的研究报告。

## ✨ 特性

- 🤖 **智能需求分析**: 自动解析用户需求，提取关键信息和搜索关键词
- 🔍 **多搜索引擎支持**: 支持 Tavily 和 SearXNG 两种搜索引擎
- 📊 **信息可信度评估**: 自动评估信息源的可信度和相关性（批量优化）
- 📝 **自动报告生成**: 生成结构化的 Markdown 格式研究报告
- ⚡ **快速/完整两种模式**: 根据需求选择快速搜索或多轮迭代优化
- 🎯 **优先搜索源**: 支持优先搜索权威机构信息
- 💾 **自动保存**: 自动保存报告并支持浏览器打开
- 📈 **性能监控*详细文档请查看：[REPORT_METADATA_GUIDE.md](REPORT_METADATA_GUIDE.md)

## 🎯 综合报告制作模式 ✨新功能

**功能说明**：整合多个历史报告，生成深度综合分详细文档请查看：[REPORT_METADATA_GUIDE.md](REPORT_METADATA_GUIDE.md)

**综合报告详细使用指南**：[COMPREHENSIVE_REPORT_GUIDE.md](COMPREHENSIVE_REPORT_GUIDE.md)

---

## 📚 完整文档索引

| 文档 | 说明 | 适合人群 |
|------|------|---------|
| [README.md](README.md) | 系统介绍和快速开始 | 所有用户 |
| [COMPREHENSIVE_REPORT_GUIDE.md](COMPREHENSIVE_REPORT_GUIDE.md) | 综合报告功能详细指南 | 综合报告用户 |
| [REPORT_METADATA_GUIDE.md](REPORT_METADATA_GUIDE.md) | 报告元数据系统文档 | 高级用户 |
| [IMPLEMENTATION_REPORT_PHASE1-2.md](IMPLEMENTATION_REPORT_PHASE1-2.md) | 阶段1-2技术实施报告 | 开发者 |
| [IMPLEMENTATION_REPORT_PHASE3.md](IMPLEMENTATION_REPORT_PHASE3.md) | 阶段3技术实施报告 | 开发者 |
| [PHASE3_COMPLETION_SUMMARY.md](PHASE3_COMPLETION_SUMMARY.md) | 阶段3完成总结 | 项目管理者 |

## 📝 许可证


### 使用场景

- 已完成多个单独主题的调研，想要生成综合分析报告
- 需要对比分析多个相关报告，发现新洞察
- 想要进行数据交叉验证，识别矛盾和一致性

### 工作流程

```
1. 用户输入综合报告主题
   ↓
2. 系统自动检索相关历史报告
   ↓
3. AI深度分析并整合多个报告
   ↓
4. 进行数据交叉验证
   ↓
5. 发现跨报告新洞察
   ↓
6. 生成综合报告
```

### 使用方法

#### 方法1: 直接输入主题

```bash
python main.py
# 选择模式: 2. 综合报告制作模式
# 选择输入方式: 1. 直接输入主题描述
# 输入: 2020-2024年中国汽车行业综合分析
```

#### 方法2: 提供大纲文件

支持Markdown、Word、PDF格式：

```bash
python main.py
# 选择模式: 2. 综合报告制作模式
# 选择输入方式: 2. 提供大纲文件路径
# 输入文件路径: ./my_outline.md
```

### 核心能力

#### 1. 数据交叉验证
- 对比不同来源的数据
- 识别一致和矛盾的信息
- 分析矛盾原因（时间、口径、地域等）
- 给出采用建议

#### 2. 发现新洞察
- **纵向对比**: 同主题跨时间趋势
- **横向对比**: 不同细分领域对比
- **因果分析**: 数据变化的潜在原因
- **预测推断**: 基于历史数据的合理推测

#### 3. 内容去重与整合
- 自动去除重复信息
- 整合互补数据
- 综合提炼相似观点

### 示例

```python
# 假设已有3个历史报告：
# 1. "2024年日系汽车在华销售情况"
# 2. "中国汽车市场2024年分析"
# 3. "新能源汽车对传统汽车的影响"

# 用户输入：
"综合分析2024年中国汽车市场格局"

# 系统自动：
1. 检索到以上3个相关报告
2. 提取关键数据和观点
3. 交叉验证：
   - 报告1和2的销售数据一致 ✓
   - 报告3的新能源数据与报告2有补充关系
4. 发现新洞察：
   - "传统汽车降幅与新能源增幅呈强相关"
   - "日系品牌受新能源冲击最为显著"
5. 生成综合报告，包含：
   - 市场整体格局
   - 各细分领域表现
   - 趋势预测
   - 数据来源标注
```

### 文档解析支持

系统支持解析以下格式的初稿文件：

- **Markdown (.md)**: 原生支持
- **Word (.docx)**: 需安装 `pip install python-docx`
- **PDF (.pdf)**: 需安装 `pip install pdfplumber` 或 `pip install PyPDF2`

### 注意事项

1. **需要先积累报告**：综合报告功能依赖历史报告库，建议先使用"单次调研模式"生成3个以上报告
2. **报告相关性**：系统会自动匹配相关报告，相关度越高整合效果越好
3. **数据矛盾处理**：如发现数据矛盾，系统会保留多个来源并说明差异原因
4. **AI推理模式**：综合报告使用DeepSeek推理模式，分析更深入但耗时较长

## 📝 许可证
置性能计时器，实时显示各环节耗时和优化建议
- 🏷️  **报告元数据管理**: 自动生成报告元数据，支持检索和管理
- 🔍 **历史报告检索**: 按关键词、主题、标签搜索历史报告
- 🎯 **综合报告制作**: 整合多个历史报告生成深度综合分析 ✨NEW

## 📋 系统要求

- Python 3.8+
- DeepSeek API Key（必需）
- Tavily API Key（可选，用于 Tavily 搜索）
- SearXNG 实例（可选，用于 SearXNG 搜索）

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd 009
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env`：

```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux/Mac
cp .env.example .env
```

编辑 `.env` 文件，配置必要的参数：

```bash
# DeepSeek API配置（必需）
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com

# Tavily搜索引擎配置（可选）
TAVILY_API_KEY=your_tavily_api_key_here
TAVILY_ENABLED=false

# SearXNG搜索引擎配置（可选）
SEARXNG_ENABLED=true
SEARXNG_BASE_URL=http://localhost:8080
SEARXNG_API_KEY=

# 搜索引擎选择：'tavily' 或 'searxng'
SEARCH_ENGINE_TYPE=searxng

# 搜索模式配置
# SEARCH_MODE: 'quick' (快速搜索) 或 'full' (完整搜索)
SEARCH_MODE=quick

# 完整搜索模式的最大迭代次数（仅在SEARCH_MODE=full时生效）
MAX_LOOP_COUNT=1

# 是否启用优先搜索源（权威机构优先）
USE_PRIORITY_SOURCES=false
```

### 4. 运行程序

#### Windows:
```bash
python main.py
# 或者
.\run.bat
```

#### Linux/Mac:
```bash
python main.py
```

## ⚙️ 配置说明

### 搜索引擎配置

系统支持两种搜索引擎：

1. **SearXNG** (默认)
   - 开源、隐私友好的元搜索引擎
   - 需要自己部署或使用公共实例
   - 无需 API Key
   - 配置示例：
     ```bash
     SEARCH_ENGINE_TYPE=searxng
     SEARXNG_BASE_URL=http://localhost:8080
     ```

2. **Tavily** (推荐)
   - 专业的 AI 搜索 API
   - 需要注册获取 API Key
   - 搜索质量更高
   - 配置示例：
     ```bash
     SEARCH_ENGINE_TYPE=tavily
     TAVILY_API_KEY=your_tavily_api_key_here
     ```

### 搜索模式配置

- **快速搜索模式** (`SEARCH_MODE=quick`)
  - 一次搜索直接生成报告
  - 速度快，适合快速获取信息
  - 默认模式

- **完整搜索模式** (`SEARCH_MODE=full`)
  - 多轮迭代优化
  - 包含质量评审和缺失信息补充
  - 报告质量更高，但耗时更长
  - 可通过 `MAX_LOOP_COUNT` 设置最大迭代次数

### 优先搜索源

启用后，系统会优先搜索配置的权威机构信息：

```bash
USE_PRIORITY_SOURCES=true
```

可在 `config.py` 中的 `PRIORITY_SOURCES` 配置优先搜索的机构列表。

## 📖 使用示例

### 基本使用

运行程序后，输入您的需求描述：

```
请输入您的需求描述: 近五年中国船舶涂料销售额
```

系统会自动：
1. 分析您的需求
2. 生成搜索关键词
3. 执行搜索
4. 评估信息可信度
5. 生成研究报告
6. 保存报告到 `reports/` 目录

### 报告示例

生成的报告包含：
- 执行摘要
- 详细数据和分析
- 信息来源
- 可信度评估
- 搜索元信息

报告以 Markdown 格式保存，文件名格式：`report_YYYYMMDD_HHMMSS.md`

## 📁 项目结构

```
009/
├── main.py                 # 主程序
├── config.py              # 配置文件
├── agents.py              # Agent 定义（需求分析、信息收集、报告生成等）
├── search_engine.py       # 搜索引擎封装
├── requirements.txt       # Python 依赖
├── .env.example          # 环境变量模板
├── .env                  # 环境变量配置（需自行创建）
├── run.bat               # Windows 启动脚本
└── reports/              # 报告保存目录
    └── report_*.md       # 生成的报告
```

## 🔧 高级配置

### 修改优先搜索源

编辑 `config.py` 中的 `PRIORITY_SOURCES` 配置：

```python
PRIORITY_SOURCES = {
    "enabled": USE_PRIORITY_SOURCES,
    "organizations": [
        "中国涂料工业协会",
        "中国国家统计局",
        "涂界",
        # 添加更多机构...
    ],
    "keywords_boost": [
        # 添加关键词提升...
    ]
}
```

### 修改搜索超时和结果数量

在 `config.py` 中修改：

```python
SEARCH_TIMEOUT = 10          # 搜索超时时间（秒）
MAX_SEARCH_RESULTS = 20      # 最大搜索结果数量
```

## 🛠️ 开发

### Agent 系统架构

系统包含 4 个主要 Agent：

1. **RequirementAnalyzer** - 需求分析
   - 解析用户需求
   - 提取关键信息
   - 生成搜索策略

2. **InformationCollector** - 信息收集
   - 执行搜索
   - 评估信息可信度
   - 过滤无关信息

3. **ReportWriter** - 报告生成
   - 整合收集的信息
   - 生成结构化报告
   - 格式化输出

4. **QualityJudge** - 质量评审（完整模式）
   - 评估报告质量
   - 识别缺失信息
   - 提供改进建议

### 添加新的搜索引擎

1. 在 `search_engine.py` 中添加新的搜索引擎实现
2. 在 `config.py` 中添加相关配置
3. 更新 `SEARCH_ENGINE_TYPE` 环境变量选项

## ⚡ 性能优化

### 默认性能

- **快速模式**: 约 30-35秒
- **完整模式**: 约 60-90秒

### 性能监控

系统运行后会自动显示性能分析报告，包括：
- 各环节耗时统计
- 时间占比分析
- 优化建议

示例输出：
```
================================================================================
性能分析报告
================================================================================
总耗时: 28.45s

环节名称                         次数     总耗时          占比
--------------------------------------------------------------------------------
步骤4-信息评估                   1        15.23s          53.54%
步骤5-生成报告                   1        4.56s           16.03%
步骤3-执行搜索                   1        3.21s           11.28%
步骤1-需求分析                   1        2.14s           7.52%
--------------------------------------------------------------------------------
```

### 快速优化

如需提速，可修改 `.env` 配置：

```bash
# 性能优化配置
MAX_SEARCH_RESULTS=10    # 减少搜索结果数量（默认20）
SEARCH_TIMEOUT=5         # 减少搜索超时时间（默认10）
```

**预期提速**: 50-70%

详细优化指南请查看：
- 📊 [PERFORMANCE.md](PERFORMANCE.md) - 性能瓶颈分析
- 🚀 [OPTIMIZATION_GUIDE.md](OPTIMIZATION_GUIDE.md) - 优化配置指南

## 🐛 故障排除

### 常见问题

1. **API Key 错误**
   - 检查 `.env` 文件中的 `DEEPSEEK_API_KEY` 是否正确
   - 确认 API Key 有效且有足够的配额

2. **搜索引擎连接失败**
   - 检查 SearXNG 服务是否运行（如使用 SearXNG）
   - 检查 Tavily API Key 是否有效（如使用 Tavily）
   - 检查网络连接

3. **报告生成失败**
   - 检查搜索结果是否为空
   - 查看终端输出的错误信息
   - 尝试使用不同的搜索关键词

4. **程序运行慢**
   - 查看性能分析报告，找出瓶颈
   - 参考 [OPTIMIZATION_GUIDE.md](OPTIMIZATION_GUIDE.md) 进行优化
   - 考虑使用更快的搜索引擎（Tavily）
   - 减少 MAX_SEARCH_RESULTS 配置值

## � 报告元数据与检索系统（NEW）

### 自动元数据生成

从现在开始，每个生成的报告都会自动创建对应的元数据文件：

```
reports/
├── .index.json                          # 全局索引
├── 报告名称_20260105_204258.md         # 报告文件
└── 报告名称_20260105_204258.json       # 元数据文件
```

### 使用报告检索工具

```bash
# 启动交互式检索界面
python report_search.py
```

功能菜单：
1. 🔍 搜索报告 - 按关键词、主题、标签搜索
2. 📚 查看所有主题
3. 🏷️  查看所有标签
4. 📊 统计信息
5. 🔄 重建索引

### Python API使用

```python
from report_metadata import ReportIndex

# 搜索报告
index = ReportIndex()
results = index.search(
    keywords=["汽车", "减产"],
    topic="汽车行业",
    limit=10
)

# 查看结果
for metadata in results:
    print(f"{metadata.title} - {metadata.created_at}")
    print(f"摘要: {metadata.content_summary[:100]}...")
```

详细文档请查看：[REPORT_METADATA_GUIDE.md](REPORT_METADATA_GUIDE.md)

## �📝 许可证

本项目采用 MIT 许可证。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系方式

如有问题或建议，请通过以下方式联系：
- 提交 Issue
- 发送邮件至：[your-email@example.com]

---

**注意**: 使用本系统时请遵守相关法律法规，尊重信息源的版权和使用条款。
