# 更新日志 - 2026年1月6日

## 🎉 重要更新

### 1. GLM 默认模型配置优化

**变更内容**:
- ✅ GLM 默认模型改为 `glm-4.7`（之前是 `glm-4-flash`）
- ✅ 支持通过环境变量配置 GLM 模型

**配置方式**:

在 `.env` 文件中添加：
```env
# 智谱AI (GLM-4) API配置
ZHIPU_API_KEY=your_api_key_here
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4

# 可选：自定义模型（默认值已优化）
ZHIPU_DEFAULT_MODEL=glm-4.7        # 默认模型
ZHIPU_ADVANCED_MODEL=glm-4-plus    # 高级模型（use_reasoner时使用）
```

**影响的文件**:
- `.env.example` - 添加配置说明
- `llm_providers.py` - 支持环境变量读取模型名称

---

### 2. 日志输出精简和美化 🎨

**问题**: 之前日志输出过多，包括：
- 详细的 API 调用信息
- 提供商和模型详情
- 最终报告全文打印
- 导致控制台刷屏，难以看到关键信息

**解决方案**: 新增日志级别控制

#### 配置选项

在 `.env` 文件中设置：

```env
# 日志输出级别
LOG_LEVEL=normal          # verbose/normal/minimal

# 是否打印最终报告到控制台
PRINT_FINAL_REPORT=false  # true/false
```

#### 三种日志级别

**verbose（详细模式）**:
- 显示所有 API 调用详情
- 显示提供商和模型信息
- 显示思考过程（推理模型）
- 显示 API 调用耗时
- 适合：调试和问题排查

**normal（正常模式）** ⭐ 推荐:
- 显示关键步骤进度
- 显示重要结果汇总
- 推理模式有提示
- 隐藏 API 调用细节
- 适合：日常使用

**minimal（精简模式）**:
- 只显示核心进度
- 最少的输出信息
- 适合：自动化运行

#### 报告打印控制

**PRINT_FINAL_REPORT=false** （推荐）:
- ✅ 不在控制台打印报告全文
- ✅ 避免刷屏
- ✅ 报告仍然保存到文件
- ✅ 自动打开文件查看

**PRINT_FINAL_REPORT=true**:
- 在控制台打印报告全文
- 适合需要立即查看内容的场景

#### 优化的输出示例

**Before（之前）**:
```
[步骤1] 需求分析师正在分析需求...
  [需求分析师] 提供商: OPENROUTER, 模型: xiaomi/mimo-v2-flash:free
  [需求分析师] API调用耗时: 4.00秒
  [需求分析师] API调用耗时: 4.00秒  # 重复
✓ 需求分析完成 (耗时: 4.00秒)

[步骤5] 报告撰写员正在生成Markdown报告...
  [报告撰写员] 使用思考模式进行深度分析...
  [报告撰写员] 提供商: OPENROUTER, 模型: xiaomi/mimo-v2-flash:free
  [报告撰写员] API调用耗时: 13.43秒
✓ 报告生成完成！（耗时: 13.43秒）

============================================================
最终报告（Markdown格式）
============================================================
# 2024年中国船舶涂料市场销售额研究报告
[... 大量报告内容，刷屏...]
============================================================
```

**After（现在 - normal模式）**:
```
[步骤1] 深度分析需求...
  💡 需求分析师使用推理模式分析中...
✓ 需求分析完成 (耗时: 4.00秒)

[步骤5] 生成报告...
  💡 报告撰写员使用推理模式分析中...
✓ 报告生成完成！（耗时: 13.43秒）

✅ 报告生成完成（已跳过控制台打印，避免刷屏）

💾 正在保存报告...
报告已保存到: reports\2024年中国船舶涂料销售额_20260106_210114.md
```

**影响的文件**:
- `config.py` - 添加 `LOG_LEVEL` 和 `PRINT_FINAL_REPORT` 配置
- `.env.example` - 添加日志配置说明
- `agents.py` - `BaseAgent.call_llm()` 根据日志级别输出
- `main.py` - 控制最终报告打印

---

### 3. 网络错误说明文档 📝

**问题**: 用户看到网络错误，不知道是否影响功能
```
[21752:0106/210114.432:ERROR:network_change_notifier_win.cc(267)] WSALookupServiceBegin failed with: 0
```

**解决方案**: 创建详细的问题排查指南

#### 新增文件: `TROUBLESHOOTING.md`

包含以下内容：
1. **网络相关错误**
   - WSALookupServiceBegin 错误说明（不影响功能）
   - SSL 证书验证错误处理

2. **API 调用失败**
   - Rate Limit 处理方案
   - API Key 无效的排查

3. **搜索引擎问题**
   - SearXNG 连接失败
   - Tavily 配置问题

4. **日志输出问题**
   - 如何精简日志
   - 如何查看详细信息

5. **性能问题**
   - 运行太慢的优化方案
   - API 超时处理

6. **模型配置问题**
   - 如何查看当前模型
   - 如何更改模型配置

7. **报告质量问题**
   - 内容不完整的解决方案
   - 质量提升技巧

8. **文件和路径问题**
   - 报告保存位置
   - 如何检索历史报告

**特别说明 WSALookupServiceBegin 错误**:
- ❌ **不影响程序功能**
- ❌ **不影响报告生成**  
- ❌ **不影响文件保存**
- ✅ 只是 Windows 的网络状态通知服务警告
- ✅ 可以安全忽略
- ✅ 是 Chromium 浏览器打开 Markdown 文件时的已知问题

---

## 📋 更新文件清单

### 配置文件
- ✅ `.env.example` - 添加 GLM 模型配置和日志级别配置
- ✅ `config.py` - 添加 LOG_LEVEL 和 PRINT_FINAL_REPORT

### 核心代码
- ✅ `llm_providers.py` - ZhipuProvider 支持环境变量配置模型
- ✅ `agents.py` - BaseAgent.call_llm() 支持日志级别控制
- ✅ `main.py` - 控制最终报告打印

### 文档
- ✅ `TROUBLESHOOTING.md` - 新增问题排查指南
- ✅ `UPDATE_LOG_20260106.md` - 本更新日志

---

## 🚀 使用建议

### 推荐配置（日常使用）

在 `.env` 文件中：
```env
# GLM 配置（使用优化后的默认值）
ZHIPU_API_KEY=your_api_key_here
ZHIPU_DEFAULT_MODEL=glm-4.7

# 日志配置（推荐设置）
LOG_LEVEL=normal              # 正常模式，关键信息清晰
PRINT_FINAL_REPORT=false      # 不打印报告，避免刷屏

# 性能配置
MAX_CONCURRENT_EVALUATIONS=3  # 并发评估，提速
CONTENT_EXTRACT_LENGTH=2000   # 数据完整性
SEARCH_MODE=quick             # 快速模式
```

### 调试配置（问题排查）

```env
LOG_LEVEL=verbose             # 详细模式，看所有细节
PRINT_FINAL_REPORT=true       # 打印报告内容
```

### 极简配置（自动化）

```env
LOG_LEVEL=minimal             # 精简模式，最少输出
PRINT_FINAL_REPORT=false      # 不打印报告
```

---

## ✅ 验证方法

### 1. 测试 GLM 模型配置
```bash
python agent_config.py
# 查看 GLM 的默认模型是否为 glm-4.7
```

### 2. 测试日志级别
```bash
# 编辑 .env，设置 LOG_LEVEL=normal
python main.py
# 观察输出是否精简，无 API 调用详情

# 编辑 .env，设置 LOG_LEVEL=verbose
python main.py
# 观察输出是否包含详细的 API 信息
```

### 3. 测试报告打印
```bash
# 编辑 .env，设置 PRINT_FINAL_REPORT=false
python main.py
# 报告不在控制台打印，只显示 "已跳过控制台打印"

# 编辑 .env，设置 PRINT_FINAL_REPORT=true
python main.py
# 报告全文在控制台打印
```

---

## 🔧 如何回滚（如果需要）

如果不适应新的日志模式，可以：

1. **恢复详细日志**:
   ```env
   LOG_LEVEL=verbose
   PRINT_FINAL_REPORT=true
   ```

2. **恢复之前的 GLM 模型**:
   ```env
   ZHIPU_DEFAULT_MODEL=glm-4-flash
   ```

---

## 📞 问题反馈

如遇到问题：
1. 查看 `TROUBLESHOOTING.md` 排查常见问题
2. 设置 `LOG_LEVEL=verbose` 查看详细日志
3. 运行测试工具诊断：
   ```bash
   python test_all_models.py      # 测试模型连接
   python agent_config.py          # 查看配置
   ```

---

## 🎯 下一步计划

1. [ ] 添加日志文件输出功能（verbose 日志写入文件）
2. [ ] 添加彩色日志支持（区分不同级别）
3. [ ] 优化错误提示信息
4. [ ] 添加进度条显示

---

**更新时间**: 2026年1月6日 21:30
**版本**: v2.1.0
