"""
Pipeline工厂：根据组合配置实例化Agent与工具。
"""
from typing import Any, Dict, Optional

import config
from agent_config import get_active_agent_config
from agents import (
    RequirementAnalyzer,
    InformationCollector,
    ReportWriter,
    QualityJudge,
    ComprehensiveReportWriter,
)
from document_parser import DocumentParser
from report_metadata import ReportIndex
from search_engine import SearchEngine


class PipelineFactory:
    """根据 pipeline 配置创建组件的工厂。"""

    def __init__(self, pipeline_config: Optional[Dict[str, Any]] = None):
        self.pipeline_config = pipeline_config or config.PIPELINE_CONFIG or {}
        self.agent_config = get_active_agent_config(pipeline_config=self.pipeline_config)
        self.agent_classes = {
            "RequirementAnalyzer": RequirementAnalyzer,
            "InformationCollector": InformationCollector,
            "ReportWriter": ReportWriter,
            "QualityJudge": QualityJudge,
            "ComprehensiveReportWriter": ComprehensiveReportWriter,
            "requirement_analyzer": RequirementAnalyzer,
            "information_collector": InformationCollector,
            "report_writer": ReportWriter,
            "quality_judge": QualityJudge,
            "comprehensive_report_writer": ComprehensiveReportWriter,
        }
        self.tool_classes = {
            "SearchEngine": SearchEngine,
            "DocumentParser": DocumentParser,
            "ReportIndex": ReportIndex,
        }

    def create_agent(self, agent_key: str, system_datetime: Optional[str] = None):
        """按组合配置创建Agent实例。"""
        agent_def = (self.pipeline_config.get("agents", {}) or {}).get(agent_key, {})
        class_name = agent_def.get("class") or agent_key
        agent_class = self.agent_classes.get(class_name)
        if not agent_class:
            return None

        resolved_settings = self.agent_config.get(agent_key, {})
        provider = resolved_settings.get("provider")
        model = resolved_settings.get("model")
        use_reasoner = resolved_settings.get("use_reasoner")

        agent = agent_class(system_datetime=system_datetime, provider=provider)
        if model:
            agent.model_name = model
        if use_reasoner is not None:
            agent.use_reasoner = use_reasoner
        return agent

    def create_tool(self, tool_key: str, **overrides):
        """按组合配置创建工具实例。"""
        tool_def = (self.pipeline_config.get("tools", {}) or {}).get(tool_key, {})
        class_name = tool_def.get("class") or tool_key
        tool_class = self.tool_classes.get(class_name)
        if not tool_class:
            return None

        if tool_class is SearchEngine:
            engine_type = overrides.get("engine_type") or tool_def.get("engine_type") or config.SEARCH_ENGINE_TYPE
            return tool_class(engine_type=engine_type)

        return tool_class()

    def get_pipeline_steps(self):
        """返回 pipeline 定义的步骤列表。"""
        return (self.pipeline_config.get("pipeline", {}) or {}).get("steps", [])
