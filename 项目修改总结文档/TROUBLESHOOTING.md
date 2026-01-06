# 常见问题排查指南

## 网络相关错误

### WSALookupServiceBegin failed with: 0

**错误信息**:
```
[21752:0106/210114.432:ERROR:network_change_notifier_win.cc(267)] WSALookupServiceBegin failed with: 0
```

**原因**:
- 这是 Windows 操作系统的网络状态通知服务错误
- 通常在 Chromium 内核的浏览器（如系统打开 Markdown 文件）启动时出现
- 是 Windows 10/11 的已知问题，与 IPv6 或网络适配器配置有关

**影响**:
- ❌ **不影响程序功能**
- ❌ **不影响报告生成**
- ❌ **不影响文件保存**
- ✅ 只是一个警告信息，可以安全忽略

**解决方案**:

1. **忽略它**（推荐）
   - 这个错误不影响任何功能，可以直接忽略

2. **禁用自动打开报告**
   - 在代码中设置 `auto_open=False`
   - 或者手动打开保存的报告文件

3. **系统级修复**（可选）
   ```powershell
   # 以管理员身份运行 PowerShell
   # 重置网络适配器
   netsh winsock reset
   netsh int ip reset
   # 重启电脑
   ```

---

## SSL 证书验证错误

**错误信息**:
```
[警告] 获取网页内容失败: SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED]'))
```

**原因**:
- 目标网站的 SSL 证书过期或无效
- 网络代理干扰证书验证
- 系统缺少根证书

**解决方案**:

1. **正常情况**
   - 程序会自动跳过该网站，继续搜索其他来源
   - 不影响整体功能

2. **如果大量出现**
   - 检查是否使用了代理
   - 检查系统时间是否正确
   - 更新系统根证书

---

## API 调用失败

### Rate Limit Exceeded

**错误信息**:
```
❌ [Agent名称] API调用失败: Rate limit exceeded
```

**解决方案**:
1. 降低并发评估数：在 `.env` 中设置 `MAX_CONCURRENT_EVALUATIONS=1`
2. 检查 API 额度是否充足
3. 等待几分钟后重试

### API Key Invalid

**错误信息**:
```
❌ [Agent名称] API调用失败: Invalid API key
```

**解决方案**:
1. 检查 `.env` 文件中的 API 密钥是否正确
2. 确认 API 密钥未过期
3. 验证 API 密钥的格式（无多余空格）

---

## 搜索引擎问题

### SearXNG 连接失败

**错误信息**:
```
❌ SearXNG 搜索失败: Connection refused
```

**解决方案**:
1. 确认 SearXNG 是否正在运行
2. 检查 `.env` 中的 `SEARXNG_BASE_URL` 配置
3. 或切换到 Tavily: `SEARCH_ENGINE_TYPE=tavily`

---

## 日志输出问题

### 日志太多，看不到关键信息

**解决方案**:
在 `.env` 中设置：
```env
LOG_LEVEL=normal          # 正常模式（推荐）
PRINT_FINAL_REPORT=false  # 不打印报告全文
```

### 需要查看详细调试信息

**解决方案**:
在 `.env` 中设置：
```env
LOG_LEVEL=verbose         # 详细模式
PRINT_FINAL_REPORT=true   # 打印报告全文
```

### 只想看核心进度

**解决方案**:
在 `.env` 中设置：
```env
LOG_LEVEL=minimal         # 精简模式
PRINT_FINAL_REPORT=false  # 不打印报告全文
```

---

## 性能问题

### 运行太慢

**解决方案**:
1. 启用并发评估：
   ```env
   MAX_CONCURRENT_EVALUATIONS=3
   ```

2. 精简内容提取：
   ```env
   CONTENT_EXTRACT_LENGTH=1500
   ```

3. 跳过评估（极速模式）：
   ```env
   SKIP_EVALUATION=true
   ```

4. 使用快速搜索：
   ```env
   SEARCH_MODE=quick
   ```

### API 调用超时

**解决方案**:
1. 检查网络连接
2. 尝试更换 LLM 供应商
3. 降低并发数

---

## 模型配置问题

### 不知道使用了什么模型

**解决方案**:
```bash
python agent_config.py
```
会显示每个 Agent 使用的具体模型。

### 想要更改模型

**解决方案**:

**方式1**: 编辑 `agent_config.py`
```python
AGENT_CONFIG_PRESET = "balanced"  # economy/balanced/premium/custom
```

**方式2**: 在 `.env` 中指定
```env
REQUIREMENT_ANALYZER_PROVIDER=glm
REQUIREMENT_ANALYZER_MODEL=glm-4.7
```

---

## 报告质量问题

### 报告内容不完整

**解决方案**:
1. 使用完整搜索模式：
   ```env
   SEARCH_MODE=full
   MAX_LOOP_COUNT=3
   ```

2. 增加内容提取长度：
   ```env
   CONTENT_EXTRACT_LENGTH=4000
   ```

3. 不跳过评估：
   ```env
   SKIP_EVALUATION=false
   ```

### 报告质量不高

**解决方案**:
1. 使用高端配置方案：
   ```python
   # agent_config.py
   AGENT_CONFIG_PRESET = "premium"
   ```

2. 使用推理模型：
   - 报告撰写员会自动使用推理模式
   - 在 `agent_config.py` 中设置 `use_reasoner=True`

---

## 文件和路径问题

### 找不到报告文件

**位置**:
- 报告保存在 `reports/` 目录下
- 文件名格式：`{主题}_{时间戳}.md`
- 元数据：`{主题}_{时间戳}.json`

**解决方案**:
```bash
# 查看所有报告
ls reports/

# 搜索特定报告
python main.py
# 选择模式 3（报告检索工具）
```

---

## 获取更多帮助

### 查看配置文档
- `AGENT_CONFIG_GUIDE.md` - Agent 配置详细指南
- `MODEL_SELECTION_GUIDE.md` - 模型选择指南
- `QUICK_REFERENCE.txt` - 快速参考卡
- `LLM_PROVIDERS_GUIDE.md` - 供应商使用指南

### 测试工具
```bash
# 测试所有模型连接
python test_all_models.py

# 查看当前配置
python agent_config.py

# 测试供应商功能
python test_llm_providers.py
```

### 联系支持
- GitHub Issues: [项目仓库地址]
- 文档: [文档地址]
