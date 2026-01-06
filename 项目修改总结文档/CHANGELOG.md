# 🚀 AI研究报告生成系统 - 更新日志

## 📦 Version 1.0.0 (2025-01-05)

### ✨ 新功能

#### 🎨 GUI桌面应用
- **框架**：wxPython桌面应用
- **启动**：双击 `启动GUI.bat` 或运行 `python gui_app.py`
- **界面**：4个功能标签 + 菜单栏 + 状态栏

#### 📝 Tab 1: 新建报告
- 研究主题输入
- 搜索模式选择（快速/完整）
- 实时日志显示（重定向所有stdout/stderr）
- 进度条显示
- 后台线程执行，不阻塞UI
- 启动/停止按钮

#### 🔍 Tab 2: 历史报告
- 报告列表显示（文件名、主题、时间、大小）
- 搜索过滤功能
- 打开报告
- 删除报告（含元数据）
- 刷新列表

#### ⚙️ Tab 3: 系统配置
**子标签1：Agent模型配置**
- 4种配置方案：ECONOMY / BALANCED / PREMIUM / CUSTOM
- 5个Agent独立配置：
  - 需求分析师
  - 信息收集员
  - 报告撰写员
  - 质量评审员
  - 综合报告撰写员
- 每个Agent可选：供应商（deepseek/glm/zhipu/openrouter）
- 模型选择
- 推理模式开关

**子标签2：环境变量配置**
- API密钥管理（DeepSeek / Zhipu/GLM / OpenRouter / Tavily）
- SearXNG服务器地址配置
- 密码框保护敏感信息

**子标签3：搜索配置**
- 搜索引擎选择（SearXNG / Tavily）
- 性能优化选项：
  - 跳过信息评估（提速70%）
  - 精简报告输入（提速30%）
  - 优先搜索权威来源
- 并发评估批数（1-10）
- 内容提取长度（500-10000字符）

**配置操作**：
- 保存配置到 .env 文件
- 重新加载配置
- 恢复默认配置

#### 📚 Tab 4: 综合报告
- 综合报告主题输入
- 历史报告多选列表
- 报告整合功能：
  - 提取关键数据
  - 交叉验证信息
  - 处理数据冲突
  - 生成结构化报告
- 辅助功能：全选、清空、刷新
- 进度显示
- 后台线程执行

### 🔧 技术改进

#### 日志系统
- **LogRedirector 类**：捕获 stdout/stderr
- **GUI日志窗口**：实时显示所有输出
- **线程安全**：使用 wx.CallAfter 确保UI更新安全

#### 多线程架构
- **ResearchWorker**：新建报告后台线程
- **ComprehensiveWorker**：综合报告后台线程
- **非阻塞UI**：所有长时间任务在后台执行
- **进度回调**：on_task_start / on_task_complete / on_task_error

#### 配置管理
- **可视化编辑**：所有配置项可通过GUI修改
- **实时验证**：输入框验证
- **持久化存储**：保存到 .env 文件
- **热加载**：重新加载配置无需重启

### 📚 文档
- **GUI使用说明.md**：完整使用指南
- **.env.example**：配置文件模板
- **copilot-instructions.md**：AI代码编辑指南（已更新）

### 🐛 修复
- 修复了日志只显示在终端的问题
- 修复了GUI界面卡顿问题（使用后台线程）
- 修复了配置加载错误

---

## 🔄 升级指南

### 从命令行版本升级

1. **安装依赖**：
```bash
pip install wxpython
```

2. **启动GUI**：
```bash
python gui_app.py
# 或双击 启动GUI.bat
```

3. **配置迁移**：
- 现有的 `.env` 文件会自动加载
- 可在GUI的"系统配置"标签中调整

### 兼容性
- ✅ 完全兼容现有命令行功能
- ✅ `main.py` 可以独立运行
- ✅ 报告格式完全一致
- ✅ 所有Agent和提示词配置保持不变

---

## 📝 待办功能 (Future)

### Phase 6: 高级功能
- [ ] 报告预览功能
- [ ] 导出为PDF/Word格式
- [ ] 报告版本管理
- [ ] 搜索结果预览

### Phase 7: 用户体验
- [ ] 深色/浅色主题切换
- [ ] 自定义图标
- [ ] 任务进度详情（多个子步骤）
- [ ] 报告评分系统

### Phase 8: 性能监控
- [ ] 性能统计图表
- [ ] API调用次数统计
- [ ] 成本估算
- [ ] 缓存机制

---

## 🛠️ 技术栈

- **GUI框架**：wxPython 4.2+
- **Python版本**：≥ 3.8
- **核心依赖**：
  - requests (HTTP客户端)
  - pathlib (路径处理)
  - json (数据序列化)
  - threading (多线程)
  
- **LLM集成**：
  - DeepSeek API
  - Zhipu GLM API
  - OpenRouter API
  
- **搜索引擎**：
  - SearXNG (本地部署)
  - Tavily (云端服务)

---

## 👥 贡献者

- AI Assistant (开发者)
- User (需求提供者 & 测试者)

---

## 📄 许可证

MIT License

---

## 🙏 致谢

感谢以下开源项目：
- wxPython
- DeepSeek
- Zhipu AI
- OpenRouter
- SearXNG
- Tavily

---

**上次更新**：2025-01-05  
**当前版本**：1.0.0
