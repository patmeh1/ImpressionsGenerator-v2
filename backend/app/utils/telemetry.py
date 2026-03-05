"""OpenTelemetry setup for distributed tracing across the agent pipeline."""

import logging

from fastapi import FastAPI

from app.config import settings

logger = logging.getLogger(__name__)


def setup_telemetry(app: FastAPI) -> None:
    """Configure OpenTelemetry with Azure Monitor exporter."""
    try:
        from opentelemetry import trace
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({
            "service.name": "impressions-generator-v2",
            "service.version": "2.0.0",
            "deployment.environment": "production",
        })

        provider = TracerProvider(resource=resource)

        # Azure Monitor exporter
        if settings.APPLICATIONINSIGHTS_CONNECTION_STRING:
            from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

            exporter = AzureMonitorTraceExporter(
                connection_string=settings.APPLICATIONINSIGHTS_CONNECTION_STRING
            )
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info("Azure Monitor trace exporter configured")

        # OTLP exporter (for local development / Jaeger)
        if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )

            otlp_exporter = OTLPSpanExporter(
                endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT
            )
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info("OTLP trace exporter configured")

        trace.set_tracer_provider(provider)

        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(app)
        logger.info("OpenTelemetry instrumentation configured")

    except ImportError as e:
        logger.warning("OpenTelemetry not available: %s", e)
    except Exception as e:
        logger.warning("Failed to configure telemetry: %s", e)
