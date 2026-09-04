import { context, metrics, propagation, SpanStatusCode, trace } from '@opentelemetry/api';
import WebSocket from 'ws';

import { BrowserCommandSchema, BrowserWorkerMessageSchema } from '@careerflow/contracts';

import { BrowserRuntime } from './runtime';
import { requireLoopbackWebSocketUrl } from './security';
import { startTelemetry } from './telemetry';

const WORKER_VERSION = '0.1.9';
const sdk = startTelemetry();
const tracer = trace.getTracer('careerflow-browser-worker', WORKER_VERSION);
const meter = metrics.getMeter('careerflow-browser-worker', WORKER_VERSION);
const browserActions = meter.createCounter('browser_actions_total');
const browserActionDuration = meter.createHistogram('browser_action_duration_ms', {
  unit: 'ms',
});

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
    const startedAt = performance.now();
    let result: 'ok' | 'error' = 'error';
    span.setAttribute('careerflow.run_id', command.envelope.runId);
    span.setAttribute('careerflow.browser.command', command.action);
    try {
      if (command.action === 'navigate' && command.url) {
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
      } else if (command.action === 'open_synthetic_form' || command.action === 'scan') {
        const observedForm =
          command.action === 'open_synthetic_form'
            ? await runtime.openSyntheticForm()
            : await runtime.scanCurrentForm();
        span.setAttribute('careerflow.browser.control_count', observedForm.controls.length);
        ws.send(
          JSON.stringify(
            BrowserWorkerMessageSchema.parse({
              type: 'form_observed',
              actionId: command.commandId,
              runId: command.envelope.runId,
              observedForm,
            }),
          ),
        );
      } else if (command.action === 'fill') {
        const filledMappings = await runtime.fillApprovedFields(
          command.fills,
          command.expectedPageStateHash,
        );
        const observedForm = await runtime.scanCurrentForm();
        span.setAttribute('careerflow.browser.filled_count', filledMappings.length);
        span.setAttribute('careerflow.browser.blocked_count', command.blockedMappings.length);
        ws.send(
          JSON.stringify(
            BrowserWorkerMessageSchema.parse({
              type: 'fill_result',
              actionId: command.commandId,
              runId: command.envelope.runId,
              ok: true,
              pageStateHash: observedForm.pageStateHash,
              filledMappings,
              blockedMappings: command.blockedMappings,
            }),
          ),
        );
      } else {
        throw new Error(`Unsupported browser command: ${command.action}`);
      }
      result = 'ok';
      span.setStatus({ code: SpanStatusCode.OK });
    } catch (error) {
      span.recordException(error as Error);
      span.setStatus({ code: SpanStatusCode.ERROR });
      const failedMessage =
        command.action === 'fill'
          ? {
              type: 'fill_result' as const,
              actionId: command.commandId,
              runId: command.envelope.runId,
              ok: false,
              filledMappings: [],
              blockedMappings: command.blockedMappings,
              errorCode: 'fill_failed',
            }
          : {
              type: 'action_result' as const,
              actionId: command.commandId,
              runId: command.envelope.runId,
              ok: false,
              errorCode:
                command.action === 'open_synthetic_form' || command.action === 'scan'
                  ? 'scan_failed'
                  : 'navigation_failed',
            };
      ws.send(JSON.stringify(BrowserWorkerMessageSchema.parse(failedMessage)));
    } finally {
      const attributes = { action: command.action, result };
      browserActions.add(1, attributes);
      browserActionDuration.record(performance.now() - startedAt, attributes);
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
