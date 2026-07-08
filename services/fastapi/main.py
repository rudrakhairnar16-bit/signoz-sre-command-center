import os
import logging
import httpx
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

class TraceIdFilter(logging.Filter):
    def filter(self, record):
        span = trace.get_current_span()
        ctx = span.get_span_context() if span else None
        if ctx and ctx.trace_id:
            record.trace_id = format(ctx.trace_id, '032x')
            record.span_id = format(ctx.span_id, '016x')
        else:
            record.trace_id = ''
            record.span_id = ''
        return True

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] trace_id=%(trace_id)s span_id=%(span_id)s %(message)s',
)
logger = logging.getLogger("fastapi-svc")
logger.addFilter(TraceIdFilter())

OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318/v1/traces")
EXPRESS_URL = os.getenv("EXPRESS_URL", "http://express-svc:3000")

resource = Resource(attributes={SERVICE_NAME: "fastapi-svc"})
provider = TracerProvider(resource=resource)
exporter = OTLPSpanExporter(endpoint=OTEL_ENDPOINT)
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

app = FastAPI(title="fastapi-svc")
FastAPIInstrumentor.instrument_app(app)
HTTPXClientInstrumentor().instrument()


@app.get("/process")
async def process():
    logger.info("Processing request")
    with tracer.start_as_current_span("process_request") as span:
        span.set_attribute("slo_tier", "critical")
        span.set_attribute("service.version", "1.0.0")

        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{EXPRESS_URL}/execute")
            result = resp.json()

        span.set_attribute("express.status", result.get("status", "unknown"))
        span.add_event("express_response_received", {"status": result.get("status", "unknown")})
        logger.info("Express response received", extra={"express_status": result.get("status", "unknown")})

    return {"service": "fastapi-svc", "express_result": result}


@app.get("/health")
async def health():
    return {"status": "ok"}
