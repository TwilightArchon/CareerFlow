import react from '@vitejs/plugin-react';
import { defineConfig, externalizeDepsPlugin } from 'electron-vite';

export default defineConfig({
  main: {
    // Workspace TypeScript must be compiled into the Electron entrypoint. Leaving it external
    // makes the packaged app ask Node to execute a .ts file from app.asar/node_modules.
    plugins: [externalizeDepsPlugin({ exclude: ['@careerflow/contracts'] })],
    build: { sourcemap: true },
  },
  preload: {
    plugins: [externalizeDepsPlugin()],
    // Sandboxed Electron preload scripts run as plain CommonJS. An ESM preload builds
    // successfully but fails at runtime before it can expose the renderer bridge.
    build: {
      sourcemap: true,
      rollupOptions: {
        output: {
          format: 'cjs',
          entryFileNames: '[name].cjs',
        },
      },
    },
  },
  renderer: {
    plugins: [react()],
    build: { sourcemap: true },
  },
});
