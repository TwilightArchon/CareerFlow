import { join } from 'node:path';

import { app, BrowserWindow, ipcMain } from 'electron';

import { ProcessSupervisor } from './supervisor';
import { startTelemetry } from './telemetry';

const telemetry = startTelemetry();
const supervisor = new ProcessSupervisor();
let mainWindow: BrowserWindow | undefined;

function createWindow(): BrowserWindow {
  const window = new BrowserWindow({
    width: 1240,
    height: 820,
    minWidth: 980,
    minHeight: 680,
    backgroundColor: '#f4f3ef',
    show: false,
    webPreferences: {
      preload: join(__dirname, '../preload/index.cjs'),
      sandbox: true,
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: true,
    },
  });
  window.once('ready-to-show', () => window.show());
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  window.webContents.on('will-navigate', (event) => event.preventDefault());

  if (!app.isPackaged && process.env.ELECTRON_RENDERER_URL) {
    void window.loadURL(process.env.ELECTRON_RENDERER_URL);
  } else {
    void window.loadFile(join(__dirname, '../renderer/index.html'));
  }
  return window;
}

app.whenReady().then(async () => {
  ipcMain.handle('system:get-health', () => supervisor.refreshHealth());
  ipcMain.handle('runs:list', () => supervisor.listRuns());
  ipcMain.handle('runs:field-explanations:list', (_event, input: { runId: string }) =>
    supervisor.listFieldExplanations(input.runId),
  );
  ipcMain.handle(
    'runs:outcome:record',
    (
      _event,
      input: {
        runId: string;
        outcome: import('@careerflow/contracts').RecordApplicationOutcomeRequest;
      },
    ) => supervisor.recordApplicationOutcome(input.runId, input.outcome),
  );
  ipcMain.handle('applications:statistics', () => supervisor.getApplicationStatistics());
  ipcMain.handle('profile:get', () => supervisor.getProfile());
  ipcMain.handle(
    'profile:save',
    (
      _event,
      input: {
        profile: import('@careerflow/contracts').CandidateProfileInput;
        expectedVersion: number | null;
      },
    ) => supervisor.saveProfile(input.profile, input.expectedVersion),
  );
  ipcMain.handle(
    'profile:resume:import',
    (
      _event,
      input: {
        filename: string;
        mediaType: string;
        bytes: Uint8Array;
        expectedVersion: number;
      },
    ) => supervisor.importResume(input),
  );
  ipcMain.handle(
    'profile:resume:preview',
    (
      _event,
      input: {
        filename: string;
        mediaType: string;
        bytes: Uint8Array;
      },
    ) => supervisor.previewResume(input),
  );
  ipcMain.handle(
    'profile:evidence:verify',
    (_event, input: { evidenceId: string; verified: boolean; expectedVersion: number }) =>
      supervisor.setEvidenceVerification(input.evidenceId, input.verified, input.expectedVersion),
  );
  ipcMain.handle('jobs:ingest', (_event, input: { url: string }) =>
    supervisor.ingestJob(input.url),
  );
  ipcMain.handle(
    'materials:prepare',
    (
      _event,
      input: {
        jobId: string;
        candidateProfileId: string;
        candidateProfileVersion: number;
      },
    ) => supervisor.prepareMaterials(input),
  );
  ipcMain.handle(
    'runs:create',
    (_event, input: { jobId: string; jobUrl: string; autoSubmitAuthorized: boolean }) =>
      supervisor.createRun(input.jobId, input.jobUrl, input.autoSubmitAuthorized),
  );
  ipcMain.handle('demo:synthetic:start', () => supervisor.startSyntheticDemo());
  mainWindow = createWindow();
  try {
    await supervisor.start();
  } catch (error) {
    process.stderr.write(`CareerFlow startup failed: ${String(error)}\n`);
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', (event) => {
  if (mainWindow) mainWindow = undefined;
  event.preventDefault();
  void supervisor
    .stop()
    .then(() => telemetry.shutdown())
    .finally(() => app.exit(0));
});
