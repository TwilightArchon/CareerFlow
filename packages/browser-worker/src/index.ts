import { context, propagation, SpanStatusCode, trace } from '@opentelemetry/api';
import WebSocket from 'ws';

import { BrowserCommandSchema, BrowserWorkerMessageSchema } from '@careerflow/contracts';

import { BrowserRuntime } from './runtime';
import { requireLoopbackWebSocketUrl } from './security';
import { startTelemetry } from './telemetry';

const WORKER_VERSION = '0.1.5';
const sdk = startTelemetry();
const tracer = trace.getTracer('careerflow-browser-worker', WORKER_VERSION);

const rawUrl = process.env.CAREERFLOW_BROWSER_WS_URL;
const token = process.env.CAREERFLOW_LOCAL_TOKEN;
const profileDir = process.env.CAREERFLOW_BROWSER_PROFILE_DIR;

if (!rawUrl || !token || !profileDir) {
  throw new Error(
    'CAREERFLOW_BROWSER_WS_URL, CAREERFLOW_LOCAL_TOKEN, and CAREERFLOW_BROWSER_PROFILE_DIR are required',
  );
}

const url = requireLoopbackWebSocketUrl(rawUrl);
let heartbeat: NodeJS.Timeout | undefined;
const runtime = new BrowserRuntime(profileDir);

const ws = new WebSocket(url, {
  headers: { Authorization: `Bearer ${token}` },
});

ws.on('open', () => {
  tracer.startActiveSpan('browser.connect', (span) => {
    const message = BrowserWorkerMessageSchema.parse({
      type: 'ready',
      workerVersion: WORKER_VERSION,
    });
    ws.send(JSON.stringify(message));
    span.setStatus({ code: SpanStatusCode.OK });
    span.end();
  });

  heartbeat = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(
        JSON.stringify(
          BrowserWorkerMessageSchema.parse({
            type: 'heartbeat',
            timestamp: new Date().toISOString(),
          }),
        ),
      );
    }
  }, 5_000);
});

ws.on('message', (data) => {
  const command = BrowserCommandSchema.parse(JSON.parse(data.toString()));
  const carrier = command.envelope.traceContext.traceparent
    ? { traceparent: command.envelope.traceContext.traceparent }
    : {};
  const parent = propagation.extract(context.active(), carrier);
  void tracer.startActiveSpan('browser.action', {}, parent, async (span) => {
    span.setAttribute('careerflow.run_id', command.envelope.runId);
    span.setAttribute('careerflow.browser.command', command.action);
    try {
      if (command.action !== 'navigate' || !command.url) {
        throw new Error(`Unsupported browser command: ${command.action}`);
      }
      const pageStateHash = await runtime.navigate(command.url);
      ws.send(
        JSON.stringify(
          BrowserWorkerMessageSchema.parse({
            type: 'action_result',
            actionId: command.commandId,
            runId: command.envelope.runId,
            ok: true,
            pageStateHash,
          }),
        ),
      );
      span.setStatus({ code: SpanStatusCode.OK });
    } catch (error) {
      span.recordException(error as Error);
      span.setStatus({ code: SpanStatusCode.ERROR });
      ws.send(
        JSON.stringify(
          BrowserWorkerMessageSchema.parse({
            type: 'action_result',
            actionId: command.commandId,
            runId: command.envelope.runId,
            ok: false,
            errorCode: 'navigation_failed',
          }),
        ),
      );
    } finally {
      span.end();
    }
  });
});

ws.on('close', () => {
  if (heartbeat) clearInterval(heartbeat);
  void runtime
    .close()
    .then(() => sdk.shutdown())
    .finally(() => process.exit(0));
});

ws.on('error', (error) => {
  process.stderr.write(`Browser worker connection failed: ${error.message}\n`);
});

for (const signal of ['SIGTERM', 'SIGINT'] as const) {
  process.on(signal, () => {
    if (heartbeat) clearInterval(heartbeat);
    void runtime.close().finally(() => ws.close());
  });
}
