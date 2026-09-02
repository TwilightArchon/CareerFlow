from __future__ import annotations

from pathlib import Path

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from careerflow_agent.telemetry import RedactedFileSpanExporter


def test_local_span_export_is_bounded_and_redacted(tmp_path: Path) -> None:
    target = tmp_path / "spans.jsonl"
    exporter = RedactedFileSpanExporter(target, max_bytes=100_000)
    provider = TracerProvider(resource=Resource.create({"service.name": "test"}))
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test")
    with tracer.start_as_current_span("safe-span") as span:
        span.set_attribute("authorization", "Bearer secret")
        span.set_attribute("careerflow.run_id", "safe-id")
    provider.shutdown()
    content = target.read_text()
    assert "Bearer secret" not in content
    assert "[REDACTED]" in content
    assert "safe-id" in content
