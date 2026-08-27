"""OpenTelemetry setup and configuration"""
import os
import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION

logger = logging.getLogger("telemetry")

_tracer = None


def setup_telemetry(app=None, service_name="ai-devops-platform", service_version="3.2.1"):
    """Initialize OpenTelemetry"""
    global _tracer

    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    enable_console = os.environ.get("OTEL_CONSOLE_EXPORTER", "false").lower() == "true"

    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": os.environ.get("ENVIRONMENT", "development"),
    })

    provider = TracerProvider(resource=resource)

    # OTLP exporter (production)
    if otlp_endpoint:
        try:
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info("OTLP exporter configured: %s", otlp_endpoint)
        except Exception as e:
            logger.warning("OTLP exporter failed: %s", e)

    # Console exporter (debug)
    if enable_console:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        logger.info("Console span exporter enabled")

    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(service_name, service_version)

    # Instrument FastAPI
    if app is not None:
        try:
            FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
            logger.info("FastAPI instrumented for OpenTelemetry")
        except Exception as e:
            logger.warning("FastAPI instrumentation failed: %s", e)

    # Instrument SQLAlchemy
    try:
        SQLAlchemyInstrumentor().instrument(
            engine=None,  # auto-discover
            tracer_provider=provider,
        )
        logger.info("SQLAlchemy instrumented for OpenTelemetry")
    except Exception as e:
        logger.warning("SQLAlchemy instrumentation failed: %s", e)

    logger.info("OpenTelemetry initialized (service=%s v=%s)", service_name, service_version)
    return provider


def tracer():
    """Get the global tracer instance"""
    global _tracer
    if _tracer is None:
        setup_telemetry()
    return _tracer


def get_trace_id() -> str:
    """Get current trace ID from OpenTelemetry context"""
    span = trace.get_current_span()
    if span and span.get_span_context().trace_id:
        return format(span.get_span_context().trace_id, '032x')
    return ""


def trace_span(name: str, attributes: dict = None):
    """Decorator/context manager for tracing spans"""
    return tracer().start_as_current_span(name, attributes=attributes)
