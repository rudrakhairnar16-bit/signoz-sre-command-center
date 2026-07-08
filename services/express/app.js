const http = require('http');
const { OTLPTraceExporter } = require('@opentelemetry/exporter-trace-otlp-http');
const { Resource } = require('@opentelemetry/resources');
const { SemanticResourceAttributes } = require('@opentelemetry/semantic-conventions');
const { NodeTracerProvider } = require('@opentelemetry/sdk-trace-node');
const { BatchSpanProcessor } = require('@opentelemetry/sdk-trace-base');
const { ExpressInstrumentation } = require('@opentelemetry/instrumentation-express');
const { HttpInstrumentation } = require('@opentelemetry/instrumentation-http');
const { registerInstrumentations } = require('@opentelemetry/instrumentation');

const OTEL_ENDPOINT = process.env.OTEL_EXPORTER_OTLP_ENDPOINT || 'http://otel-collector:4318/v1/traces';
const GOWORKER_URL = process.env.GOWORKER_URL || 'http://goworker-svc:8080';

const resource = new Resource({
  [SemanticResourceAttributes.SERVICE_NAME]: 'express-svc',
});
const provider = new NodeTracerProvider({ resource });
const exporter = new OTLPTraceExporter({ url: OTEL_ENDPOINT });
provider.addSpanProcessor(new BatchSpanProcessor(exporter));
provider.register();

registerInstrumentations({
  instrumentations: [
    new ExpressInstrumentation(),
    new HttpInstrumentation(),
  ],
});

const express = require('express');
const app = express();
app.use(express.json());

const api = require('@opentelemetry/api');
const tracer = api.trace.getTracer('express-svc');

function logWithTrace(msg) {
  const span = api.trace.getSpan(api.context.active());
  const ctx = span ? span.spanContext() : null;
  const tid = ctx ? ctx.traceId : '';
  const sid = ctx ? ctx.spanId : '';
  console.log(`${new Date().toISOString()} [express-svc] trace_id=${tid} span_id=${sid} ${msg}`);
}

app.get('/execute', async (req, res) => {
  const span = api.trace.getSpan(api.context.active());
  if (span) {
    span.setAttribute('slo_tier', 'standard');
    span.setAttribute('service.version', '1.0.0');
  }
  logWithTrace('Processing execute request');

  const result = await new Promise((resolve, reject) => {
    http.get(`${GOWORKER_URL}/work`, (resp) => {
      let data = '';
      resp.on('data', (chunk) => data += chunk);
      resp.on('end', () => {
        try { resolve(JSON.parse(data)); }
        catch (e) { reject(e); }
      });
    }).on('error', reject);
  });

  if (span) {
    span.setAttribute('goworker.status', result.status);
    span.addEvent('goworker_response_received', { status: result.status });
  }
  logWithTrace(`GoWorker response received: ${result.status}`);

  res.json({ service: 'express-svc', goworker_result: result });
});

app.get('/health', (req, res) => res.json({ status: 'ok' }));

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`express-svc on :${PORT}`));
