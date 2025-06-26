#!/usr/bin/env python3
"""T-01: Measure latency of process_message natural language queries.
Generates a markdown report with timing statistics for 10 representative queries.
Placed under CICD/tests/reports per architecture template.
Run: python CICD/tests/reports/t01_latency_measure.py
"""

import asyncio
import os
import time
import statistics
from datetime import datetime
from pathlib import Path
import json

# Ensure src in path
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../../apps/bot/src"))

from src.infrastructure.enhanced_service_factory import get_enhanced_service_factory

QUERIES = [
    "機台稼動率",
    "查看所有機台",
    "M001 機台狀況如何",
    "最近三天故障記錄",
    "加工部的生產統計報告",
    "目前所有機台的稼動率趨勢",
    "哪台機台最常停機",
    "產線 A 本週產量",
    "查詢機台維護時間表",
    "產線總良率"
]

async def main():
    factory = get_enhanced_service_factory()
    factory.initialize()
    handler = factory.create_message_handler()

    runtimes = []
    details = []

    for text in QUERIES:
        start = time.perf_counter()
        try:
            await handler.process_message("test-user", text, "dummy-token")
            status = "success"
        except Exception as e:
            status = f"error: {e.__class__.__name__}"
        elapsed = time.perf_counter() - start
        runtimes.append(elapsed)
        details.append({"query": text, "elapsed": elapsed, "status": status})
        print(f"{text}: {elapsed:.2f}s ({status})")

    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "count": len(QUERIES),
        "mean": statistics.mean(runtimes),
        "p95": statistics.quantiles(runtimes, n=20)[18],
        "max": max(runtimes),
        "min": min(runtimes),
        "details": details,
    }

    # Save JSON and markdown
    report_dir = Path(__file__).parent
    json_path = report_dir / "t01_latency_report.json"
    md_path = report_dir / "t01_latency_report.md"

    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    md_lines = [
        "# T-01 解析耗時量測報告",
        f"生成時間: {report['timestamp']}",
        "",
        "| 指標 | 值 (秒) |",
        "|------|---------|",
        f"| 平均值 | {report['mean']:.2f} |",
        f"| P95 | {report['p95']:.2f} |",
        f"| 最快 | {report['min']:.2f} |",
        f"| 最慢 | {report['max']:.2f} |",
        "",
        "## 明細",
        "| 查詢 | 時間(s) | 狀態 |",
        "|------|--------|-------|",
    ]
    for d in details:
        md_lines.append(f"| {d['query']} | {d['elapsed']:.2f} | {d['status']} |")

    md_path.write_text("\n".join(md_lines))
    print(f"\n報告已保存: {json_path}\nMarkdown: {md_path}")


if __name__ == "__main__":
    asyncio.run(main())
