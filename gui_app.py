"""
AI研究报告生成系统 - wxPython GUI界面
"""
import wx
import wx.lib.scrolledpanel as scrolled
import threading
import queue
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from io import StringIO
from time_utils import beijing_now_str

# 导入现有的业务逻辑
from main import ResearchAgentSystem
import config
from agent_config import get_active_agent_config
from runtime_config import load_runtime_config, save_runtime_config, get_runtime_config_path


class LogRedirector:
    """日志重定向器 - 将print输出重定向到GUI"""
    
    def __init__(self, text_widget, log_type='stdout'):
        self.text_widget = text_widget
        self.log_type = log_type
        self._buffer = StringIO()
        self._line_buffer = ""  # 缓存不完整的行
        
    def write(self, message):
        """写入消息"""
        if not message:
            return
            
        # 累积到行缓冲区
        self._line_buffer += message
        
        # 如果包含换行符，处理完整的行
        if '\n' in self._line_buffer:
            lines = self._line_buffer.split('\n')
            # 最后一个可能是不完整的行
            self._line_buffer = lines[-1]
            
            # 处理完整的行
            for line in lines[:-1]:
                if line.strip():  # 忽略空行
                    wx.CallAfter(self._append_text, line + '\n')
        
        self._buffer.write(message)
        
    def _append_text(self, message):
        """在GUI线程中添加文本"""
        if self.text_widget:
            try:
                self.text_widget.AppendText(message)
                # 自动滚动到最新内容
                self.text_widget.ShowPosition(self.text_widget.GetLastPosition())
            except:
                pass  # 如果窗口已关闭，忽略错误
            
    def flush(self):
        """刷新缓冲区"""
        if self._line_buffer.strip():
            wx.CallAfter(self._append_text, self._line_buffer + '\n')
            self._line_buffer = ""


LOG_ROUTER_OUT = None
LOG_ROUTER_ERR = None

class LogRouter:
    """Route stdout/stderr to per-thread log widgets."""
    def __init__(self, fallback, log_type='stdout'):
        self._fallback = fallback
        self.log_type = log_type
        self._targets = {}
        self._buffers = {}
        self._lock = threading.Lock()

    def register(self, thread_id, widget):
        if widget is None:
            return
        with self._lock:
            self._targets[thread_id] = widget
            self._buffers.setdefault(thread_id, '')

    def unregister(self, thread_id):
        with self._lock:
            self._targets.pop(thread_id, None)
            self._buffers.pop(thread_id, None)

    def write(self, message):
        if not message:
            return
        thread_id = threading.get_ident()
        with self._lock:
            widget = self._targets.get(thread_id)
            if widget is None and len(self._targets) == 1:
                widget = next(iter(self._targets.values()))
            if widget is None:
                fallback = self._fallback
            else:
                buffer = self._buffers.get(thread_id, '')
                buffer += message
                if '\n' in buffer:
                    lines = buffer.split('\n')
                    self._buffers[thread_id] = lines[-1]
                    for line in lines[:-1]:
                        if line.strip():
                            wx.CallAfter(self._append_text, widget, line + '\n')
                else:
                    self._buffers[thread_id] = buffer
                fallback = None
        if fallback:
            try:
                fallback.write(message)
                fallback.flush()
            except Exception:
                pass

    def flush(self):
        thread_id = threading.get_ident()
        with self._lock:
            widget = self._targets.get(thread_id)
            if widget:
                buffer = self._buffers.get(thread_id, '')
                if buffer.strip():
                    wx.CallAfter(self._append_text, widget, buffer + '\n')
                    self._buffers[thread_id] = ''
        if self._fallback:
            try:
                self._fallback.flush()
            except Exception:
                pass

    @staticmethod
    def _append_text(widget, message):
        if widget:
            try:
                widget.AppendText(message)
                widget.ShowPosition(widget.GetLastPosition())
            except Exception:
                pass

def init_log_routers():
    global LOG_ROUTER_OUT, LOG_ROUTER_ERR
    if LOG_ROUTER_OUT is None:
        LOG_ROUTER_OUT = LogRouter(sys.__stdout__, 'stdout')
        LOG_ROUTER_ERR = LogRouter(sys.__stderr__, 'stderr')
        sys.stdout = LOG_ROUTER_OUT
        sys.stderr = LOG_ROUTER_ERR


class ResearchWorker(threading.Thread):
    """后台工作线程 - 执行报告生成任务"""
    
    def __init__(self, parent, requirement, search_mode='full', task_id=None):
        super().__init__()
        self.parent = parent
        self.requirement = requirement
        self.search_mode = search_mode
        self.task_id = task_id  # 添加任务ID
        self.daemon = True
        self._stop_event = threading.Event()
        
    def run(self):
        """执行报告生成"""
        try:
            # Register per-thread log target to avoid cross-task log mixing.
            thread_id = threading.get_ident()
            log_widget = self.parent.log_text
            if LOG_ROUTER_OUT:
                LOG_ROUTER_OUT.register(thread_id, log_widget)
            if LOG_ROUTER_ERR:
                LOG_ROUTER_ERR.register(thread_id, log_widget)
            
            # 发送开始信号
            wx.CallAfter(self.parent.on_task_start)
            
            # 打印任务信息（添加分隔符和任务ID）
            if self.task_id:
                print(f"\n{'='*60}")
                print(f"🚀 任务 #{self.task_id} 开始执行")
                print(f"{'='*60}\n")
            
            # 创建系统实例
            system = ResearchAgentSystem()
            
            # 根据模式生成报告
            if self.search_mode == 'quick':
                print("📌 使用快速搜索模式")
                report = system.quick_search(self.requirement)
            else:
                print("📌 使用完整搜索模式")
                report = system.process_requirement(self.requirement)
            
            # 保存报告
            analysis_result = system.context.get('analysis_result')
            search_keywords = None
            if system.context.get('search_history'):
                search_keywords = system.context['search_history'][0].get('keywords', [])
            
            print("\n💾 正在保存报告...")
            system.save_report(
                report, 
                auto_open=True, 
                topic=self.requirement,
                analysis_result=analysis_result,
                search_keywords=search_keywords
            )
            
            print(f"\n{'='*60}")
            print(f"✅ 任务 #{self.task_id if self.task_id else ''} 完成")
            print(f"{'='*60}\n")
            
            if LOG_ROUTER_OUT:
                LOG_ROUTER_OUT.unregister(threading.get_ident())
            if LOG_ROUTER_ERR:
                LOG_ROUTER_ERR.unregister(threading.get_ident())
            
            # 发送完成信号
            wx.CallAfter(self.parent.on_task_complete, report)
            
        except Exception as e:
            if LOG_ROUTER_OUT:
                LOG_ROUTER_OUT.unregister(threading.get_ident())
            if LOG_ROUTER_ERR:
                LOG_ROUTER_ERR.unregister(threading.get_ident())
            wx.CallAfter(self.parent.on_task_error, str(e))
            
    def stop(self):
        """停止任务"""
        self._stop_event.set()


class ComprehensiveWorker(threading.Thread):
    """综合报告生成工作线程"""
    
    def __init__(self, parent, topic, report_paths):
        super().__init__()
        self.parent = parent
        self.topic = topic
        self.report_paths = report_paths
        self.daemon = True
        
    def run(self):
        """执行综合报告生成"""
        try:
            # Register per-thread log target to avoid cross-task log mixing.
            thread_id = threading.get_ident()
            log_widget = self.parent.log_text
            if LOG_ROUTER_OUT:
                LOG_ROUTER_OUT.register(thread_id, log_widget)
            if LOG_ROUTER_ERR:
                LOG_ROUTER_ERR.register(thread_id, log_widget)
            
            # 发送开始信号
            wx.CallAfter(self.parent.on_task_start)
            
            print(f"\n{'='*60}")
            print(f"🚀 开始生成综合报告")
            print(f"📋 主题: {self.topic}")
            print(f"📚 报告数量: {len(self.report_paths)}")
            print(f"{'='*60}\n")
            
            # 读取所有报告内容
            print("📖 正在读取报告内容...")
            reports_data = []
            for idx, path in enumerate(self.report_paths, 1):
                try:
                    print(f"  [{idx}/{len(self.report_paths)}] {path.name}")
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # 简单解析元数据（从文件名和内容）
                        from collections import namedtuple
                        Metadata = namedtuple('Metadata', ['title', 'topic', 'keywords', 'tags', 'content_summary', 'created_at'])
                        
                        # 从文件名提取主题
                        topic_from_filename = path.stem.rsplit('_', 2)[0] if '_' in path.stem else path.stem
                        
                        # 获取创建时间
                        import os
                        created_at = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                        
                        # 提取内容摘要（前500字符）
                        content_summary = content[:500].replace('\n', ' ') if content else ""
                        
                        metadata = Metadata(
                            title=path.name,
                            topic=topic_from_filename,
                            keywords=[],
                            tags=[],
                            content_summary=content_summary,
                            created_at=created_at
                        )
                        
                        reports_data.append({
                            'filename': path.name,
                            'content': content,
                            'path': str(path),
                            'metadata': metadata
                        })
                except Exception as e:
                    print(f"❌ 读取报告失败 {path}: {e}")
            
            print(f"\n✅ 成功读取 {len(reports_data)} 个报告")
            print("\n🤖 正在调用AI生成综合报告...")
            
            # 使用ComprehensiveReportWriter生成综合报告
            from agents import ComprehensiveReportWriter
            
            writer = ComprehensiveReportWriter(
                system_datetime=beijing_now_str()
            )
            
            # 准备用户输入
            user_input = f"请基于以下{len(reports_data)}个历史报告，生成关于'{self.topic}'的综合分析报告"
            
            # 调用正确的方法：analyze_and_integrate
            result = writer.analyze_and_integrate(
                user_input=user_input,
                related_reports=reports_data,
                outline_file=None
            )
            
            # 提取综合报告内容
            comprehensive_report = result.get('comprehensive_report', '')
            if not comprehensive_report:
                raise Exception("综合报告生成失败：返回内容为空")
            
            # 保存报告
            from main import ResearchAgentSystem
            system = ResearchAgentSystem()
            
            # 生成干净的文件名
            clean_topic = "".join(c for c in self.topic if c.isalnum() or c in (' ', '_', '-'))[:50]
            timestamp = beijing_now_str("%Y%m%d_%H%M%S")
            filename = f"综合报告_{clean_topic}_{timestamp}.md"
            
            reports_dir = Path("reports")
            reports_dir.mkdir(exist_ok=True)
            filepath = reports_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(comprehensive_report)
            
            print(f"\n{'='*60}")
            print(f"✅ 综合报告生成完成")
            print(f"📁 保存位置: {filepath}")
            print(f"{'='*60}\n")
            
            # 打开报告
            os.startfile(filepath)
            
            if LOG_ROUTER_OUT:
                LOG_ROUTER_OUT.unregister(threading.get_ident())
            if LOG_ROUTER_ERR:
                LOG_ROUTER_ERR.unregister(threading.get_ident())
            
            # 发送完成信号
            wx.CallAfter(self.parent.on_task_complete, comprehensive_report)
            
        except Exception as e:
            if LOG_ROUTER_OUT:
                LOG_ROUTER_OUT.unregister(threading.get_ident())
            if LOG_ROUTER_ERR:
                LOG_ROUTER_ERR.unregister(threading.get_ident())
            wx.CallAfter(self.parent.on_task_error, str(e))
class TaskPanel(wx.Panel):
    """单个任务面板"""
    
    def __init__(self, parent, task_id, on_close_callback=None):
        super().__init__(parent)
        self.task_id = task_id
        self.worker = None
        self.on_close_callback = on_close_callback
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 顶部工具栏
        toolbar_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # 任务ID标签
        task_label = wx.StaticText(self, label=f"任务 #{self.task_id}")
        task_label_font = task_label.GetFont()
        task_label_font = task_label_font.Bold()
        task_label.SetFont(task_label_font)
        toolbar_sizer.Add(task_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        
        # 按钮
        self.start_btn = wx.Button(self, label="▶️ 开始", size=(80, -1))
        self.start_btn.Bind(wx.EVT_BUTTON, self.on_start)
        toolbar_sizer.Add(self.start_btn, 0, wx.RIGHT, 5)
        
        self.stop_btn = wx.Button(self, label="⏹️ 停止", size=(80, -1))
        self.stop_btn.Enable(False)
        self.stop_btn.Bind(wx.EVT_BUTTON, self.on_stop)
        toolbar_sizer.Add(self.stop_btn, 0, wx.RIGHT, 5)
        
        self.close_btn = wx.Button(self, label="❌ 关闭", size=(80, -1))
        self.close_btn.Bind(wx.EVT_BUTTON, self.on_close)
        toolbar_sizer.Add(self.close_btn, 0)
        
        main_sizer.Add(toolbar_sizer, 0, wx.ALL, 5)
        
        # 研究主题
        topic_sizer = wx.BoxSizer(wx.HORIZONTAL)
        topic_sizer.Add(wx.StaticText(self, label="主题:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.topic_input = wx.TextCtrl(self, value="", size=(400, -1))
        topic_sizer.Add(self.topic_input, 1)
        main_sizer.Add(topic_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # 配置选项（紧凑型）
        config_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.mode_quick = wx.RadioButton(self, label="快速", style=wx.RB_GROUP)
        self.mode_full = wx.RadioButton(self, label="完整")
        self.mode_full.SetValue(True)
        config_sizer.Add(self.mode_quick, 0, wx.RIGHT, 10)
        config_sizer.Add(self.mode_full, 0, wx.RIGHT, 20)
        
        main_sizer.Add(config_sizer, 0, wx.ALL, 5)
        
        # 进度
        self.progress_label = wx.StaticText(self, label="⏱️ 等待开始...")
        main_sizer.Add(self.progress_label, 0, wx.ALL, 5)
        
        self.progress_bar = wx.Gauge(self, range=100, size=(-1, 15))
        main_sizer.Add(self.progress_bar, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        
        # 日志
        log_label = wx.StaticText(self, label="📋 实时日志")
        main_sizer.Add(log_label, 0, wx.ALL, 5)
        
        self.log_text = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.TE_WORDWRAP,
            size=(-1, 150)
        )
        
        # 设置等宽字体，提升可读性
        font = wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.log_text.SetFont(font)
        
        # 设置背景色和文字颜色
        self.log_text.SetBackgroundColour(wx.Colour(245, 245, 245))
        self.log_text.SetForegroundColour(wx.Colour(33, 33, 33))
        
        main_sizer.Add(self.log_text, 1, wx.EXPAND | wx.ALL, 5)
        
        self.SetSizer(main_sizer)
        
    def on_start(self, event):
        """开始任务"""
        topic = self.topic_input.GetValue().strip()
        if not topic:
            wx.MessageBox("请输入研究主题", "提示", wx.OK | wx.ICON_WARNING)
            return
        
        search_mode = 'quick' if self.mode_quick.GetValue() else 'full'
        
        # 清空日志
        self.log_text.Clear()
        self.update_log(f"🎯 任务 #{self.task_id} 准备启动")
        self.update_log(f"📋 主题: {topic}")
        self.update_log(f"⚙️ 模式: {'快速搜索' if search_mode == 'quick' else '完整搜索'}")
        self.update_log(f"{'─'*60}")
        
        # 更新按钮状态
        self.start_btn.Enable(False)
        self.stop_btn.Enable(True)
        self.topic_input.Enable(False)
        
        # 重置进度
        self.progress_bar.SetValue(0)
        self.progress_label.SetLabel("⏱️ 进行中...")
        
        # 启动后台线程，传递任务ID
        self.worker = ResearchWorker(self, topic, search_mode, task_id=self.task_id)
        self.worker.start()
        
    def on_stop(self, event):
        """停止任务"""
        if self.worker:
            self.worker.stop()
            self.update_log(f"{'─'*60}")
            self.update_log(f"⏹️ 正在停止任务 #{self.task_id}...")
            self.update_log(f"{'─'*60}")
            self.on_task_complete("任务已停止")
            
    def on_close(self, event):
        """关闭任务标签"""
        if self.worker and self.worker.is_alive():
            dlg = wx.MessageDialog(
                self,
                "任务正在运行中，确定要关闭吗？",
                "确认关闭",
                wx.YES_NO | wx.ICON_QUESTION
            )
            if dlg.ShowModal() == wx.ID_YES:
                if self.worker:
                    self.worker.stop()
                if self.on_close_callback:
                    self.on_close_callback(self.task_id)
        else:
            if self.on_close_callback:
                self.on_close_callback(self.task_id)
                
    def on_task_start(self):
        """任务开始回调"""
        self.progress_bar.Pulse()
        
    def on_task_complete(self, report):
        """任务完成回调"""
        self.progress_bar.SetValue(100)
        self.progress_label.SetLabel("✅ 完成")
        self.update_log(f"{'─'*60}")
        self.update_log(f"✅ 任务 #{self.task_id} 已完成")
        self.update_log(f"{'─'*60}")
        
        # 恢复按钮
        self.start_btn.Enable(True)
        self.stop_btn.Enable(False)
        self.topic_input.Enable(True)
        
    def on_task_error(self, error_msg):
        """任务错误回调"""
        self.progress_bar.SetValue(0)
        self.progress_label.SetLabel("❌ 失败")
        self.update_log(f"{'─'*60}")
        self.update_log(f"❌ 任务 #{self.task_id} 失败")
        self.update_log(f"❌ 错误: {error_msg}")
        self.update_log(f"{'─'*60}")
        
        # 恢复按钮
        self.start_btn.Enable(True)
        self.stop_btn.Enable(False)
        self.topic_input.Enable(True)
        
    def update_log(self, message):
        """更新日志"""
        timestamp = beijing_now_str("%H:%M:%S")
        
        # 根据消息内容添加颜色和格式
        if message.strip():
            # 添加时间戳和消息
            log_entry = f"[{timestamp}] {message}\n"
            self.log_text.AppendText(log_entry)
            
            # 自动滚动到最新日志
            self.log_text.ShowPosition(self.log_text.GetLastPosition())


class NewReportPanel(wx.Panel):
    """新建报告面板 - 支持多任务"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.task_counter = 0
        self.task_panels = {}
        self.init_ui()
        
        # 创建第一个任务
        self.add_new_task()
        
    def init_ui(self):
        """初始化界面"""
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 标题和工具栏
        toolbar_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        title = wx.StaticText(self, label="📝 新建调研报告")
        title_font = title.GetFont()
        title_font.PointSize += 4
        title_font = title_font.Bold()
        title.SetFont(title_font)
        toolbar_sizer.Add(title, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 20)
        
        # 新建任务按钮
        new_task_btn = wx.Button(self, label="➕ 新建任务")
        new_task_btn.Bind(wx.EVT_BUTTON, self.on_new_task)
        toolbar_sizer.Add(new_task_btn, 0)
        
        main_sizer.Add(toolbar_sizer, 0, wx.ALL, 10)
        
        # 任务标签页
        self.task_notebook = wx.Notebook(self)
        main_sizer.Add(self.task_notebook, 1, wx.EXPAND | wx.ALL, 10)
        
        self.SetSizer(main_sizer)
        
    def add_new_task(self):
        """添加新任务"""
        self.task_counter += 1
        task_id = self.task_counter
        
        # 创建任务面板
        task_panel = TaskPanel(self.task_notebook, task_id, self.on_close_task)
        
        # 添加到notebook
        self.task_notebook.AddPage(task_panel, f"任务 #{task_id}")
        
        # 切换到新任务
        page_count = self.task_notebook.GetPageCount()
        self.task_notebook.SetSelection(page_count - 1)
        
        # 保存引用
        self.task_panels[task_id] = task_panel
        
    def on_new_task(self, event):
        """新建任务按钮"""
        self.add_new_task()
        
    def on_close_task(self, task_id):
        """关闭任务回调"""
        # 找到对应的页面索引
        for i in range(self.task_notebook.GetPageCount()):
            page = self.task_notebook.GetPage(i)
            if hasattr(page, 'task_id') and page.task_id == task_id:
                # 如果只剩一个任务，不允许关闭
                if self.task_notebook.GetPageCount() == 1:
                    wx.MessageBox("至少需要保留一个任务标签", "提示", wx.OK | wx.ICON_WARNING)
                    return
                
                # 关闭页面
                self.task_notebook.DeletePage(i)
                
                # 从字典中移除
                if task_id in self.task_panels:
                    del self.task_panels[task_id]
                
                break


class ConfigPanel(wx.Panel):
    """配置管理面板"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.init_ui()
        self.load_config()
        
    def init_ui(self):
        """初始化界面"""
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 标题
        title = wx.StaticText(self, label="⚙️ 系统配置")
        title_font = title.GetFont()
        title_font.PointSize += 4
        title_font = title_font.Bold()
        title.SetFont(title_font)
        main_sizer.Add(title, 0, wx.ALL, 10)
        
        # 创建Notebook用于配置分类
        config_notebook = wx.Notebook(self)
        
        # Tab 1: Agent配置
        agent_panel = self.create_agent_config_panel(config_notebook)
        config_notebook.AddPage(agent_panel, "Agent模型配置")
        
        # Tab 2: 环境变量配置
        env_panel = self.create_env_config_panel(config_notebook)
        config_notebook.AddPage(env_panel, "环境变量配置")
        
        # Tab 3: 搜索配置
        search_panel = self.create_search_config_panel(config_notebook)
        config_notebook.AddPage(search_panel, "搜索配置")
        
        main_sizer.Add(config_notebook, 1, wx.EXPAND | wx.ALL, 10)
        
        # 按钮
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        save_btn = wx.Button(self, label="💾 保存配置")
        save_btn.Bind(wx.EVT_BUTTON, self.on_save)
        btn_sizer.Add(save_btn, 0, wx.RIGHT, 10)
        
        reload_btn = wx.Button(self, label="🔄 重新加载")
        reload_btn.Bind(wx.EVT_BUTTON, self.on_reload)
        btn_sizer.Add(reload_btn, 0, wx.RIGHT, 10)
        
        reset_btn = wx.Button(self, label="↩️ 恢复默认")
        reset_btn.Bind(wx.EVT_BUTTON, self.on_reset)
        btn_sizer.Add(reset_btn, 0)
        
        main_sizer.Add(btn_sizer, 0, wx.ALL, 10)
        
        self.SetSizer(main_sizer)
        
    def create_agent_config_panel(self, parent):
        """创建Agent配置面板"""
        panel = scrolled.ScrolledPanel(parent)
        panel.SetupScrolling()
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 说明文字
        info_box = wx.StaticBox(panel, label="ℹ️ 说明")
        info_sizer = wx.StaticBoxSizer(info_box, wx.VERTICAL)
        info_text = wx.StaticText(
            panel, 
            label="为每个Agent配置使用的AI模型供应商和具体模型。配置会保存到 .env 文件。\n"
                  "💡 提示：可以编辑 config/runtime.json 文件来添加新的供应商和模型。"
        )
        info_text.Wrap(600)
        info_sizer.Add(info_text, 0, wx.ALL, 5)
        
        # 编辑配置文件按钮
        edit_btn = wx.Button(panel, label="📝 编辑运行时配置文件 (config/runtime.json)")
        edit_btn.Bind(wx.EVT_BUTTON, self.on_edit_model_config)
        info_sizer.Add(edit_btn, 0, wx.ALL, 5)
        
        sizer.Add(info_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        # 加载模型配置
        self.load_model_config()
        
        # Agent配置
        self.agent_configs = {}
        self.default_agent_temperatures = {
            "requirement_analyzer": float(config.REQUIREMENT_ANALYZER_TEMPERATURE),
            "information_collector": float(config.INFORMATION_COLLECTOR_TEMPERATURE),
            "report_writer": float(config.REPORT_WRITER_TEMPERATURE),
            "quality_judge": float(config.QUALITY_JUDGE_TEMPERATURE),
            "comprehensive_report_writer": float(config.COMPREHENSIVE_REPORT_WRITER_TEMPERATURE),
        }
        agent_names = {
            "requirement_analyzer": "需求分析师 (Requirement Analyzer)",
            "information_collector": "信息收集员 (Information Collector)",
            "report_writer": "报告撰写员 (Report Writer)",
            "quality_judge": "质量评审员 (Quality Judge)",
            "comprehensive_report_writer": "综合报告撰写员 (Comprehensive Writer)"
        }
        
        for agent_key, agent_name in agent_names.items():
            box = wx.StaticBox(panel, label=agent_name)
            box_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
            
            # 供应商和模型在同一行
            row_sizer = wx.BoxSizer(wx.HORIZONTAL)
            
            # 供应商选择
            provider_sizer = wx.BoxSizer(wx.HORIZONTAL)
            provider_sizer.Add(wx.StaticText(panel, label="供应商:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            provider_choices = list(self.model_options.keys())
            provider_choice = wx.Choice(panel, choices=provider_choices)
            provider_choice.SetMinSize((120, -1))
            provider_sizer.Add(provider_choice, 0)
            row_sizer.Add(provider_sizer, 0, wx.RIGHT, 20)
            
            # 模型选择
            model_sizer = wx.BoxSizer(wx.HORIZONTAL)
            model_sizer.Add(wx.StaticText(panel, label="模型:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            model_choice = wx.Choice(panel, choices=[])
            model_choice.SetMinSize((350, -1))
            model_sizer.Add(model_choice, 1)
            row_sizer.Add(model_sizer, 1)
            
            box_sizer.Add(row_sizer, 0, wx.EXPAND | wx.ALL, 5)
            
            # 自定义模型输入框（默认隐藏）
            custom_sizer = wx.BoxSizer(wx.HORIZONTAL)
            custom_sizer.Add(wx.StaticText(panel, label="自定义模型:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            custom_input = wx.TextCtrl(panel)
            custom_input.SetMinSize((350, -1))
            custom_input.Show(False)  # 默认隐藏
            custom_sizer.Add(custom_input, 1)
            box_sizer.Add(custom_sizer, 0, wx.EXPAND | wx.ALL, 5)
            
            # 推理模式
            reasoner_checkbox = wx.CheckBox(panel, label="✓ 启用推理模式 (deepseek-reasoner 或类似)")
            box_sizer.Add(reasoner_checkbox, 0, wx.ALL, 5)

            # 温度参数
            temperature_sizer = wx.BoxSizer(wx.HORIZONTAL)
            temperature_sizer.Add(wx.StaticText(panel, label="温度 Temperature:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            temperature_ctrl = wx.SpinCtrlDouble(panel, min=0.0, max=2.0, initial=0.7, inc=0.1)
            temperature_ctrl.SetDigits(2)
            temperature_ctrl.SetValue(self.default_agent_temperatures.get(agent_key, 0.7))
            temperature_ctrl.SetMinSize((100, -1))
            temperature_sizer.Add(temperature_ctrl, 0)
            box_sizer.Add(temperature_sizer, 0, wx.ALL, 5)
            
            sizer.Add(box_sizer, 0, wx.EXPAND | wx.ALL, 10)
            
            # 保存控件引用
            self.agent_configs[agent_key] = {
                'provider': provider_choice,
                'model': model_choice,
                'custom_input': custom_input,
                'custom_sizer': custom_sizer,
                'reasoner': reasoner_checkbox,
                'temperature': temperature_ctrl
            }
            
            # 绑定供应商变化事件
            provider_choice.Bind(wx.EVT_CHOICE, lambda evt, key=agent_key: self.on_provider_changed(evt, key))
        
        panel.SetSizer(sizer)
        return panel
    
    def load_model_config(self):
        """从 runtime.json 的 providers 字段加载模型选项。"""
        default_config = {
            "deepseek": ["deepseek-chat", "deepseek-reasoner"],
            "glm": ["glm-4-flash", "glm-4-plus", "glm-4-air", "glm-4-airx", "glm-4-long"],
            "zhipu": ["glm-4-flash", "glm-4-plus", "glm-4-air", "glm-4-airx", "glm-4-long"],
            "openrouter": [
                "anthropic/claude-3.5-sonnet",
                "openai/gpt-4o",
                "openai/gpt-4o-mini",
                "google/gemini-pro-1.5",
                "meta-llama/llama-3.1-70b-instruct",
                "qwen/qwen-2.5-72b-instruct",
                "deepseek/deepseek-chat",
                "anthropic/claude-3-opus",
                "xiaomi/mimo-v2-flash:free",
                "z-ai/glm-4.5-air:free",
            ],
        }

        self.model_options = {}
        self.model_descriptions = {}

        try:
            runtime_cfg = load_runtime_config()
            providers_cfg = runtime_cfg.get("providers", {}) if isinstance(runtime_cfg, dict) else {}
            providers_cfg = providers_cfg if isinstance(providers_cfg, dict) else {}

            if providers_cfg:
                for provider, provider_cfg in providers_cfg.items():
                    if not isinstance(provider_cfg, dict):
                        continue

                    models = []
                    descriptions = {}
                    models_cfg = provider_cfg.get("models", [])
                    if isinstance(models_cfg, list) and models_cfg:
                        for model_item in models_cfg:
                            if isinstance(model_item, dict):
                                model_id = str(model_item.get("id", "")).strip()
                                model_name = str(model_item.get("name", "")).strip() or model_id
                                model_desc = str(model_item.get("description", "")).strip()
                            else:
                                model_id = str(model_item).strip()
                                model_name = model_id
                                model_desc = ""

                            if not model_id and not model_name:
                                continue

                            display_name = "自定义模型..." if (model_id or model_name).lower() == "custom" else model_name
                            models.append(display_name)
                            descriptions[display_name] = {
                                "id": model_id or model_name,
                                "description": model_desc,
                            }
                    else:
                        fallback_models = list(default_config.get(provider, []))
                        for model_id in fallback_models:
                            models.append(model_id)
                            descriptions[model_id] = {"id": model_id, "description": ""}

                    if "自定义模型..." not in models:
                        models.append("自定义模型...")
                        descriptions["自定义模型..."] = {"id": "custom", "description": "手动输入模型 ID"}

                    self.model_options[provider] = models
                    self.model_descriptions[provider] = descriptions

                    aliases = provider_cfg.get("aliases", [])
                    if not isinstance(aliases, list):
                        aliases = []
                    if provider == "zhipu" and "glm" not in aliases:
                        aliases = aliases + ["glm"]
                    for alias in aliases:
                        alias_key = str(alias).strip()
                        if not alias_key or alias_key in self.model_options:
                            continue
                        self.model_options[alias_key] = list(models)
                        self.model_descriptions[alias_key] = dict(descriptions)
            else:
                for provider, models in default_config.items():
                    model_list = list(models)
                    if "自定义模型..." not in model_list:
                        model_list.append("自定义模型...")
                    self.model_options[provider] = model_list
                    self.model_descriptions[provider] = {
                        model_name: {"id": model_name if model_name != "自定义模型..." else "custom", "description": ""}
                        for model_name in model_list
                    }

            print(f"✓ 已从 runtime.json 加载 {len(self.model_options)} 个供应商的模型配置")
        except Exception as e:
            print(f"⚠ 加载 runtime.json 失败: {e}，使用默认配置")
            for provider, models in default_config.items():
                model_list = list(models)
                if "自定义模型..." not in model_list:
                    model_list.append("自定义模型...")
                self.model_options[provider] = model_list
                self.model_descriptions[provider] = {
                    model_name: {"id": model_name if model_name != "自定义模型..." else "custom", "description": ""}
                    for model_name in model_list
                }
    
    def on_edit_model_config(self, event):
        """编辑运行时配置文件。"""
        config_file = get_runtime_config_path()
        if config_file.exists():
            os.startfile(config_file)
            wx.MessageBox(
                f"已打开 {config_file} 文件。\n\n"
                "编辑完成后保存，然后点击「重新加载」按钮应用更改。",
                "提示",
                wx.OK | wx.ICON_INFORMATION
            )
        else:
            wx.MessageBox(f"{config_file} 文件不存在！", "错误", wx.OK | wx.ICON_ERROR)
    
    def on_provider_changed(self, event, agent_key):
        """供应商变化时更新模型列表"""
        controls = self.agent_configs[agent_key]
        provider = controls['provider'].GetStringSelection()
        model_choice = controls['model']
        custom_input = controls['custom_input']
        custom_sizer = controls['custom_sizer']
        
        # 更新模型选项
        if provider in self.model_options:
            models = self.model_options[provider]
            model_choice.Clear()
            for model in models:
                model_choice.Append(model)
            
            # 默认选择第一个
            if model_choice.GetCount() > 0:
                model_choice.SetSelection(0)
        
        # 绑定模型选择事件（处理自定义模型）
        model_choice.Bind(wx.EVT_CHOICE, lambda evt: self.on_model_changed(evt, agent_key))
    
    def on_model_changed(self, event, agent_key):
        """模型选择变化时处理自定义模型输入"""
        controls = self.agent_configs[agent_key]
        model = controls['model'].GetStringSelection()
        custom_input = controls['custom_input']
        
        # 检查是否是自定义模型选项
        is_custom = False
        provider = controls['provider'].GetStringSelection()
        
        if provider in self.model_descriptions:
            # 从描述中获取实际ID
            if model in self.model_descriptions[provider]:
                model_id = self.model_descriptions[provider][model].get('id', '')
                if model_id == 'custom' or '自定义' in model:
                    is_custom = True
        elif 'custom' in model.lower() or '自定义' in model:
            is_custom = True
        
        # 如果选择"自定义模型"，显示输入框
        if is_custom:
            custom_input.Show(True)
        else:
            custom_input.Show(False)
        
        # 刷新布局
        custom_input.GetParent().Layout()
        
    def create_env_config_panel(self, parent):
        """创建环境变量配置面板"""
        panel = scrolled.ScrolledPanel(parent)
        panel.SetupScrolling()
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # API Keys
        api_box = wx.StaticBox(panel, label="API密钥配置")
        api_sizer = wx.StaticBoxSizer(api_box, wx.VERTICAL)
        
        self.env_inputs = {}
        
        env_vars = [
            ('DEEPSEEK_API_KEY', 'DeepSeek API Key'),
            ('ZHIPU_API_KEY', 'Zhipu/GLM API Key'),
            ('OPENROUTER_API_KEY', 'OpenRouter API Key'),
            ('TAVILY_API_KEY', 'Tavily API Key'),
        ]
        
        for key, label in env_vars:
            var_sizer = wx.BoxSizer(wx.HORIZONTAL)
            var_sizer.Add(wx.StaticText(panel, label=f"{label}:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            text_input = wx.TextCtrl(panel, style=wx.TE_PASSWORD, size=(400, -1))
            var_sizer.Add(text_input, 1)
            api_sizer.Add(var_sizer, 0, wx.EXPAND | wx.ALL, 5)
            self.env_inputs[key] = text_input
        
        sizer.Add(api_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        # SearXNG配置
        searxng_box = wx.StaticBox(panel, label="SearXNG配置")
        searxng_sizer = wx.StaticBoxSizer(searxng_box, wx.VERTICAL)
        
        url_sizer = wx.BoxSizer(wx.HORIZONTAL)
        url_sizer.Add(wx.StaticText(panel, label="服务器地址:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.searxng_url = wx.TextCtrl(panel, size=(400, -1))
        url_sizer.Add(self.searxng_url, 1)
        searxng_sizer.Add(url_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        sizer.Add(searxng_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        panel.SetSizer(sizer)
        return panel
        
    def create_search_config_panel(self, parent):
        """创建搜索配置面板"""
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 搜索引擎选择
        engine_box = wx.StaticBox(panel, label="搜索引擎")
        engine_sizer = wx.StaticBoxSizer(engine_box, wx.VERTICAL)
        
        self.engine_searxng = wx.RadioButton(panel, label="SearXNG", style=wx.RB_GROUP)
        self.engine_tavily = wx.RadioButton(panel, label="Tavily")
        engine_sizer.Add(self.engine_searxng, 0, wx.ALL, 5)
        engine_sizer.Add(self.engine_tavily, 0, wx.ALL, 5)
        
        sizer.Add(engine_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        # 搜索参数
        other_box = wx.StaticBox(panel, label="搜索参数")
        other_sizer = wx.StaticBoxSizer(other_box, wx.VERTICAL)
        
        # 并发数
        concurrent_sizer = wx.BoxSizer(wx.HORIZONTAL)
        concurrent_sizer.Add(wx.StaticText(panel, label="并发评估批数:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.concurrent_spin = wx.SpinCtrl(panel, value="6", min=1, max=10)
        concurrent_sizer.Add(self.concurrent_spin, 0)
        other_sizer.Add(concurrent_sizer, 0, wx.ALL, 5)
        
        # 内容长度
        length_sizer = wx.BoxSizer(wx.HORIZONTAL)
        length_sizer.Add(wx.StaticText(panel, label="内容提取长度:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.length_spin = wx.SpinCtrl(panel, value="4000", min=500, max=10000)
        length_sizer.Add(self.length_spin, 0)
        other_sizer.Add(length_sizer, 0, wx.ALL, 5)
        
        sizer.Add(other_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        panel.SetSizer(sizer)
        return panel
        
    def load_config(self):
        """加载当前配置"""
        try:
            # 加载环境变量
            env_file = Path('.env')
            if env_file.exists():
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if '=' in line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"\'')
                            
                            if key in self.env_inputs:
                                self.env_inputs[key].SetValue(value)
                            elif key == 'SEARXNG_BASE_URL':
                                self.searxng_url.SetValue(value)
            
            # 加载搜索引擎配置
            if config.SEARCH_ENGINE_TYPE == 'searxng':
                self.engine_searxng.SetValue(True)
            else:
                self.engine_tavily.SetValue(True)
            
            # 加载搜索参数
            self.concurrent_spin.SetValue(config.MAX_CONCURRENT_EVALUATIONS)
            self.length_spin.SetValue(config.CONTENT_EXTRACT_LENGTH)
            
            # 加载Agent配置
            agent_config = get_active_agent_config()
            for agent_key, controls in self.agent_configs.items():
                if agent_key in agent_config:
                    cfg = agent_config[agent_key]
                    provider = cfg.get('provider', 'deepseek')
                    
                    # 设置供应商
                    selected = controls['provider'].SetStringSelection(provider)
                    if not selected and controls['provider'].GetCount() > 0:
                        controls['provider'].SetSelection(0)
                    
                    # 触发供应商变化，更新模型列表
                    self.on_provider_changed(None, agent_key)
                    
                    # 设置模型
                    model = cfg.get('model', '')
                    if model:
                        # 检查模型是否在列表中
                        model_choice = controls['model']
                        if model_choice.FindString(model) != wx.NOT_FOUND:
                            model_choice.SetStringSelection(model)
                        else:
                            # 不在列表中，使用自定义模型
                            if model_choice.FindString('自定义模型...') != wx.NOT_FOUND:
                                model_choice.SetStringSelection('自定义模型...')
                                controls['custom_input'].SetValue(model)
                                controls['custom_input'].Show(True)
                    
                    # 设置推理模式
                    controls['reasoner'].SetValue(cfg.get('use_reasoner', False))
                    temp_value = cfg.get('temperature', self.default_agent_temperatures.get(agent_key, 0.7))
                    try:
                        controls['temperature'].SetValue(float(temp_value))
                    except (TypeError, ValueError):
                        controls['temperature'].SetValue(self.default_agent_temperatures.get(agent_key, 0.7))
                    
        except Exception as e:
            wx.MessageBox(f"加载配置失败：{e}", "错误", wx.OK | wx.ICON_ERROR)
            
    def on_save(self, event):
        """保存配置"""
        try:
            runtime_cfg = load_runtime_config()
            if not isinstance(runtime_cfg, dict):
                runtime_cfg = {}

            # 读取现有.env文件（保留其他配置）
            env_lines = []
            existing_keys = set()
            
            if Path('.env').exists():
                with open('.env', 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '=' in line:
                                key = line.split('=')[0].strip()
                                existing_keys.add(key)
                                # 保留不在GUI中编辑的配置项
                                if not any(key.startswith(prefix) for prefix in [
                                    'DEEPSEEK_API_KEY', 'ZHIPU_API_KEY', 'OPENROUTER_API_KEY', 'TAVILY_API_KEY',
                                    'SEARXNG_BASE_URL', 'SEARCH_ENGINE_TYPE',
                                    'SKIP_EVALUATION', 'SIMPLIFY_REPORT_INPUT', 'USE_PRIORITY_SOURCES',
                                    'MAX_CONCURRENT_EVALUATIONS', 'CONTENT_EXTRACT_LENGTH',
                                    'REQUIREMENT_ANALYZER_', 'INFORMATION_COLLECTOR_', 'REPORT_WRITER_',
                                    'QUALITY_JUDGE_', 'COMPREHENSIVE_REPORT_WRITER_'
                                ]):
                                    env_lines.append(line)
            
            # Agent配置
            agents_section = runtime_cfg.get("agents")
            if not isinstance(agents_section, dict):
                agents_section = {}
                runtime_cfg["agents"] = agents_section

            for agent_key, controls in self.agent_configs.items():
                provider = controls['provider'].GetStringSelection()
                model_choice = controls['model'].GetStringSelection()
                
                # 处理模型 - 获取实际的model ID
                model = ''
                if model_choice:
                    # 如果是自定义模型
                    if provider in self.model_descriptions and model_choice in self.model_descriptions[provider]:
                        model_info = self.model_descriptions[provider][model_choice]
                        if model_info.get('id') == 'custom':
                            model = controls['custom_input'].GetValue().strip()
                        else:
                            model = model_info.get('id', model_choice)
                    else:
                        # 兼容旧格式：直接使用选中的文本
                        if 'custom' in model_choice.lower() or '自定义' in model_choice:
                            model = controls['custom_input'].GetValue().strip()
                        else:
                            model = model_choice
                
                use_reasoner = controls['reasoner'].GetValue()
                temperature = float(controls['temperature'].GetValue())

                existing_agent_cfg = agents_section.get(agent_key, {})
                if not isinstance(existing_agent_cfg, dict):
                    existing_agent_cfg = {}
                existing_agent_cfg["provider"] = provider or "deepseek"
                existing_agent_cfg["model"] = model or ""
                existing_agent_cfg["use_reasoner"] = bool(use_reasoner)
                existing_agent_cfg["temperature"] = round(temperature, 2)
                agents_section[agent_key] = existing_agent_cfg
            
            # API Keys
            for key, input_ctrl in self.env_inputs.items():
                value = input_ctrl.GetValue().strip()
                if value:
                    env_lines.append(f'{key}="{value}"')
            
            # SearXNG URL
            searxng_url = self.searxng_url.GetValue().strip()
            if searxng_url:
                env_lines.append(f'SEARXNG_BASE_URL="{searxng_url}"')

            engine = 'searxng' if self.engine_searxng.GetValue() else 'tavily'
            search_section = runtime_cfg.get("search")
            if not isinstance(search_section, dict):
                search_section = {}
                runtime_cfg["search"] = search_section
            search_section["engine_type"] = engine
            search_section.pop("skip_evaluation", None)
            search_section.pop("simplify_report_input", None)
            search_section.pop("use_priority_sources", None)
            search_section["max_concurrent_evaluations"] = int(self.concurrent_spin.GetValue())
            search_section["content_extract_length"] = int(self.length_spin.GetValue())

            save_ok = save_runtime_config(runtime_cfg)
            
            # 写入文件
            with open('.env', 'w', encoding='utf-8') as f:
                f.write('\n'.join(env_lines))
            
            if save_ok:
                wx.MessageBox("配置已保存到 runtime.json 与 .env！\n需要重启应用才能生效。", "保存成功", wx.OK | wx.ICON_INFORMATION)
            else:
                wx.MessageBox("已保存 .env，但保存 runtime.json 失败。", "保存部分成功", wx.OK | wx.ICON_WARNING)
            
        except Exception as e:
            wx.MessageBox(f"保存配置失败：{e}", "错误", wx.OK | wx.ICON_ERROR)
            
    def on_reload(self, event):
        """重新加载配置"""
        # 重新加载模型配置
        self.load_model_config()
        
        # 重新加载其他配置
        self.load_config()
        
        wx.MessageBox(
            "配置已重新加载！\n\n"
            "✓ 模型配置 (config/runtime.json)\n"
            "✓ 环境变量 (.env)\n"
            "✓ 搜索配置",
            "重新加载成功",
            wx.OK | wx.ICON_INFORMATION
        )
        
    def on_reset(self, event):
        """恢复默认配置"""
        dlg = wx.MessageDialog(
            self,
            "确定要恢复默认配置吗？这将清空所有当前配置！",
            "确认恢复默认",
            wx.YES_NO | wx.ICON_QUESTION
        )
        
        if dlg.ShowModal() == wx.ID_YES:
            # 清空所有输入
            for input_ctrl in self.env_inputs.values():
                input_ctrl.SetValue('')
            
            # 重置Agent配置为默认值
            for agent_key, controls in self.agent_configs.items():
                controls['provider'].SetSelection(0)  # 默认deepseek
                self.on_provider_changed(None, agent_key)  # 更新模型列表
                controls['model'].SetSelection(0)  # 默认第一个模型
                controls['custom_input'].SetValue('')
                controls['custom_input'].Show(False)
                controls['reasoner'].SetValue(False)
                controls['temperature'].SetValue(self.default_agent_temperatures.get(agent_key, 0.7))
            
            # 重置其他配置
            self.searxng_url.SetValue('http://localhost:8080')
            self.engine_searxng.SetValue(True)
            self.concurrent_spin.SetValue(6)
            self.length_spin.SetValue(4000)
            
            wx.MessageBox("已恢复默认配置", "完成", wx.OK | wx.ICON_INFORMATION)


class ComprehensiveReportPanel(wx.Panel):
    """综合报告面板"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.selected_reports = []
        self.init_ui()
        self.load_reports()
        
    def init_ui(self):
        """初始化界面"""
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 标题
        title = wx.StaticText(self, label="📚 综合报告制作")
        title_font = title.GetFont()
        title_font.PointSize += 4
        title_font = title_font.Bold()
        title.SetFont(title_font)
        main_sizer.Add(title, 0, wx.ALL, 10)
        
        # 说明
        desc = wx.StaticText(
            self,
            label="选择多个历史报告，AI将自动整合、交叉验证并生成综合分析报告"
        )
        main_sizer.Add(desc, 0, wx.ALL, 10)
        
        # 主题输入
        topic_label = wx.StaticText(self, label="综合报告主题：")
        main_sizer.Add(topic_label, 0, wx.LEFT | wx.TOP, 10)
        
        self.topic_input = wx.TextCtrl(
            self, 
            value="中国船舶涂料行业综合分析",
            size=(-1, 35)
        )
        main_sizer.Add(self.topic_input, 0, wx.EXPAND | wx.ALL, 10)
        
        # 报告选择器
        select_label = wx.StaticText(self, label="选择要整合的报告：")
        main_sizer.Add(select_label, 0, wx.LEFT | wx.TOP, 10)
        
        self.report_checklist = wx.CheckListBox(self, size=(-1, 200))
        main_sizer.Add(self.report_checklist, 1, wx.EXPAND | wx.ALL, 10)
        
        # 按钮
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.generate_btn = wx.Button(self, label="🚀 生成综合报告")
        self.generate_btn.Bind(wx.EVT_BUTTON, self.on_generate)
        btn_sizer.Add(self.generate_btn, 0, wx.RIGHT, 10)
        
        refresh_btn = wx.Button(self, label="🔄 刷新列表")
        refresh_btn.Bind(wx.EVT_BUTTON, self.on_refresh)
        btn_sizer.Add(refresh_btn, 0, wx.RIGHT, 10)
        
        select_all_btn = wx.Button(self, label="☑️ 全选")
        select_all_btn.Bind(wx.EVT_BUTTON, self.on_select_all)
        btn_sizer.Add(select_all_btn, 0, wx.RIGHT, 10)
        
        clear_btn = wx.Button(self, label="❌ 清空")
        clear_btn.Bind(wx.EVT_BUTTON, self.on_clear)
        btn_sizer.Add(clear_btn, 0)
        
        main_sizer.Add(btn_sizer, 0, wx.ALL, 10)
        
        # 进度显示
        self.progress_label = wx.StaticText(self, label="")
        main_sizer.Add(self.progress_label, 0, wx.ALL, 10)
        
        self.progress_bar = wx.Gauge(self, range=100)
        main_sizer.Add(self.progress_bar, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        
        # 日志显示
        log_label = wx.StaticText(self, label="📋 生成日志")
        main_sizer.Add(log_label, 0, wx.LEFT | wx.TOP, 10)
        
        self.log_text = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.TE_WORDWRAP,
            size=(-1, 150)
        )
        
        # 设置等宽字体
        font = wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.log_text.SetFont(font)
        self.log_text.SetBackgroundColour(wx.Colour(245, 245, 245))
        self.log_text.SetForegroundColour(wx.Colour(33, 33, 33))
        
        main_sizer.Add(self.log_text, 1, wx.EXPAND | wx.ALL, 10)
        
        self.SetSizer(main_sizer)
        
    def load_reports(self):
        """加载报告列表"""
        self.report_checklist.Clear()
        self.report_paths = []
        
        reports_dir = Path("reports")
        if not reports_dir.exists():
            return
        
        for md_file in sorted(reports_dir.glob("*.md"), key=os.path.getmtime, reverse=True):
            try:
                # 提取主题
                topic = md_file.stem.rsplit('_', 2)[0] if '_' in md_file.stem else md_file.stem
                mtime = datetime.fromtimestamp(md_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                
                display_name = f"{topic} ({mtime})"
                self.report_checklist.Append(display_name)
                self.report_paths.append(md_file)
                
            except Exception as e:
                print(f"加载报告失败 {md_file}: {e}")
                
    def on_generate(self, event):
        """生成综合报告"""
        # 获取选中的报告
        checked = []
        for i in range(self.report_checklist.GetCount()):
            if self.report_checklist.IsChecked(i):
                checked.append(i)
        
        if len(checked) < 2:
            wx.MessageBox("请至少选择2个报告进行综合", "提示", wx.OK | wx.ICON_WARNING)
            return
        
        topic = self.topic_input.GetValue().strip()
        if not topic:
            wx.MessageBox("请输入综合报告主题", "提示", wx.OK | wx.ICON_WARNING)
            return
        
        # 显示进度
        self.progress_label.SetLabel(f"正在整合 {len(checked)} 个报告...")
        self.progress_bar.Pulse()
        self.generate_btn.Enable(False)
        
        # 获取报告路径
        selected_paths = [self.report_paths[i] for i in checked]
        
        # 启动后台线程生成综合报告
        worker = ComprehensiveWorker(self, topic, selected_paths)
        worker.start()
        
    def on_refresh(self, event):
        """刷新列表"""
        self.load_reports()
        
    def on_select_all(self, event):
        """全选"""
        for i in range(self.report_checklist.GetCount()):
            self.report_checklist.Check(i, True)
            
    def on_clear(self, event):
        """清空选择"""
        for i in range(self.report_checklist.GetCount()):
            self.report_checklist.Check(i, False)
            
    def on_task_start(self):
        """任务开始"""
        self.progress_bar.Pulse()
        
    def on_task_complete(self, report):
        """任务完成"""
        self.progress_bar.SetValue(100)
        self.progress_label.SetLabel("✅ 综合报告生成完成！")
        self.generate_btn.Enable(True)
        wx.MessageBox("综合报告已生成并打开！", "成功", wx.OK | wx.ICON_INFORMATION)
        
    def on_task_error(self, error_msg):
        """任务出错"""
        self.progress_bar.SetValue(0)
        self.progress_label.SetLabel(f"❌ 生成失败")
        self.generate_btn.Enable(True)
        wx.MessageBox(f"生成失败：{error_msg}", "错误", wx.OK | wx.ICON_ERROR)


class HistoryPanel(wx.Panel):
    """历史报告面板"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.init_ui()
        self.load_reports()
        
    def init_ui(self):
        """初始化界面"""
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 标题
        title = wx.StaticText(self, label="🔍 历史报告")
        title_font = title.GetFont()
        title_font.PointSize += 4
        title_font = title_font.Bold()
        title.SetFont(title_font)
        main_sizer.Add(title, 0, wx.ALL, 10)
        
        # 搜索栏
        search_sizer = wx.BoxSizer(wx.HORIZONTAL)
        search_label = wx.StaticText(self, label="搜索：")
        search_sizer.Add(search_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        
        self.search_input = wx.TextCtrl(self, size=(300, -1))
        search_sizer.Add(self.search_input, 0, wx.RIGHT, 10)
        
        search_btn = wx.Button(self, label="🔍 搜索")
        search_btn.Bind(wx.EVT_BUTTON, self.on_search)
        search_sizer.Add(search_btn, 0, wx.RIGHT, 10)
        
        refresh_btn = wx.Button(self, label="🔄 刷新")
        refresh_btn.Bind(wx.EVT_BUTTON, self.on_refresh)
        search_sizer.Add(refresh_btn, 0)
        
        main_sizer.Add(search_sizer, 0, wx.ALL, 10)
        
        # 报告列表
        self.report_list = wx.ListCtrl(
            self,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL
        )
        self.report_list.InsertColumn(0, "文件名", width=300)
        self.report_list.InsertColumn(1, "主题", width=200)
        self.report_list.InsertColumn(2, "创建时间", width=150)
        self.report_list.InsertColumn(3, "大小", width=100)
        
        main_sizer.Add(self.report_list, 1, wx.EXPAND | wx.ALL, 10)
        
        # 按钮
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        open_btn = wx.Button(self, label="📄 打开")
        open_btn.Bind(wx.EVT_BUTTON, self.on_open)
        btn_sizer.Add(open_btn, 0, wx.RIGHT, 10)
        
        delete_btn = wx.Button(self, label="🗑️ 删除")
        delete_btn.Bind(wx.EVT_BUTTON, self.on_delete)
        btn_sizer.Add(delete_btn, 0)
        
        main_sizer.Add(btn_sizer, 0, wx.ALL, 10)
        
        self.SetSizer(main_sizer)
        
    def load_reports(self):
        """加载报告列表"""
        self.report_list.DeleteAllItems()
        
        reports_dir = Path("reports")
        if not reports_dir.exists():
            return
        
        for md_file in sorted(reports_dir.glob("*.md"), key=os.path.getmtime, reverse=True):
            try:
                stat = md_file.stat()
                size_kb = stat.st_size / 1024
                mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                
                # 提取主题（从文件名）
                topic = md_file.stem.rsplit('_', 2)[0] if '_' in md_file.stem else md_file.stem
                
                index = self.report_list.InsertItem(self.report_list.GetItemCount(), md_file.name)
                self.report_list.SetItem(index, 1, topic)
                self.report_list.SetItem(index, 2, mtime)
                self.report_list.SetItem(index, 3, f"{size_kb:.1f} KB")
                
            except Exception as e:
                print(f"加载报告失败 {md_file}: {e}")
                
    def on_search(self, event):
        """搜索报告"""
        keyword = self.search_input.GetValue().strip().lower()
        if not keyword:
            self.load_reports()
            return
        
        self.report_list.DeleteAllItems()
        reports_dir = Path("reports")
        
        for md_file in sorted(reports_dir.glob("*.md"), key=os.path.getmtime, reverse=True):
            if keyword in md_file.name.lower():
                try:
                    stat = md_file.stat()
                    size_kb = stat.st_size / 1024
                    mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                    topic = md_file.stem.rsplit('_', 2)[0] if '_' in md_file.stem else md_file.stem
                    
                    index = self.report_list.InsertItem(self.report_list.GetItemCount(), md_file.name)
                    self.report_list.SetItem(index, 1, topic)
                    self.report_list.SetItem(index, 2, mtime)
                    self.report_list.SetItem(index, 3, f"{size_kb:.1f} KB")
                except:
                    pass
                    
    def on_refresh(self, event):
        """刷新列表"""
        self.load_reports()
        
    def on_open(self, event):
        """打开选中的报告"""
        index = self.report_list.GetFirstSelected()
        if index == -1:
            wx.MessageBox("请先选择一个报告", "提示", wx.OK | wx.ICON_WARNING)
            return
        
        filename = self.report_list.GetItemText(index, 0)
        filepath = Path("reports") / filename
        
        if filepath.exists():
            os.startfile(filepath)
        else:
            wx.MessageBox("文件不存在", "错误", wx.OK | wx.ICON_ERROR)
            
    def on_delete(self, event):
        """删除选中的报告"""
        index = self.report_list.GetFirstSelected()
        if index == -1:
            wx.MessageBox("请先选择一个报告", "提示", wx.OK | wx.ICON_WARNING)
            return
        
        filename = self.report_list.GetItemText(index, 0)
        
        dlg = wx.MessageDialog(
            self,
            f"确定要删除报告 '{filename}' 吗？",
            "确认删除",
            wx.YES_NO | wx.ICON_QUESTION
        )
        
        if dlg.ShowModal() == wx.ID_YES:
            filepath = Path("reports") / filename
            try:
                filepath.unlink()
                # 同时删除元数据文件
                json_file = filepath.with_suffix('.json')
                if json_file.exists():
                    json_file.unlink()
                self.load_reports()
                wx.MessageBox("删除成功", "成功", wx.OK | wx.ICON_INFORMATION)
            except Exception as e:
                wx.MessageBox(f"删除失败：{e}", "错误", wx.OK | wx.ICON_ERROR)


class MainFrame(wx.Frame):
    """主窗口"""
    
    def __init__(self):
        super().__init__(
            None,
            title="🔬 AI研究报告生成系统",
            size=(1280, 900)
        )
        
        self.init_ui()
        self.Centre()
        
    def init_ui(self):
        """初始化界面"""
        # 创建菜单栏
        menubar = wx.MenuBar()
        
        # 文件菜单
        file_menu = wx.Menu()
        file_menu.Append(wx.ID_EXIT, "退出")
        self.Bind(wx.EVT_MENU, self.on_quit, id=wx.ID_EXIT)
        menubar.Append(file_menu, "文件")
        
        # 帮助菜单
        help_menu = wx.Menu()
        help_menu.Append(wx.ID_ABOUT, "关于")
        self.Bind(wx.EVT_MENU, self.on_about, id=wx.ID_ABOUT)
        menubar.Append(help_menu, "帮助")
        
        self.SetMenuBar(menubar)
        
        # 创建Notebook（标签页）
        notebook = wx.Notebook(self)
        
        # 添加面板
        self.new_report_panel = NewReportPanel(notebook)
        notebook.AddPage(self.new_report_panel, "📝 新建报告")
        
        self.history_panel = HistoryPanel(notebook)
        notebook.AddPage(self.history_panel, "🔍 历史报告")
        
        self.config_panel = ConfigPanel(notebook)
        notebook.AddPage(self.config_panel, "⚙️ 系统配置")
        
        self.comprehensive_panel = ComprehensiveReportPanel(notebook)
        notebook.AddPage(self.comprehensive_panel, "📚 综合报告")
        
        # 状态栏
        self.CreateStatusBar()
        self.SetStatusText("就绪")
        
    def on_quit(self, event):
        """退出程序"""
        self.Close()
        
    def on_about(self, event):
        """关于对话框"""
        info = wx.adv.AboutDialogInfo()
        info.SetName("AI研究报告生成系统")
        info.SetVersion("1.0.0")
        info.SetDescription("基于多Agent协作的智能研究报告生成工具")
        info.SetWebSite("https://github.com")
        info.AddDeveloper("AI Assistant")
        
        wx.adv.AboutBox(info)


class App(wx.App):
    """应用程序类"""
    
    def OnInit(self):
        init_log_routers()
        self.frame = MainFrame()
        self.frame.Show()
        return True


def main():
    """主函数"""
    # 确保工作目录固定在脚本所在位置，避免相对路径读取失败
    script_dir = Path(__file__).resolve().parent
    os.chdir(script_dir)
    
    app = App()
    app.MainLoop()


if __name__ == '__main__':
    main()
