from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from threading import Lock

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter, SpanExportResult

from .config import Settings
from .security import redact


class RedactedFileSpanExporter(SpanExporter):
    """Bounded local diagnostics with allowlisted structural span data."""

    def __init__(self, path: Path, max_bytes: int) -> None:
        self.path = path
        self.max_bytes = max_bytes
        self._lock = Lock()

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        lines = []
        for span in spans:
            parent_id = f"{span.parent.span_id:016x}" if span.parent else None
            lines.append(
                json.dumps(
                    {
                        "name": span.name,
                        "trace_id": f"{span.context.trace_id:032x}" if span.context else None,
                        "span_id": f"{span.context.span_id:016x}" if span.context else None,
                        "parent_span_id": parent_id,
                        "start_time_ns": span.start_time,
                        "end_time_ns": span.end_time,
                        "status": span.status.status_code.name,
                        "attributes": redact(dict(span.attributes or {})),
                    },
                    separators=(",", ":"),
                )
            )
        payload = ("\n".join(lines) + "\n").encode()
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            current_size = self.path.stat().st_size if self.path.exists() else 0
            if current_size + len(payload) > self.max_bytes:
                rotated = self.path.with_suffix(self.path.suffix + ".1")
                if rotated.exists():
                    rotated.unlink()
                if self.path.exists():
                    self.path.replace(rotated)
            with self.path.open("ab") as destination:
                destination.write(payload)
        return SpanExportResult.SUCCESS


def configure_telemetry(settings: Settings) -> bool:
    resource = Resource.create({"service.name": "careerflow-agent", "service.version": "0.1.5"})
    tracer_provider = TracerProvider(resource=resource)
    endpoint = settings.otel_exporter_otlp_endpoint
    if endpoint:
        tracer_provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces"))
        )
    if settings.local_diagnostics_enabled:
        tracer_provider.add_span_processor(
            BatchSpanProcessor(
                RedactedFileSpanExporter(
                    settings.data_dir / "diagnostics" / "spans.jsonl",
                    settings.diagnostics_max_bytes,
                )
            )
        )
    trace.set_tracer_provider(tracer_provider)

    readers = []
    if endpoint:
        readers.append(
            PeriodicExportingMetricReader(
                OTLPMetricExporter(endpoint=f"{endpoint.rstrip('/')}/v1/metrics")
            )
        )
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=readers))
    HTTPXClientInstrumentor().instrument()
    return endpoint is not None or settings.local_diagnostics_enabled
