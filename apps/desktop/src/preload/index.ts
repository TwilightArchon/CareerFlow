import { contextBridge, ipcRenderer } from 'electron';

import type {
  ApplicationMaterialPlan,
  ApplicationOutcome,
  ApplicationRun,
  ApplicationStatistics,
  CandidateProfileInput,
  CandidateProfileSnapshot,
  FieldExplanation,
  HealthStatus,
  JobPosting,
  ResumeImportResult,
  ResumePreviewResult,
  RecordApplicationOutcomeRequest,
  RunControlRequest,
} from '@careerflow/contracts';

export interface CareerFlowApi {
  getHealth(): Promise<HealthStatus>;
  listRuns(): Promise<ApplicationRun[]>;
  listFieldExplanations(input: { runId: string }): Promise<FieldExplanation[]>;
  recordApplicationOutcome(input: {
    runId: string;
    outcome: RecordApplicationOutcomeRequest;
  }): Promise<ApplicationOutcome>;
  getApplicationStatistics(): Promise<ApplicationStatistics>;
  controlRun(input: { runId: string; control: RunControlRequest }): Promise<ApplicationRun>;
  getProfile(): Promise<CandidateProfileSnapshot | null>;
  saveProfile(input: {
    profile: CandidateProfileInput;
    expectedVersion: number | null;
  }): Promise<CandidateProfileSnapshot>;
  importResume(input: {
    filename: string;
    mediaType: string;
    bytes: Uint8Array;
    expectedVersion: number;
  }): Promise<ResumeImportResult>;
  previewResume(input: {
    filename: string;
    mediaType: string;
    bytes: Uint8Array;
  }): Promise<ResumePreviewResult>;
  ingestJob(input: { url: string }): Promise<JobPosting>;
  prepareMaterials(input: {
    jobId: string;
    candidateProfileId: string;
    candidateProfileVersion: number;
  }): Promise<ApplicationMaterialPlan>;
  setEvidenceVerification(input: {
    evidenceId: string;
    verified: boolean;
    expectedVersion: number;
  }): Promise<CandidateProfileSnapshot>;
  createRun(input: {
    jobId: string;
    jobUrl: string;
    autoSubmitAuthorized: boolean;
  }): Promise<ApplicationRun>;
  startSyntheticDemo(): Promise<ApplicationRun>;
}

const api: CareerFlowApi = {
  getHealth: () => ipcRenderer.invoke('system:get-health') as Promise<HealthStatus>,
  listRuns: () => ipcRenderer.invoke('runs:list') as Promise<ApplicationRun[]>,
  listFieldExplanations: (input) =>
    ipcRenderer.invoke('runs:field-explanations:list', input) as Promise<FieldExplanation[]>,
  recordApplicationOutcome: (input) =>
    ipcRenderer.invoke('runs:outcome:record', input) as Promise<ApplicationOutcome>,
  getApplicationStatistics: () =>
    ipcRenderer.invoke('applications:statistics') as Promise<ApplicationStatistics>,
  controlRun: (input) => ipcRenderer.invoke('runs:control', input) as Promise<ApplicationRun>,
  getProfile: () => ipcRenderer.invoke('profile:get') as Promise<CandidateProfileSnapshot | null>,
  saveProfile: (input) =>
    ipcRenderer.invoke('profile:save', input) as Promise<CandidateProfileSnapshot>,
  importResume: (input) =>
    ipcRenderer.invoke('profile:resume:import', input) as Promise<ResumeImportResult>,
  previewResume: (input) =>
    ipcRenderer.invoke('profile:resume:preview', input) as Promise<ResumePreviewResult>,
  ingestJob: (input) => ipcRenderer.invoke('jobs:ingest', input) as Promise<JobPosting>,
  prepareMaterials: (input) =>
    ipcRenderer.invoke('materials:prepare', input) as Promise<ApplicationMaterialPlan>,
  setEvidenceVerification: (input) =>
    ipcRenderer.invoke('profile:evidence:verify', input) as Promise<CandidateProfileSnapshot>,
  createRun: (input) => ipcRenderer.invoke('runs:create', input),
  startSyntheticDemo: () => ipcRenderer.invoke('demo:synthetic:start') as Promise<ApplicationRun>,
};

contextBridge.exposeInMainWorld('careerflow', api);
