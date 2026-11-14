import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const configureBackendProxy = (proxy: {
  on: (
    event: string,
    listener: (
      err: Error,
      req: unknown,
      res: {
        headersSent?: boolean;
        writeHead?: (statusCode: number, headers: Record<string, string>) => void;
        end?: (chunk: string) => void;
      }
    ) => void
  ) => void;
}) => {
  proxy.on('error', (_err, _req, res) => {
    if (
      res &&
      !res.headersSent &&
      typeof res.writeHead === 'function' &&
      typeof res.end === 'function'
    ) {
      res.writeHead(503, { 'Content-Type': 'application/json' });
      res.end(
        JSON.stringify({
          success: false,
          error_code: 'BACKEND_UNAVAILABLE',
          message:
            'Backend API server (http://127.0.0.1:8000) is not running or unreachable. Please ensure the FastAPI backend is started on port 8000.',
        })
      );
    }
  });
};

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        configure: configureBackendProxy,
      },
      '/health': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        configure: configureBackendProxy,
      },
    },
  },
  preview: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        configure: configureBackendProxy,
      },
      '/health': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        configure: configureBackendProxy,
      },
    },
  },
});
