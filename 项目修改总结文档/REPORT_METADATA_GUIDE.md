# 报告元数据与检索系统

## 🎯 功能概述

从现在开始，每个生成的报告都会自动创建对应的元数据文件，支持：
- ✅ 按关键词、主题、标签搜索历史报告
- ✅ 查看报告摘要和详细信息
- ✅ 统计分析报告库
- ✅ 为未来的综合报告功能打好基础

## 📁 文件结构

```
reports/
├── .index.json                                    # 📇 全局索引文件
├── 2025汽车减产_20260105_204258.md              # 📄 报告文件
├── 2025汽车减产_20260105_204258.json            # 🏷️  元数据文件
└── ...
```

### 元数据JSON结构

```json
{
  "report_id": "uuid",
  "title": "2025年中国汽车主机厂减产情况",
  "topic": "汽车行业",
  "content_summary": "本报告分析了2025年中国汽车行业...",
  "keywords": ["减产", "汽车", "主机厂", "2025"],
  "tags": ["汽车行业", "市场分析"],
  "data_sources": [
    {"url": "...", "title": "...", "credibility": 8}
  ],
  "search_keywords": ["2025汽车减产", "主机厂销量"],
  "created_at": "2026-01-05 20:42:58",
  "file_path": "reports/2025汽车减产_20260105_204258.md"
}
```

## 🚀 使用方法

### 方式1：命令行检索工具

```bash
# 启动交互式检索界面
python report_search.py
```

**功能菜单**：
1. 🔍 搜索报告 - 按关键词、主题、标签搜索
2. 📚 查看所有主题 - 列出所有报告主题
3. 🏷️  查看所有标签 - 列出所有标签
4. 📊 统计信息 - 查看报告库统计
5. 🔄 重建索引 - 扫描reports目录重建索引

### 方式2：Python API

```python
from report_metadata import ReportIndex

# 初始化索引
index = ReportIndex()

# 搜索报告
results = index.search(
    keywords=["汽车", "减产"],
    topic="汽车行业",
    tags=["市场分析"],
    limit=10
)

# 遍历结果
for metadata in results:
    print(f"标题: {metadata.title}")
    print(f"摘要: {metadata.content_summary}")
    print(f"文件: {metadata.file_path}")
    print("---")

# 读取报告内容
content = index.get_report_content(metadata.report_id)
print(content)

# 统计信息
stats = index.get_statistics()
print(f"总报告数: {stats['total_reports']}")
print(f"主题: {stats['topics']}")
print(f"标签: {stats['tags']}")
```

## 🔍 搜索示例

### 示例1：按关键词搜索

```python
# 搜索包含"减产"或"销量"的报告
results = index.search(keywords=["减产", "销量"], limit=5)
```

### 示例2：按主题搜索

```python
# 搜索汽车行业相关报告
results = index.search(topic="汽车行业")
```

### 示例3：按标签搜索

```python
# 搜索有"市场分析"或"2025年"标签的报告
results = index.search(tags=["市场分析", "2025年"])
```

### 示例4：组合搜索

```python
# 组合多个条件
results = index.search(
    keywords=["新能源", "销量"],
    topic="汽车行业",
    tags=["市场分析"],
    start_date="2026-01-01",
    end_date="2026-01-31"
)
```

## 📊 相关度评分规则

搜索结果会自动按相关度排序，评分规则：

| 匹配位置 | 完全匹配 | 部分匹配 |
|---------|---------|---------|
| 标题 | +10分 | +5分 |
| 关键词列表 | - | +3分/个 |
| 摘要 | - | +2分/个 |
| 主题 | - | +8分 |
| 标签 | - | +5分/个 |

## 🔧 管理功能

### 重建索引

如果索引文件损坏或需要更新：

```python
index = ReportIndex()
index.rebuild_index()
```

或使用命令行工具：
```bash
python report_search.py
# 选择 "5. 重建索引"
```

### 手动添加报告到索引

```python
from report_metadata import ReportMetadata, ReportIndex

# 创建元数据
metadata = ReportMetadata(
    title="报告标题",
    topic="主题",
    content_summary="摘要内容...",
    keywords=["关键词1", "关键词2"],
    tags=["标签1", "标签2"],
    file_path="reports/report.md"
)

# 保存元数据文件
metadata.save_to_file()

# 添加到索引
index = ReportIndex()
index.add_report(metadata)
```

## 🎨 标签设计建议

建议使用以下标签结构：

### 行业标签
- 汽车行业、电子行业、化工行业、金融行业等

### 类型标签
- 市场分析、竞争格局、技术趋势、政策研究等

### 时间标签
- 2025年、2026年、近五年等

### 地域标签
- 中国、美国、全球、华东地区等

## 📝 自动元数据生成

现在每次运行 `main.py` 生成报告时，系统会自动：

1. ✅ 从报告内容中提取标题和摘要
2. ✅ 从需求分析结果中提取关键词
3. ✅ 从搜索结果中提取数据来源
4. ✅ 根据主题自动生成标签
5. ✅ 保存元数据JSON文件
6. ✅ 更新全局索引

**无需手动操作，一切自动完成！**

## 🔮 未来功能预告

基于此元数据系统，即将推出：

### 阶段3：综合报告制作模式（开发中）

```
单次调研 → 报告A.md (关于主题1的方面A)
单次调研 → 报告B.md (关于主题1的方面B)
单次调研 → 报告C.md (关于主题1的方面C)
   ↓
综合调研报告制作
   ↓
输入: 报告主题/纲要/初稿
   ↓
AI分析 → 自动检索相关报告 → 整合分析 → 生成综合报告
```

功能特性：
- 🔍 自动检索相关历史报告
- 🧠 深度分析发现新洞察
- ✅ 交叉验证去重矛盾信息
- 📊 支持Markdown/Word/PDF初稿输入
- 🎯 手动选择或自动关联报告

## 🐛 故障排除

### Q: 索引文件丢失怎么办？
A: 运行 `python report_search.py`，选择"重建索引"，系统会自动扫描reports目录下所有JSON文件重建索引。

### Q: 如何为历史报告补充元数据？
A: 
1. 确保reports目录有Markdown文件
2. 运行 `python report_search.py`
3. 选择"重建索引"
4. 如果没有JSON文件，需要手动创建或重新生成报告

### Q: 搜索不到报告？
A: 
1. 检查 `.index.json` 是否存在
2. 运行"重建索引"
3. 确认JSON元数据文件格式正确

## 📞 技术支持

遇到问题？查看：
- `report_metadata.py` - 元数据核心模块
- `report_search.py` - 检索工具源码
- `main.py` 中的 `_save_report_metadata()` 方法

---

**版本**: v2.0  
**更新时间**: 2026-01-05  
**状态**: ✅ 阶段1-2完成，阶段3开发中
