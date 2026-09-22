"""Optional OpenTelemetry observability for Cascade Breaker.

Tracing is opt-in via CASCADE_BREAKER_TRACE=1.
No prompts, completions, credentials, or connection strings are recorded.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator


_TRUE_VALUES = {"1", "true", "yes", "on"}
_TRACER = None


def tracing_enabled() -> bool:
    return os.getenv("CASCADE_BREAKER_TRACE", "").strip().lower() in _TRUE_VALUES


def configure_foundry_tracer(project_client):
    """Configure Azure Monitor tracing once per process."""
    global _TRACER

    if not tracing_enabled():
        return None

    if _TRACER is not None:
        return _TRACER

    from azure.monitor.opentelemetry import configure_azure_monitor
    from opentelemetry import trace

    connection_string = (
        project_client.telemetry.get_application_insights_connection_string()
    )
    if not connection_string:
        raise RuntimeError(
            "Cascade Breaker tracing requested but no Application Insights "
            "connection string is linked to the Foundry project."
        )

    configure_azure_monitor(connection_string=connection_string)
    _TRACER = trace.get_tracer("cascade-breaker")
    return _TRACER


def set_span_attributes(span, attributes: dict[str, Any]) -> None:
    """Attach only non-None, audit-safe scalar attributes."""
    if span is None:
        return

    for key, value in attributes.items():
        if value is not None:
            span.set_attribute(key, value)


@contextmanager
def traced_span(
    tracer,
    name: str,
    attributes: dict[str, Any] | None = None,
    *,
    server_span: bool = False,
) -> Iterator[Any]:
    """Create a span when tracing is enabled; otherwise behave as a no-op."""
    if tracer is None:
        yield None
        return

    kwargs = {}
    if server_span:
        from opentelemetry.trace import SpanKind

        kwargs["kind"] = SpanKind.SERVER

    with tracer.start_as_current_span(name, **kwargs) as span:
        set_span_attributes(span, attributes or {})
        yield span

def flush_traces(timeout_millis: int = 10000) -> bool:
    """Force completed spans to the configured exporter before process exit."""
    if not tracing_enabled():
        return True

    from opentelemetry import trace

    provider = trace.get_tracer_provider()
    force_flush = getattr(provider, "force_flush", None)
    if not callable(force_flush):
        return False

    return bool(force_flush(timeout_millis=timeout_millis))
