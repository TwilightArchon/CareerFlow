import { contextBridge, ipcRenderer } from 'electron';

import type {
  ApplicationRun,
  CandidateProfileInput,
  CandidateProfileSnapshot,
  HealthStatus,
  ResumeImportResult,
} from '@careerflow/contracts';

export interface CareerFlowApi {
  getHealth(): Promise<HealthStatus>;
  listRuns(): Promise<ApplicationRun[]>;
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
  setEvidenceVerification(input: {
    evidenceId: string;
    verified: boolean;
    expectedVersion: number;
  }): Promise<CandidateProfileSnapshot>;
  createRun(input: { jobUrl: string; autoSubmitAuthorized: boolean }): Promise<ApplicationRun>;
}

const api: CareerFlowApi = {
  getHealth: () => ipcRenderer.invoke('system:get-health') as Promise<HealthStatus>,
  listRuns: () => ipcRenderer.invoke('runs:list') as Promise<ApplicationRun[]>,
  getProfile: () => ipcRenderer.invoke('profile:get') as Promise<CandidateProfileSnapshot | null>,
  saveProfile: (input) =>
    ipcRenderer.invoke('profile:save', input) as Promise<CandidateProfileSnapshot>,
  importResume: (input) =>
    ipcRenderer.invoke('profile:resume:import', input) as Promise<ResumeImportResult>,
  setEvidenceVerification: (input) =>
    ipcRenderer.invoke('profile:evidence:verify', input) as Promise<CandidateProfileSnapshot>,
  createRun: (input) => ipcRenderer.invoke('runs:create', input),
};

contextBridge.exposeInMainWorld('careerflow', api);
