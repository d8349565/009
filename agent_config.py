import os
from typing import Any, Dict

from runtime_config import load_runtime_config, parse_bool


AGENT_ENV_PREFIX = {
    "requirement_analyzer": "REQUIREMENT_ANALYZER",
    "information_collector": "INFORMATION_COLLECTOR",
    "report_writer": "REPORT_WRITER",
    "quality_judge": "QUALITY_JUDGE",
    "comprehensive_report_writer": "COMPREHENSIVE_REPORT_WRITER",
}


def get_active_agent_config() -> Dict[str, Dict[str, Any]]:
    runtime = load_runtime_config()
    agents_cfg = runtime.get("agents") if isinstance(runtime, dict) else {}
    agents_cfg = agents_cfg if isinstance(agents_cfg, dict) else {}

    final_config: Dict[str, Dict[str, Any]] = {}
    for agent_key, env_prefix in AGENT_ENV_PREFIX.items():
        base = agents_cfg.get(agent_key, {}) if isinstance(agents_cfg.get(agent_key, {}), dict) else {}

        env_provider = os.getenv(f"{env_prefix}_PROVIDER")
        env_model = os.getenv(f"{env_prefix}_MODEL")
        env_use_reasoner = os.getenv(f"{env_prefix}_USE_REASONER")

        provider = (env_provider or base.get("provider") or "deepseek").strip()
        model = (env_model or base.get("model") or "").strip()
        use_reasoner = parse_bool(env_use_reasoner, bool(base.get("use_reasoner", False)))

        temperature = base.get("temperature")
        if isinstance(temperature, (int, float)):
            temperature_value = float(temperature)
        else:
            temperature_value = None

        final_config[agent_key] = {
            "provider": provider,
            "model": model,
            "use_reasoner": use_reasoner,
        }
        if temperature_value is not None:
            final_config[agent_key]["temperature"] = temperature_value

    return final_config


def print_current_config():
    config = get_active_agent_config()
    agent_names = {
        "requirement_analyzer": "需求分析师",
        "information_collector": "信息收集员",
        "report_writer": "报告撰写员",
        "quality_judge": "质量评审员",
        "comprehensive_report_writer": "综合报告撰写员",
    }

    print("\n" + "=" * 80)
    print("📋 当前 Agent 配置")
    print("=" * 80)
    print(f"\n{'Agent名称':<20} {'供应商':<12} {'模型':<30} {'推理':<6}")
    print("-" * 80)

    for agent_key, settings in config.items():
        name = agent_names.get(agent_key, agent_key)
        provider = (settings.get("provider") or "").upper()
        model = settings.get("model") or "(自动选择)"
        reasoner = "是" if settings.get("use_reasoner") else "否"
        print(f"{name:<20} {provider:<12} {model:<30} {reasoner:<6}")

    print("=" * 80 + "\n")


if __name__ == "__main__":
    print_current_config()
