"""
AI研究报告生成系统 - PyQt6 GUI界面
"""

import contextvars
import os
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import importlib

import config
from agent_config import get_active_agent_config
from agents import ComprehensiveReportWriter
from llm_providers import reset_llm_manager
from main import ResearchAgentSystem
from runtime_config import get_runtime_config_path, load_runtime_config, save_runtime_config
from time_utils import beijing_now_str


# Context variable so ThreadPoolExecutor child threads inherit the correct emitter
_LOG_EMITTER_CTX: contextvars.ContextVar = contextvars.ContextVar('_log_emitter', default=None)


def open_in_system(path: Path) -> None:
    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
        return
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
        return
    subprocess.run(["xdg-open", str(path)], check=False)


class QtLogRouter:
    """Route stdout/stderr to per-thread Qt signal emitters."""

    def __init__(self, fallback):
        self._fallback = fallback
        self._targets: Dict[int, Any] = {}
        self._buffers: Dict[int, str] = {}
        self._lock = threading.Lock()

    def register(self, thread_id: int, emitter) -> None:
        with self._lock:
            self._targets[thread_id] = emitter
            self._buffers.setdefault(thread_id, "")
        # Propagate emitter to ThreadPoolExecutor child threads via context variable
        _LOG_EMITTER_CTX.set(emitter)

    def unregister(self, thread_id: int) -> None:
        with self._lock:
            self._targets.pop(thread_id, None)
            self._buffers.pop(thread_id, None)
        _LOG_EMITTER_CTX.set(None)

    def write(self, message: str) -> int:
        if not message:
            return 0

        fallback = None
        with self._lock:
            thread_id = threading.get_ident()
            emitter = self._targets.get(thread_id)
            if emitter is None:
                # Inherited by ThreadPoolExecutor child threads via contextvars
                emitter = _LOG_EMITTER_CTX.get(None)
            if emitter is None and len(self._targets) == 1:
                # Fallback: single active task owns all unregistered thread output
                emitter = next(iter(self._targets.values()))

            if emitter is None:
                fallback = self._fallback
            else:
                buf = self._buffers.get(thread_id, "")
                buf += message
                if "\n" in buf:
                    lines = buf.split("\n")
                    self._buffers[thread_id] = lines[-1]
                    for line in lines[:-1]:
                        if line.strip():
                            emitter(line)
                else:
                    self._buffers[thread_id] = buf

        if fallback is not None:
            try:
                fallback.write(message)
                fallback.flush()
            except Exception:
                pass
        return len(message)

    def flush(self) -> None:
        fallback = None
        with self._lock:
            thread_id = threading.get_ident()
            emitter = self._targets.get(thread_id)
            if emitter is None:
                emitter = _LOG_EMITTER_CTX.get(None)
            if emitter is None and len(self._targets) == 1:
                emitter = next(iter(self._targets.values()))
            if emitter is not None:
                buf = self._buffers.get(thread_id, "")
                if buf.strip():
                    emitter(buf)
                    self._buffers[thread_id] = ""
            else:
                fallback = self._fallback

        if fallback is not None:
            try:
                fallback.flush()
            except Exception:
                pass


LOG_ROUTER_OUT = None
LOG_ROUTER_ERR = None


def init_log_routers() -> None:
    global LOG_ROUTER_OUT, LOG_ROUTER_ERR
    if LOG_ROUTER_OUT is None:
        LOG_ROUTER_OUT = QtLogRouter(sys.__stdout__)
        LOG_ROUTER_ERR = QtLogRouter(sys.__stderr__)
        sys.stdout = LOG_ROUTER_OUT
        sys.stderr = LOG_ROUTER_ERR


class ResearchTaskWorker(QObject):
    started = pyqtSignal()
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)
    cancelled = pyqtSignal()  # 新增：取消信号
    log_message = pyqtSignal(str)

    def __init__(self, requirement: str, search_mode: str, task_id: int):
        super().__init__()
        self.requirement = requirement
        self.search_mode = search_mode
        self.task_id = task_id
        self._cancel_event = threading.Event()
        self._system = None  # 保存ResearchAgentSystem引用以便取消

    def request_cancel(self) -> None:
        """请求取消任务：设置取消事件并通知系统。"""
        self._cancel_event.set()
        if self._system is not None:
            try:
                self._system.cancel()
            except Exception:
                pass

    def run(self) -> None:
        thread_id = threading.get_ident()
        try:
            if LOG_ROUTER_OUT:
                LOG_ROUTER_OUT.register(thread_id, self.log_message.emit)
            if LOG_ROUTER_ERR:
                LOG_ROUTER_ERR.register(thread_id, self.log_message.emit)

            self.started.emit()
            print(f"\n{'=' * 60}")
            print(f"🚀 任务 #{self.task_id} 开始执行")
            print(f"{'=' * 60}\n")

            self._system = ResearchAgentSystem()
            self._system.set_cancel_event(self._cancel_event)

            if self.search_mode == "quick":
                print("📌 使用快速搜索模式")
                report = self._system.quick_search(self.requirement)
            else:
                print("📌 使用完整搜索模式")
                report = self._system.process_requirement(self.requirement)

            analysis_result = self._system.context.get("analysis_result")
            search_keywords = None
            if self._system.context.get("search_history"):
                search_keywords = self._system.context["search_history"][0].get("keywords", [])

            print("\n💾 正在保存报告...")
            self._system.save_report(
                report,
                auto_open=True,
                topic=self.requirement,
                analysis_result=analysis_result,
                search_keywords=search_keywords,
            )

            print(f"\n{'=' * 60}")
            print(f"✅ 任务 #{self.task_id} 完成")
            print(f"{'=' * 60}\n")
            self.finished.emit(report)
        except InterruptedError:
            print(f"\n{'=' * 60}")
            print(f"🚫 任务 #{self.task_id} 已被用户取消")
            print(f"{'=' * 60}\n")
            self.cancelled.emit()
        except Exception as e:
            self.failed.emit(str(e))
        finally:
            self._system = None
            if LOG_ROUTER_OUT:
                LOG_ROUTER_OUT.unregister(thread_id)
            if LOG_ROUTER_ERR:
                LOG_ROUTER_ERR.unregister(thread_id)


class ComprehensiveTaskWorker(QObject):
    started = pyqtSignal()
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)
    log_message = pyqtSignal(str)

    def __init__(self, topic: str, report_paths: List[Path]):
        super().__init__()
        self.topic = topic
        self.report_paths = report_paths

    def run(self) -> None:
        thread_id = threading.get_ident()
        try:
            if LOG_ROUTER_OUT:
                LOG_ROUTER_OUT.register(thread_id, self.log_message.emit)
            if LOG_ROUTER_ERR:
                LOG_ROUTER_ERR.register(thread_id, self.log_message.emit)

            self.started.emit()
            print(f"\n{'=' * 60}")
            print("🚀 开始生成综合报告")
            print(f"📋 主题: {self.topic}")
            print(f"📚 报告数量: {len(self.report_paths)}")
            print(f"{'=' * 60}\n")

            print("📖 正在读取报告内容...")
            reports_data = []
            for idx, path in enumerate(self.report_paths, 1):
                try:
                    print(f"  [{idx}/{len(self.report_paths)}] {path.name}")
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()

                    from collections import namedtuple

                    metadata_cls = namedtuple(
                        "Metadata",
                        ["title", "topic", "keywords", "tags", "content_summary", "created_at"],
                    )
                    topic_from_filename = path.stem.rsplit("_", 2)[0] if "_" in path.stem else path.stem
                    created_at = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                    content_summary = content[:500].replace("\n", " ") if content else ""
                    metadata = metadata_cls(
                        title=path.name,
                        topic=topic_from_filename,
                        keywords=[],
                        tags=[],
                        content_summary=content_summary,
                        created_at=created_at,
                    )
                    reports_data.append(
                        {
                            "filename": path.name,
                            "content": content,
                            "path": str(path),
                            "metadata": metadata,
                        }
                    )
                except Exception as e:
                    print(f"❌ 读取报告失败 {path}: {e}")

            print(f"\n✅ 成功读取 {len(reports_data)} 个报告")
            print("\n🤖 正在调用AI生成综合报告...")

            writer = ComprehensiveReportWriter(system_datetime=beijing_now_str())
            user_input = f"请基于以下{len(reports_data)}个历史报告，生成关于'{self.topic}'的综合分析报告"
            result = writer.analyze_and_integrate(
                user_input=user_input,
                related_reports=reports_data,
                outline_file=None,
            )

            comprehensive_report = result.get("comprehensive_report", "")
            if not comprehensive_report:
                raise RuntimeError("综合报告生成失败：返回内容为空")

            clean_topic = "".join(c for c in self.topic if c.isalnum() or c in (" ", "_", "-"))[:50].strip()
            timestamp = beijing_now_str("%Y%m%d_%H%M%S")
            filename = f"综合报告_{clean_topic or '主题'}_{timestamp}.md"
            reports_dir = Path("reports")
            reports_dir.mkdir(exist_ok=True)
            filepath = reports_dir / filename
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(comprehensive_report)

            print(f"\n{'=' * 60}")
            print("✅ 综合报告生成完成")
            print(f"📁 保存位置: {filepath}")
            print(f"{'=' * 60}\n")

            open_in_system(filepath)
            self.finished.emit(comprehensive_report)
        except Exception as e:
            self.failed.emit(str(e))
        finally:
            if LOG_ROUTER_OUT:
                LOG_ROUTER_OUT.unregister(thread_id)
            if LOG_ROUTER_ERR:
                LOG_ROUTER_ERR.unregister(thread_id)


class TaskWidget(QWidget):
    def __init__(self, task_id: int, on_close_callback):
        super().__init__()
        self.task_id = task_id
        self.on_close_callback = on_close_callback
        self.thread = None
        self.worker = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        task_label = QLabel(f"任务 #{self.task_id}")
        font = QFont()
        font.setBold(True)
        task_label.setFont(font)
        toolbar.addWidget(task_label)

        self.start_btn = QPushButton("▶ 开始")
        self.start_btn.clicked.connect(self.on_start)
        toolbar.addWidget(self.start_btn)

        self.close_btn = QPushButton("✖ 关闭")
        self.close_btn.clicked.connect(self.on_close)
        toolbar.addWidget(self.close_btn)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        topic_row = QHBoxLayout()
        topic_row.addWidget(QLabel("主题:"))
        self.topic_input = QLineEdit("")
        topic_row.addWidget(self.topic_input, 1)
        layout.addLayout(topic_row)

        mode_row = QHBoxLayout()
        self.mode_quick = QRadioButton("快速")
        self.mode_full = QRadioButton("完整")
        self.mode_full.setChecked(True)
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.mode_quick)
        self.mode_group.addButton(self.mode_full)
        mode_row.addWidget(self.mode_quick)
        mode_row.addWidget(self.mode_full)
        mode_row.addStretch(1)
        layout.addLayout(mode_row)

        self.progress_label = QLabel("等待开始...")
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        layout.addWidget(QLabel("实时日志"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("background: #f5f5f5; color: #212121;")
        mono = QFont("Consolas", 10)
        self.log_text.setFont(mono)
        layout.addWidget(self.log_text, 1)

    def on_start(self) -> None:
        topic = self.topic_input.text().strip()
        if not topic:
            QMessageBox.warning(self, "提示", "请输入研究主题")
            return

        search_mode = "quick" if self.mode_quick.isChecked() else "full"
        self.log_text.clear()
        self.append_log(f"🎯 任务 #{self.task_id} 准备启动")
        self.append_log(f"📋 主题: {topic}")
        self.append_log(f"⚙️ 模式: {'快速搜索' if search_mode == 'quick' else '完整搜索'}")
        self.append_log("-" * 60)

        self.start_btn.setEnabled(False)
        self.topic_input.setEnabled(False)
        self.mode_quick.setEnabled(False)
        self.mode_full.setEnabled(False)
        self.progress_bar.setRange(0, 0)
        self.progress_label.setText("进行中...")

        self.thread = QThread()
        self.worker = ResearchTaskWorker(topic, search_mode, self.task_id)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.started.connect(self.on_task_start)
        self.worker.log_message.connect(self.append_log)
        self.worker.finished.connect(self.on_task_complete)
        self.worker.failed.connect(self.on_task_error)
        self.worker.cancelled.connect(self.on_task_cancelled)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.worker.cancelled.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._cleanup_worker)
        self.thread.start()

    def on_close(self) -> None:
        if self.thread and self.thread.isRunning():
            reply = QMessageBox.question(
                self,
                "取消任务",
                f"任务 #{self.task_id} 正在运行。\n是否取消任务并关闭此标签页？\n（将在当前步骤完成后停止）",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.progress_label.setText("⏳ 正在取消...")
                self.close_btn.setEnabled(False)
                if self.worker:
                    self.worker.request_cancel()
                # 线程结束后自动关闭标签页
                if self.thread:
                    self.thread.finished.connect(lambda: self.on_close_callback(self.task_id))
            return
        self.on_close_callback(self.task_id)

    def on_task_start(self) -> None:
        self.progress_label.setText("进行中...")

    def on_task_complete(self, _report: str) -> None:
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_label.setText("✅ 完成")
        self.append_log("-" * 60)
        self.append_log(f"✅ 任务 #{self.task_id} 已完成")
        self.append_log("-" * 60)
        self._restore_controls()

    def on_task_error(self, error_msg: str) -> None:
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_label.setText("❌ 失败")
        self.append_log("-" * 60)
        self.append_log(f"❌ 任务 #{self.task_id} 失败")
        self.append_log(f"❌ 错误: {error_msg}")
        self.append_log("-" * 60)
        self._restore_controls()

    def on_task_cancelled(self) -> None:
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_label.setText("🚫 已取消")
        self.append_log("-" * 60)
        self.append_log(f"🚫 任务 #{self.task_id} 已被取消")
        self.append_log("-" * 60)
        self._restore_controls()
        self.close_btn.setEnabled(True)

    def _restore_controls(self) -> None:
        self.start_btn.setEnabled(True)
        self.topic_input.setEnabled(True)
        self.mode_quick.setEnabled(True)
        self.mode_full.setEnabled(True)

    def _cleanup_worker(self) -> None:
        self.worker = None
        self.thread = None

    def append_log(self, message: str) -> None:
        if not message.strip():
            return
        timestamp = beijing_now_str("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")


class NewReportTab(QWidget):
    def __init__(self):
        super().__init__()
        self.task_counter = 0
        self.task_widgets: Dict[int, TaskWidget] = {}
        self._init_ui()
        self.add_new_task()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()

        title = QLabel("新建调研报告")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        toolbar.addWidget(title)

        add_btn = QPushButton("➕ 新建任务")
        add_btn.clicked.connect(self.add_new_task)
        toolbar.addWidget(add_btn)
        toolbar.addStretch(1)

        layout.addLayout(toolbar)
        self.task_tabs = QTabWidget()
        layout.addWidget(self.task_tabs, 1)

    def add_new_task(self) -> None:
        self.task_counter += 1
        task_id = self.task_counter
        widget = TaskWidget(task_id, self.close_task)
        self.task_widgets[task_id] = widget
        self.task_tabs.addTab(widget, f"任务 #{task_id}")
        self.task_tabs.setCurrentWidget(widget)

    def close_task(self, task_id: int) -> None:
        if self.task_tabs.count() <= 1:
            QMessageBox.warning(self, "提示", "至少需要保留一个任务标签")
            return
        for i in range(self.task_tabs.count()):
            page = self.task_tabs.widget(i)
            if isinstance(page, TaskWidget) and page.task_id == task_id:
                self.task_tabs.removeTab(i)
                self.task_widgets.pop(task_id, None)
                page.deleteLater()
                return


class ConfigTab(QWidget):
    def __init__(self):
        super().__init__()
        self.agent_configs: Dict[str, Dict[str, Any]] = {}
        self.env_inputs: Dict[str, QLineEdit] = {}
        self.model_options: Dict[str, List[str]] = {}
        self.model_descriptions: Dict[str, Dict[str, Dict[str, str]]] = {}
        self.default_agent_temperatures = {
            "requirement_analyzer": float(config.REQUIREMENT_ANALYZER_TEMPERATURE),
            "information_collector": float(config.INFORMATION_COLLECTOR_TEMPERATURE),
            "report_writer": float(config.REPORT_WRITER_TEMPERATURE),
            "quality_judge": float(config.QUALITY_JUDGE_TEMPERATURE),
            "comprehensive_report_writer": float(config.COMPREHENSIVE_REPORT_WRITER_TEMPERATURE),
        }
        self._init_ui()
        self.load_model_config()
        self.refresh_provider_choices()
        self.load_config()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        title = QLabel("系统配置")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self.tabs.addTab(self._create_agent_tab(), "Agent模型配置")
        self.tabs.addTab(self._create_env_tab(), "环境变量配置")
        self.tabs.addTab(self._create_search_tab(), "搜索配置")

        btn_row = QHBoxLayout()
        save_btn = QPushButton("💾 保存配置")
        save_btn.clicked.connect(self.on_save)
        btn_row.addWidget(save_btn)
        reload_btn = QPushButton("🔄 重新加载")
        reload_btn.clicked.connect(self.on_reload)
        btn_row.addWidget(reload_btn)
        reset_btn = QPushButton("↩ 恢复默认")
        reset_btn.clicked.connect(self.on_reset)
        btn_row.addWidget(reset_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

    def _create_agent_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)

        info = QGroupBox("说明")
        info_layout = QVBoxLayout(info)
        info_text = QLabel(
            "为每个Agent配置使用的AI模型供应商和具体模型。配置会保存到 .env 与 runtime.json。\n"
            "提示：可以直接编辑 config/runtime.json 添加新的供应商和模型。"
        )
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        edit_btn = QPushButton("📝 编辑运行时配置文件 (config/runtime.json)")
        edit_btn.clicked.connect(self.on_edit_model_config)
        info_layout.addWidget(edit_btn)
        layout.addWidget(info)

        self.agent_groups_container = QWidget()
        self.agent_groups_layout = QVBoxLayout(self.agent_groups_container)
        layout.addWidget(self.agent_groups_container)
        layout.addStretch(1)
        scroll.setWidget(container)
        return scroll

    def _create_env_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)

        api_group = QGroupBox("API密钥配置")
        api_layout = QGridLayout(api_group)
        env_vars = [
            ("DEEPSEEK_API_KEY", "DeepSeek API Key"),
            ("ZHIPU_API_KEY", "Zhipu/GLM API Key"),
            ("OPENROUTER_API_KEY", "OpenRouter API Key"),
            ("QWEN_API_KEY", "阿里百炼 (Qwen) API Key"),
            ("TAVILY_API_KEY", "Tavily API Key"),
        ]
        for row, (key, label) in enumerate(env_vars):
            api_layout.addWidget(QLabel(f"{label}:"), row, 0)
            text_input = QLineEdit()
            text_input.setEchoMode(QLineEdit.EchoMode.Password)
            api_layout.addWidget(text_input, row, 1)
            self.env_inputs[key] = text_input
        layout.addWidget(api_group)

        searxng_group = QGroupBox("SearXNG配置")
        searxng_layout = QGridLayout(searxng_group)
        searxng_layout.addWidget(QLabel("服务器地址:"), 0, 0)
        self.searxng_url = QLineEdit()
        searxng_layout.addWidget(self.searxng_url, 0, 1)
        layout.addWidget(searxng_group)

        layout.addStretch(1)
        scroll.setWidget(container)
        return scroll

    def _create_search_tab(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        engine_group = QGroupBox("搜索引擎")
        engine_layout = QVBoxLayout(engine_group)
        self.engine_searxng = QRadioButton("SearXNG")
        self.engine_tavily = QRadioButton("Tavily")
        self.engine_searxng.setChecked(True)
        engine_layout.addWidget(self.engine_searxng)
        engine_layout.addWidget(self.engine_tavily)
        layout.addWidget(engine_group)

        params_group = QGroupBox("搜索参数")
        params_layout = QGridLayout(params_group)
        params_layout.addWidget(QLabel("并发评估批数:"), 0, 0)
        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(1, 10)
        self.concurrent_spin.setValue(6)
        params_layout.addWidget(self.concurrent_spin, 0, 1)

        params_layout.addWidget(QLabel("内容提取长度:"), 1, 0)
        self.length_spin = QSpinBox()
        self.length_spin.setRange(500, 10000)
        self.length_spin.setValue(4000)
        params_layout.addWidget(self.length_spin, 1, 1)
        layout.addWidget(params_group)
        layout.addStretch(1)
        return panel

    def _rebuild_agent_groups(self) -> None:
        while self.agent_groups_layout.count():
            item = self.agent_groups_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.agent_configs = {}
        agent_names = {
            "requirement_analyzer": "需求分析师 (Requirement Analyzer)",
            "information_collector": "信息收集员 (Information Collector)",
            "report_writer": "报告撰写员 (Report Writer)",
            "quality_judge": "质量评审员 (Quality Judge)",
            "comprehensive_report_writer": "综合报告撰写员 (Comprehensive Writer)",
        }

        provider_choices = list(self.model_options.keys())
        for agent_key, agent_name in agent_names.items():
            group = QGroupBox(agent_name)
            group_layout = QGridLayout(group)

            group_layout.addWidget(QLabel("供应商:"), 0, 0)
            provider_combo = QComboBox()
            provider_combo.addItems(provider_choices)
            group_layout.addWidget(provider_combo, 0, 1)

            group_layout.addWidget(QLabel("模型:"), 0, 2)
            model_combo = QComboBox()
            group_layout.addWidget(model_combo, 0, 3)

            custom_container = QWidget()
            custom_layout = QHBoxLayout(custom_container)
            custom_layout.setContentsMargins(0, 0, 0, 0)
            custom_layout.addWidget(QLabel("自定义模型:"))
            custom_input = QLineEdit()
            custom_layout.addWidget(custom_input, 1)
            group_layout.addWidget(custom_container, 1, 0, 1, 4)
            custom_container.setVisible(False)

            reasoner = QCheckBox("✓ 启用推理模式 (deepseek-reasoner 或类似)")
            group_layout.addWidget(reasoner, 2, 0, 1, 4)

            group_layout.addWidget(QLabel("温度 Temperature:"), 3, 0)
            temperature = QDoubleSpinBox()
            temperature.setRange(0.0, 2.0)
            temperature.setSingleStep(0.1)
            temperature.setDecimals(2)
            temperature.setValue(self.default_agent_temperatures.get(agent_key, 0.7))
            group_layout.addWidget(temperature, 3, 1)

            self.agent_groups_layout.addWidget(group)
            self.agent_configs[agent_key] = {
                "provider": provider_combo,
                "model": model_combo,
                "custom_container": custom_container,
                "custom_input": custom_input,
                "reasoner": reasoner,
                "temperature": temperature,
            }

            provider_combo.currentTextChanged.connect(
                lambda _text, key=agent_key: self.on_provider_changed(key)
            )
            model_combo.currentTextChanged.connect(
                lambda _text, key=agent_key: self.on_model_changed(key)
            )
            self.on_provider_changed(agent_key)

        self.agent_groups_layout.addStretch(1)

    def load_model_config(self) -> None:
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
                            descriptions[display_name] = {"id": model_id or model_name, "description": model_desc}
                    else:
                        for model_id in list(default_config.get(provider, [])):
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
        except Exception:
            for provider, models in default_config.items():
                model_list = list(models)
                if "自定义模型..." not in model_list:
                    model_list.append("自定义模型...")
                self.model_options[provider] = model_list
                self.model_descriptions[provider] = {
                    model_name: {"id": model_name if model_name != "自定义模型..." else "custom", "description": ""}
                    for model_name in model_list
                }

    def refresh_provider_choices(self) -> None:
        self._rebuild_agent_groups()

    def on_edit_model_config(self) -> None:
        config_file = get_runtime_config_path()
        if config_file.exists():
            open_in_system(config_file)
            QMessageBox.information(
                self,
                "提示",
                f"已打开 {config_file} 文件。\n\n编辑完成后保存，然后点击「重新加载」按钮应用更改。",
            )
        else:
            QMessageBox.critical(self, "错误", f"{config_file} 文件不存在！")

    def on_provider_changed(self, agent_key: str) -> None:
        controls = self.agent_configs[agent_key]
        provider = controls["provider"].currentText()
        model_combo: QComboBox = controls["model"]
        models = self.model_options.get(provider, [])
        model_combo.blockSignals(True)
        model_combo.clear()
        model_combo.addItems(models)
        model_combo.blockSignals(False)
        if model_combo.count() > 0:
            model_combo.setCurrentIndex(0)
        self.on_model_changed(agent_key)

    def on_model_changed(self, agent_key: str) -> None:
        controls = self.agent_configs[agent_key]
        provider = controls["provider"].currentText()
        model = controls["model"].currentText()
        is_custom = False
        if provider in self.model_descriptions and model in self.model_descriptions[provider]:
            model_id = self.model_descriptions[provider][model].get("id", "")
            if model_id == "custom" or "自定义" in model:
                is_custom = True
        elif "custom" in model.lower() or "自定义" in model:
            is_custom = True
        controls["custom_container"].setVisible(is_custom)

    def load_config(self) -> None:
        try:
            env_file = Path(__file__).resolve().parent / ".env"
            if env_file.exists():
                with open(env_file, "r", encoding="utf-8-sig") as f:
                    for line in f:
                        line = line.strip()
                        if "=" in line and not line.startswith("#"):
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip().strip("\"'")
                            if key in self.env_inputs:
                                self.env_inputs[key].setText(value)
                            elif key == "SEARXNG_BASE_URL":
                                self.searxng_url.setText(value)

            if config.SEARCH_ENGINE_TYPE == "searxng":
                self.engine_searxng.setChecked(True)
            else:
                self.engine_tavily.setChecked(True)

            self.concurrent_spin.setValue(config.MAX_CONCURRENT_EVALUATIONS)
            self.length_spin.setValue(config.CONTENT_EXTRACT_LENGTH)

            agent_cfg = get_active_agent_config()
            for agent_key, controls in self.agent_configs.items():
                cfg = agent_cfg.get(agent_key, {})
                provider = cfg.get("provider", "deepseek")
                provider_combo: QComboBox = controls["provider"]
                provider_index = provider_combo.findText(provider)
                provider_combo.setCurrentIndex(provider_index if provider_index >= 0 else 0)

                self.on_provider_changed(agent_key)

                model = cfg.get("model", "")
                model_combo: QComboBox = controls["model"]
                if model:
                    model_index = model_combo.findText(model)
                    if model_index >= 0:
                        model_combo.setCurrentIndex(model_index)
                    else:
                        custom_index = model_combo.findText("自定义模型...")
                        if custom_index >= 0:
                            model_combo.setCurrentIndex(custom_index)
                            controls["custom_input"].setText(model)
                            controls["custom_container"].setVisible(True)
                controls["reasoner"].setChecked(bool(cfg.get("use_reasoner", False)))
                temp_value = cfg.get("temperature", self.default_agent_temperatures.get(agent_key, 0.7))
                try:
                    controls["temperature"].setValue(float(temp_value))
                except (TypeError, ValueError):
                    controls["temperature"].setValue(self.default_agent_temperatures.get(agent_key, 0.7))
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载配置失败：{e}")

    def on_save(self) -> None:
        try:
            runtime_cfg = load_runtime_config()
            if not isinstance(runtime_cfg, dict):
                runtime_cfg = {}

            env_lines = []
            _env_path = Path(__file__).resolve().parent / ".env"
            if _env_path.exists():
                with open(_env_path, "r", encoding="utf-8-sig") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key = line.split("=")[0].strip()
                            managed_prefixes = [
                                "DEEPSEEK_API_KEY",
                                "ZHIPU_API_KEY",
                                "OPENROUTER_API_KEY",
                                "QWEN_API_KEY",
                                "TAVILY_API_KEY",
                                "SEARXNG_BASE_URL",
                                "SEARCH_ENGINE_TYPE",
                                "SKIP_EVALUATION",
                                "SIMPLIFY_REPORT_INPUT",
                                "USE_PRIORITY_SOURCES",
                                "MAX_CONCURRENT_EVALUATIONS",
                                "CONTENT_EXTRACT_LENGTH",
                                "REQUIREMENT_ANALYZER_",
                                "INFORMATION_COLLECTOR_",
                                "REPORT_WRITER_",
                                "QUALITY_JUDGE_",
                                "COMPREHENSIVE_REPORT_WRITER_",
                            ]
                            if not any(key.startswith(prefix) for prefix in managed_prefixes):
                                env_lines.append(line)

            agents_section = runtime_cfg.get("agents")
            if not isinstance(agents_section, dict):
                agents_section = {}
                runtime_cfg["agents"] = agents_section

            for agent_key, controls in self.agent_configs.items():
                provider = controls["provider"].currentText().strip()
                model_choice = controls["model"].currentText().strip()
                model = ""
                if model_choice:
                    if provider in self.model_descriptions and model_choice in self.model_descriptions[provider]:
                        model_info = self.model_descriptions[provider][model_choice]
                        if model_info.get("id") == "custom":
                            model = controls["custom_input"].text().strip()
                        else:
                            model = model_info.get("id", model_choice)
                    else:
                        model = controls["custom_input"].text().strip() if "自定义" in model_choice else model_choice

                existing_agent_cfg = agents_section.get(agent_key, {})
                if not isinstance(existing_agent_cfg, dict):
                    existing_agent_cfg = {}
                existing_agent_cfg["provider"] = provider or "deepseek"
                existing_agent_cfg["model"] = model
                existing_agent_cfg["use_reasoner"] = bool(controls["reasoner"].isChecked())
                existing_agent_cfg["temperature"] = round(float(controls["temperature"].value()), 2)
                agents_section[agent_key] = existing_agent_cfg

            for key, input_ctrl in self.env_inputs.items():
                value = input_ctrl.text().strip()
                if value:
                    env_lines.append(f'{key}={value}')

            searxng_url = self.searxng_url.text().strip()
            if searxng_url:
                env_lines.append(f'SEARXNG_BASE_URL={searxng_url}')

            search_section = runtime_cfg.get("search")
            if not isinstance(search_section, dict):
                search_section = {}
                runtime_cfg["search"] = search_section
            search_section["engine_type"] = "searxng" if self.engine_searxng.isChecked() else "tavily"
            search_section.pop("skip_evaluation", None)
            search_section.pop("simplify_report_input", None)
            search_section.pop("use_priority_sources", None)
            search_section["max_concurrent_evaluations"] = int(self.concurrent_spin.value())
            search_section["content_extract_length"] = int(self.length_spin.value())

            save_ok = save_runtime_config(runtime_cfg)
            env_path = Path(__file__).resolve().parent / ".env"
            with open(env_path, "w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(env_lines))

            if save_ok:
                self._do_reload()
                QMessageBox.information(self, "保存成功", "配置已保存并自动重新加载！\n\n✓ runtime.json\n✓ .env\n✓ 搜索配置")
            else:
                QMessageBox.warning(self, "保存部分成功", "已保存 .env，但保存 runtime.json 失败。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败：{e}")

    def _do_reload(self) -> None:
        """重新加载所有配置（不弹对话框）。"""
        # 重新加载 .env 环境变量（自动处理 UTF-8 BOM）
        try:
            _env_path = Path(__file__).resolve().parent / ".env"
            if _env_path.exists():
                # 用 utf-8-sig 读取自动剥除 BOM，如有 BOM 则写回无 BOM 版本
                raw = _env_path.read_bytes()
                if raw[:3] == b"\xef\xbb\xbf":
                    _env_path.write_text(_env_path.read_text(encoding="utf-8-sig"), encoding="utf-8")
            from dotenv import load_dotenv
            load_dotenv(dotenv_path=str(_env_path), override=True)
        except Exception:
            pass
        # 重新加载 config 模块（刷新模块级变量）
        importlib.reload(config)
        # 重置 LLM 管理器单例，使其下次重建时读取新配置
        reset_llm_manager()
        # 刷新 GUI 控件
        self.load_model_config()
        self.refresh_provider_choices()
        self.load_config()

    def on_reload(self) -> None:
        self._do_reload()
        QMessageBox.information(
            self,
            "重新加载成功",
            "配置已重新加载！\n\n✓ 模型配置 (config/runtime.json)\n✓ 环境变量 (.env)\n✓ 搜索配置",
        )

    def on_reset(self) -> None:
        reply = QMessageBox.question(self, "确认恢复默认", "确定要恢复默认配置吗？这将清空所有当前配置！")
        if reply != QMessageBox.StandardButton.Yes:
            return

        for input_ctrl in self.env_inputs.values():
            input_ctrl.setText("")

        for agent_key, controls in self.agent_configs.items():
            controls["provider"].setCurrentIndex(0 if controls["provider"].count() > 0 else -1)
            self.on_provider_changed(agent_key)
            if controls["model"].count() > 0:
                controls["model"].setCurrentIndex(0)
            controls["custom_input"].setText("")
            controls["custom_container"].setVisible(False)
            controls["reasoner"].setChecked(False)
            controls["temperature"].setValue(self.default_agent_temperatures.get(agent_key, 0.7))

        self.searxng_url.setText("http://localhost:8080")
        self.engine_searxng.setChecked(True)
        self.concurrent_spin.setValue(6)
        self.length_spin.setValue(4000)
        QMessageBox.information(self, "完成", "已恢复默认配置")


class ComprehensiveTab(QWidget):
    def __init__(self):
        super().__init__()
        self.report_paths: List[Path] = []
        self.thread = None
        self.worker = None
        self._init_ui()
        self.load_reports()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("综合报告制作")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        desc = QLabel("选择多个历史报告，AI将自动整合、交叉验证并生成综合分析报告")
        layout.addWidget(desc)

        layout.addWidget(QLabel("综合报告主题："))
        self.topic_input = QLineEdit("中国船舶涂料行业综合分析")
        layout.addWidget(self.topic_input)

        layout.addWidget(QLabel("选择要整合的报告："))
        self.report_list = QListWidget()
        self.report_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        layout.addWidget(self.report_list, 1)

        btn_row = QHBoxLayout()
        self.generate_btn = QPushButton("🚀 生成综合报告")
        self.generate_btn.clicked.connect(self.on_generate)
        btn_row.addWidget(self.generate_btn)
        refresh_btn = QPushButton("🔄 刷新列表")
        refresh_btn.clicked.connect(self.load_reports)
        btn_row.addWidget(refresh_btn)
        select_all_btn = QPushButton("☑ 全选")
        select_all_btn.clicked.connect(self.on_select_all)
        btn_row.addWidget(select_all_btn)
        clear_btn = QPushButton("✖ 清空")
        clear_btn.clicked.connect(self.on_clear)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        self.progress_label = QLabel("")
        layout.addWidget(self.progress_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        layout.addWidget(QLabel("生成日志"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("background: #f5f5f5; color: #212121;")
        self.log_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.log_text, 1)

    def load_reports(self) -> None:
        self.report_list.clear()
        self.report_paths = []
        reports_dir = Path("reports")
        if not reports_dir.exists():
            return
        for md_file in sorted(reports_dir.glob("*.md"), key=os.path.getmtime, reverse=True):
            try:
                topic = md_file.stem.rsplit("_", 2)[0] if "_" in md_file.stem else md_file.stem
                mtime = datetime.fromtimestamp(md_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                item = QListWidgetItem(f"{topic} ({mtime})")
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.report_list.addItem(item)
                self.report_paths.append(md_file)
            except Exception:
                continue

    def on_select_all(self) -> None:
        for i in range(self.report_list.count()):
            self.report_list.item(i).setCheckState(Qt.CheckState.Checked)

    def on_clear(self) -> None:
        for i in range(self.report_list.count()):
            self.report_list.item(i).setCheckState(Qt.CheckState.Unchecked)

    def on_generate(self) -> None:
        checked = []
        for i in range(self.report_list.count()):
            if self.report_list.item(i).checkState() == Qt.CheckState.Checked:
                checked.append(i)

        if len(checked) < 2:
            QMessageBox.warning(self, "提示", "请至少选择2个报告进行综合")
            return
        topic = self.topic_input.text().strip()
        if not topic:
            QMessageBox.warning(self, "提示", "请输入综合报告主题")
            return
        if self.thread and self.thread.isRunning():
            QMessageBox.warning(self, "提示", "当前已有综合任务在运行，请稍后")
            return

        self.log_text.clear()
        self.generate_btn.setEnabled(False)
        self.progress_label.setText(f"正在整合 {len(checked)} 个报告...")
        self.progress_bar.setRange(0, 0)
        selected_paths = [self.report_paths[i] for i in checked]

        self.thread = QThread()
        self.worker = ComprehensiveTaskWorker(topic, selected_paths)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.started.connect(self.on_task_start)
        self.worker.log_message.connect(self.append_log)
        self.worker.finished.connect(self.on_task_complete)
        self.worker.failed.connect(self.on_task_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._cleanup_worker)
        self.thread.start()

    def on_task_start(self) -> None:
        self.progress_label.setText("综合报告生成中...")

    def on_task_complete(self, _report: str) -> None:
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_label.setText("✅ 综合报告生成完成！")
        self.generate_btn.setEnabled(True)
        QMessageBox.information(self, "成功", "综合报告已生成并打开！")

    def on_task_error(self, error_msg: str) -> None:
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_label.setText("❌ 生成失败")
        self.generate_btn.setEnabled(True)
        QMessageBox.critical(self, "错误", f"生成失败：{error_msg}")

    def _cleanup_worker(self) -> None:
        self.worker = None
        self.thread = None

    def append_log(self, message: str) -> None:
        if not message.strip():
            return
        timestamp = beijing_now_str("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")


class HistoryTab(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()
        self.load_reports()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("历史报告")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("搜索："))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入文件名关键词")
        search_row.addWidget(self.search_input)

        search_btn = QPushButton("🔍 搜索")
        search_btn.clicked.connect(self.on_search)
        search_row.addWidget(search_btn)
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.load_reports)
        search_row.addWidget(refresh_btn)
        search_row.addStretch(1)
        layout.addLayout(search_row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["文件名", "主题", "创建时间", "大小"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table, 1)

        btn_row = QHBoxLayout()
        open_btn = QPushButton("📄 打开")
        open_btn.clicked.connect(self.on_open)
        btn_row.addWidget(open_btn)
        delete_btn = QPushButton("🗑 删除")
        delete_btn.clicked.connect(self.on_delete)
        btn_row.addWidget(delete_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

    def _iter_reports(self, keyword: str = "") -> List[Path]:
        reports_dir = Path("reports")
        if not reports_dir.exists():
            return []
        keyword = keyword.strip().lower()
        files = sorted(reports_dir.glob("*.md"), key=os.path.getmtime, reverse=True)
        if not keyword:
            return files
        return [f for f in files if keyword in f.name.lower()]

    def load_reports(self) -> None:
        self._populate(self._iter_reports())

    def _populate(self, files: List[Path]) -> None:
        self.table.setRowCount(0)
        for md_file in files:
            try:
                stat = md_file.stat()
                size_kb = stat.st_size / 1024
                mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                topic = md_file.stem.rsplit("_", 2)[0] if "_" in md_file.stem else md_file.stem

                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(md_file.name))
                self.table.setItem(row, 1, QTableWidgetItem(topic))
                self.table.setItem(row, 2, QTableWidgetItem(mtime))
                self.table.setItem(row, 3, QTableWidgetItem(f"{size_kb:.1f} KB"))
            except Exception:
                continue

    def on_search(self) -> None:
        self._populate(self._iter_reports(self.search_input.text()))

    def on_open(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择一个报告")
            return
        filename_item = self.table.item(row, 0)
        if filename_item is None:
            return
        filepath = Path("reports") / filename_item.text()
        if filepath.exists():
            open_in_system(filepath)
        else:
            QMessageBox.critical(self, "错误", "文件不存在")

    def on_delete(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择一个报告")
            return
        filename_item = self.table.item(row, 0)
        if filename_item is None:
            return
        filename = filename_item.text()
        reply = QMessageBox.question(self, "确认删除", f"确定要删除报告 '{filename}' 吗？")
        if reply != QMessageBox.StandardButton.Yes:
            return
        filepath = Path("reports") / filename
        try:
            if filepath.exists():
                filepath.unlink()
            json_file = filepath.with_suffix(".json")
            if json_file.exists():
                json_file.unlink()
            self.load_reports()
            QMessageBox.information(self, "成功", "删除成功")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"删除失败：{e}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI研究报告生成系统 (PyQt6)")
        self.resize(1280, 900)
        self._init_ui()

    def _init_ui(self) -> None:
        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件")
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menubar.addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.on_about)
        help_menu.addAction(about_action)

        tabs = QTabWidget()
        tabs.addTab(NewReportTab(), "📝 新建报告")
        tabs.addTab(HistoryTab(), "🔍 历史报告")
        tabs.addTab(ConfigTab(), "⚙️ 系统配置")
        tabs.addTab(ComprehensiveTab(), "📚 综合报告")
        self.setCentralWidget(tabs)
        self.statusBar().showMessage("就绪")

    def on_about(self) -> None:
        QMessageBox.information(
            self,
            "关于",
            "AI研究报告生成系统\nPyQt6 版本\n\n基于多Agent协作的智能研究报告生成工具",
        )


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    os.chdir(script_dir)
    init_log_routers()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
