import { randomBytes } from 'node:crypto';
import { spawn, type ChildProcess } from 'node:child_process';
import { existsSync } from 'node:fs';
import { createServer } from 'node:net';
import { dirname, join, resolve } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';

import { context, propagation, SpanStatusCode, trace } from '@opentelemetry/api';
import { app, utilityProcess, type UtilityProcess } from 'electron';

import {
  ApplicationMaterialPlanSchema,
  ApplicationOutcomeSchema,
  ApplicationRunSchema,
  ApplicationStatisticsSchema,
  CandidateProfileSnapshotSchema,
  FieldExplanationSchema,
  HealthStatusSchema,
  JobPostingSchema,
  ResumeImportResultSchema,
  ResumePreviewResultSchema,
  RecordApplicationOutcomeRequestSchema,
  type ApplicationOutcome,
  type ApplicationRun,
  type ApplicationStatistics,
  type ApplicationMaterialPlan,
  type CandidateProfileInput,
  type CandidateProfileSnapshot,
  type FieldExplanation,
  type HealthStatus,
  type JobPosting,
  type ResumeImportResult,
  type ResumePreviewResult,
  type RecordApplicationOutcomeRequest,
} from '@careerflow/contracts';

const tracer = trace.getTracer('careerflow.desktop.supervisor');

function projectRoot(start: string): string {
  let current = resolve(start);
  while (dirname(current) !== current) {
    if (existsSync(join(current, 'pnpm-workspace.yaml'))) return current;
    current = dirname(current);
  }
  throw new Error('Could not locate the CareerFlow workspace root');
}

async function availablePort(): Promise<number> {
  return await new Promise((resolvePort, reject) => {
    const server = createServer();
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      if (!address || typeof address === 'string') {
        server.close();
        reject(new Error('Failed to allocate loopback port'));
        return;
      }
      server.close((error) => (error ? reject(error) : resolvePort(address.port)));
    });
  });
}

export class ProcessSupervisor {
  private agent: ChildProcess | undefined;
  private agentStartError: Error | undefined;
  private browserWorker: UtilityProcess | undefined;
  private stopping = false;
  private port?: number;
  private token?: string;
  private readiness: HealthStatus | undefined;

  get health(): HealthStatus {
    return (
      this.readiness ?? {
        status: 'starting',
        service: 'careerflow-agent',
        version: '0.1.9',
        browserWorkerConnected: false,
        databaseReady: false,
        telemetryReady: false,
      }
    );
  }

  async start(): Promise<HealthStatus> {
    this.stopping = false;
    this.agentStartError = undefined;
    this.port = await availablePort();
    this.token = randomBytes(32).toString('base64url');

    const root = app.isPackaged ? undefined : projectRoot(app.getAppPath());
    const serviceDir = app.isPackaged
      ? join(process.resourcesPath, 'agent-service')
      : join(root!, 'services', 'agent');
    const dataDir = join(app.getPath('userData'), 'data');
    const agentExecutable = app.isPackaged
      ? join(process.resourcesPath, 'python-runtime', 'bin', 'python3.13')
      : this.uvExecutable();
    const agentArguments = app.isPackaged
      ? ['-m', 'careerflow_agent']
      : ['run', '--project', serviceDir, '--no-sync', 'careerflow-agent'];
    this.agent = spawn(agentExecutable, agentArguments, {
      env: {
        ...process.env,
        CAREERFLOW_PORT: String(this.port),
        CAREERFLOW_LOCAL_TOKEN: this.token,
        CAREERFLOW_DATA_DIR: dataDir,
        ...(app.isPackaged
          ? {
              PYTHONNOUSERSITE: '1',
              PYTHONPATH: join(serviceDir, 'src'),
            }
          : {}),
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    this.agent.once('error', (error) => {
      this.agentStartError = error;
    });
    this.agent.once('exit', (code, signal) => {
      if (!this.stopping && code !== 0) {
        this.agentStartError = new Error(
          `agent process exited before startup (code ${String(code)}, signal ${String(signal)})`,
        );
      }
    });
    this.agent.stdout?.on('data', (chunk: Buffer) =>
      process.stdout.write(`[agent] ${chunk.toString()}`),
    );
    this.agent.stderr?.on('data', (chunk: Buffer) =>
      process.stderr.write(`[agent] ${chunk.toString()}`),
    );

    this.readiness = await this.waitForHealth();
    const workerEntry = app.isPackaged
      ? join(app.getAppPath(), 'node_modules', '@careerflow', 'browser-worker', 'dist', 'index.js')
      : join(root!, 'packages', 'browser-worker', 'dist', 'index.js');
    this.browserWorker = utilityProcess.fork(workerEntry, [], {
      env: {
        ...process.env,
        CAREERFLOW_BROWSER_WS_URL: `ws://127.0.0.1:${this.port}/v1/browser/ws`,
        CAREERFLOW_LOCAL_TOKEN: this.token,
        CAREERFLOW_BROWSER_PROFILE_DIR: join(app.getPath('userData'), 'browser-profile'),
      },
      stdio: 'pipe',
      serviceName: 'CareerFlow Browser Worker',
    });
    this.browserWorker.stdout?.on('data', (chunk: Buffer) =>
      process.stdout.write(`[browser] ${chunk.toString()}`),
    );
    this.browserWorker.stderr?.on('data', (chunk: Buffer) =>
      process.stderr.write(`[browser] ${chunk.toString()}`),
    );
    await delay(250);
    this.readiness = await this.fetchHealth();
    return this.readiness;
  }

  async stop(): Promise<void> {
    this.stopping = true;
    this.browserWorker?.kill();
    this.browserWorker = undefined;
    this.agent?.kill('SIGTERM');
    this.agent = undefined;
    this.readiness = undefined;
  }

  async refreshHealth(): Promise<HealthStatus> {
    if (!this.port || !this.token) return this.health;
    try {
      this.readiness = await this.fetchHealth();
    } catch {
      this.readiness = {
        ...this.health,
        status: this.stopping ? 'stopped' : this.agentStartError ? 'degraded' : 'starting',
      };
    }
    return this.readiness;
  }

  async listRuns(): Promise<ApplicationRun[]> {
    if (!this.port || !this.token) throw new Error('Local service is not ready');
    const response = await fetch(`http://127.0.0.1:${this.port}/v1/runs`, {
      headers: { Authorization: `Bearer ${this.token}` },
    });
    if (!response.ok) throw new Error(`Local service returned ${response.status}`);
    return ApplicationRunSchema.array().parse(await response.json());
  }

  async listFieldExplanations(runId: string): Promise<FieldExplanation[]> {
    if (!this.port || !this.token) throw new Error('Local service is not ready');
    const response = await fetch(
      `http://127.0.0.1:${this.port}/v1/runs/${encodeURIComponent(runId)}/field-explanations`,
      { headers: { Authorization: `Bearer ${this.token}` } },
    );
    if (!response.ok) throw await this.responseError(response);
    return FieldExplanationSchema.array().parse(await response.json());
  }

  async recordApplicationOutcome(
    runId: string,
    input: RecordApplicationOutcomeRequest,
  ): Promise<ApplicationOutcome> {
    if (!this.port || !this.token) throw new Error('Local service is not ready');
    const request = RecordApplicationOutcomeRequestSchema.parse(input);
    const response = await fetch(
      `http://127.0.0.1:${this.port}/v1/runs/${encodeURIComponent(runId)}/outcome`,
      {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${this.token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      },
    );
    if (!response.ok) throw await this.responseError(response);
    return ApplicationOutcomeSchema.parse(await response.json());
  }

  async getApplicationStatistics(): Promise<ApplicationStatistics> {
    if (!this.port || !this.token) throw new Error('Local service is not ready');
    const response = await fetch(`http://127.0.0.1:${this.port}/v1/application-statistics`, {
      headers: { Authorization: `Bearer ${this.token}` },
    });
    if (!response.ok) throw await this.responseError(response);
    return ApplicationStatisticsSchema.parse(await response.json());
  }

  async getProfile(): Promise<CandidateProfileSnapshot | null> {
    if (!this.port || !this.token) throw new Error('Local service is not ready');
    const response = await fetch(`http://127.0.0.1:${this.port}/v1/profile`, {
      headers: { Authorization: `Bearer ${this.token}` },
    });
    if (!response.ok) throw await this.responseError(response);
    const payload: unknown = await response.json();
    return payload === null ? null : CandidateProfileSnapshotSchema.parse(payload);
  }

  async saveProfile(
    profile: CandidateProfileInput,
    expectedVersion: number | null,
  ): Promise<CandidateProfileSnapshot> {
    if (!this.port || !this.token) throw new Error('Local service is not ready');
    const response = await fetch(`http://127.0.0.1:${this.port}/v1/profile`, {
      method: 'PUT',
      headers: {
        Authorization: `Bearer ${this.token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ profile, expectedVersion }),
    });
    if (!response.ok) throw await this.responseError(response);
    return CandidateProfileSnapshotSchema.parse(await response.json());
  }

  async importResume(input: {
    filename: string;
    mediaType: string;
    bytes: Uint8Array;
    expectedVersion: number;
  }): Promise<ResumeImportResult> {
    if (!this.port || !this.token) throw new Error('Local service is not ready');
    const form = new FormData();
    const arrayBuffer = new ArrayBuffer(input.bytes.byteLength);
    new Uint8Array(arrayBuffer).set(input.bytes);
    form.append('expected_version', String(input.expectedVersion));
    form.append('file', new Blob([arrayBuffer], { type: input.mediaType }), input.filename);
    const response = await fetch(`http://127.0.0.1:${this.port}/v1/profile/resume`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${this.token}` },
      body: form,
    });
    if (!response.ok) throw await this.responseError(response);
    return ResumeImportResultSchema.parse(await response.json());
  }

  async previewResume(input: {
    filename: string;
    mediaType: string;
    bytes: Uint8Array;
  }): Promise<ResumePreviewResult> {
    if (!this.port || !this.token) throw new Error('Local service is not ready');
    const form = new FormData();
    const arrayBuffer = new ArrayBuffer(input.bytes.byteLength);
    new Uint8Array(arrayBuffer).set(input.bytes);
    form.append('file', new Blob([arrayBuffer], { type: input.mediaType }), input.filename);
    const response = await fetch(`http://127.0.0.1:${this.port}/v1/profile/resume/preview`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${this.token}` },
      body: form,
    });
    if (!response.ok) throw await this.responseError(response);
    return ResumePreviewResultSchema.parse(await response.json());
  }

  async ingestJob(url: string): Promise<JobPosting> {
    if (!this.port || !this.token) throw new Error('Local service is not ready');
    const response = await fetch(`http://127.0.0.1:${this.port}/v1/jobs/ingest`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${this.token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ url }),
    });
    if (!response.ok) throw await this.responseError(response);
    return JobPostingSchema.parse(await response.json());
  }

  async prepareMaterials(input: {
    jobId: string;
    candidateProfileId: string;
    candidateProfileVersion: number;
  }): Promise<ApplicationMaterialPlan> {
    if (!this.port || !this.token) throw new Error('Local service is not ready');
    const response = await fetch(`http://127.0.0.1:${this.port}/v1/materials/prepare`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${this.token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(input),
    });
    if (!response.ok) throw await this.responseError(response);
    return ApplicationMaterialPlanSchema.parse(await response.json());
  }

  async setEvidenceVerification(
    evidenceId: string,
    verified: boolean,
    expectedVersion: number,
  ): Promise<CandidateProfileSnapshot> {
    if (!this.port || !this.token) throw new Error('Local service is not ready');
    const response = await fetch(
      `http://127.0.0.1:${this.port}/v1/profile/evidence/${evidenceId}/verification`,
      {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${this.token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ expectedVersion, verified }),
      },
    );
    if (!response.ok) throw await this.responseError(response);
    return CandidateProfileSnapshotSchema.parse(await response.json());
  }

  async createRun(
    jobId: string,
    jobUrl: string,
    autoSubmitAuthorized: boolean,
  ): Promise<ApplicationRun> {
    if (!this.port || !this.token) throw new Error('Local service is not ready');
    return await tracer.startActiveSpan('application.run.create', async (span) => {
      try {
        const profile = await this.getProfile();
        if (!profile)
          throw new Error('Complete your verified profile before opening an application');
        const headers: Record<string, string> = {
          Authorization: `Bearer ${this.token}`,
          'Content-Type': 'application/json',
        };
        propagation.inject(context.active(), headers);
        const response = await fetch(`http://127.0.0.1:${this.port}/v1/runs`, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            job_id: jobId,
            candidate_profile_id: profile.profile.id,
            candidate_profile_version: profile.profile.version,
            autoSubmitAuthorized,
            jobUrl,
          }),
        });
        if (!response.ok) throw new Error(`Local service returned ${response.status}`);
        const run = ApplicationRunSchema.parse(await response.json());
        span.setAttribute('careerflow.run_id', run.id);
        span.setStatus({ code: SpanStatusCode.OK });
        return run;
      } catch (error) {
        span.recordException(error as Error);
        span.setStatus({ code: SpanStatusCode.ERROR });
        throw error;
      } finally {
        span.end();
      }
    });
  }

  async startSyntheticDemo(): Promise<ApplicationRun> {
    if (!this.port || !this.token) throw new Error('Local service is not ready');
    const profile = await this.getProfile();
    if (!profile) throw new Error('Create your verified profile before testing autofill');
    const response = await fetch(`http://127.0.0.1:${this.port}/v1/demo/synthetic-run`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${this.token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        candidateProfileId: profile.profile.id,
        candidateProfileVersion: profile.profile.version,
      }),
    });
    if (!response.ok) throw await this.responseError(response);
    return ApplicationRunSchema.parse(await response.json());
  }

  private async waitForHealth(): Promise<HealthStatus> {
    let lastError: unknown;
    const attempts = app.isPackaged ? 200 : 80;
    for (let attempt = 0; attempt < attempts; attempt += 1) {
      if (this.agentStartError) {
        throw new Error(
          `CareerFlow could not start its local service: ${this.agentStartError.message}`,
        );
      }
      try {
        return await this.fetchHealth();
      } catch (error) {
        lastError = error;
        await delay(100);
      }
    }
    throw new Error(`CareerFlow service did not become ready: ${String(lastError)}`);
  }

  private uvExecutable(): string {
    const configured = process.env.CAREERFLOW_UV_PATH;
    if (configured) return configured;

    const home = app.getPath('home');
    const candidates = [
      '/opt/homebrew/bin/uv',
      '/usr/local/bin/uv',
      join(home, '.local', 'bin', 'uv'),
      join(home, '.cargo', 'bin', 'uv'),
    ];
    return candidates.find((candidate) => existsSync(candidate)) ?? 'uv';
  }

  private async fetchHealth(): Promise<HealthStatus> {
    if (!this.port || !this.token) throw new Error('Local service is not configured');
    const response = await fetch(`http://127.0.0.1:${this.port}/v1/health`, {
      headers: { Authorization: `Bearer ${this.token}` },
    });
    if (!response.ok) throw new Error(`Health check returned ${response.status}`);
    return HealthStatusSchema.parse(await response.json());
  }

  private async responseError(response: Response): Promise<Error> {
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === 'string') return new Error(body.detail);
      if (
        body.detail &&
        typeof body.detail === 'object' &&
        'message' in body.detail &&
        typeof body.detail.message === 'string'
      ) {
        return new Error(body.detail.message);
      }
    } catch {
      // Fall through to the status-only error when the local service returned no JSON body.
    }
    return new Error(`Local service returned ${response.status}`);
  }
}
