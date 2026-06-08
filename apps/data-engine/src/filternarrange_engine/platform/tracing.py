"""Plan G §T12 — OpenTelemetry wiring for the data-engine.

``configure_tracing(app)`` is opt-in: it runs only when ``OTEL_TRACES_EXPORTER``
is set to a value other than ``none`` (the default in unit tests). FastAPI is
auto-instrumented so every incoming request that carries a ``traceparent``
header is stitched onto the gateway's parent span; outgoing httpx calls (to
plugins / Ollama) inherit the active span via httpx's automatic context
propagation in the OTel httpx instrumentation.

Endpoint defaults match the dev compose stack — the ``otel-collector`` service
listens on ``4318`` for HTTP/protobuf OTLP. The prod overlay sets
``OTEL_EXPORTER_OTLP_ENDPOINT`` to whatever the real collector is.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI


def configure_tracing(app: "FastAPI") -> None:
    if os.environ.get("OTEL_TRACES_EXPORTER", "none").lower() == "none":
        return

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.propagate import set_global_textmap
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.trace.propagation.tracecontext import (
        TraceContextTextMapPropagator,
    )

    endpoint = os.environ.get(
        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318"
    )
    service = os.environ.get("OTEL_SERVICE_NAME", "fna-data-engine")

    provider = TracerProvider(resource=Resource.create({"service.name": service}))
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces"))
    )
    trace.set_tracer_provider(provider)
    set_global_textmap(TraceContextTextMapPropagator())
    FastAPIInstrumentor.instrument_app(app)
