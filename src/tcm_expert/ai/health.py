from __future__ import annotations

from time import monotonic
from typing import Any

from tcm_expert.ai.factory import create_ai_workflow
from tcm_expert.ai.providers import ProviderUnavailable
from tcm_expert.database.ai_monitoring_repository import AIMonitoringRepository
from tcm_expert.database.settings_repository import SettingsRepository


def test_ai_connections(database: Any) -> list[dict[str, Any]]:
    settings = SettingsRepository(database).ai_settings()
    if settings.get("mode", "offline") != "connected":
        return [{"name": "Rule Engine", "status": "Sẵn sàng", "latency_ms": 0, "detail": "Offline"}]
    workflow = create_ai_workflow(database)
    monitoring = AIMonitoringRepository(database)
    checks = [
        ("Bộ dịch Việt–Trung", lambda: workflow.translator.vi_to_zh("Kiểm tra kết nối")),
        ("TCMChat", lambda: workflow.reasoner.suggest("连接测试，不提供诊断或处方。")),
        *[(provider.name, lambda provider=provider: provider.retrieve("kiểm tra kết nối"))
          for provider in workflow.knowledge],
    ]
    results: list[dict[str, Any]] = []
    for name, operation in checks:
        started = monotonic()
        status, detail, log_status = "Sẵn sàng", "Kết nối thành công", "ok"
        try:
            operation()
        except (ProviderUnavailable, OSError, ValueError) as error:
            status, detail, log_status = "Không sẵn sàng", str(error), "error"
        latency = int((monotonic() - started) * 1000)
        monitoring.record(None, name, log_status, latency, detail)
        results.append({"name": name, "status": status, "latency_ms": latency, "detail": detail})
    return results
