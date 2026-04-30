import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  // Load env for the current mode (development / production)
  const env = loadEnv(mode, process.cwd(), '');

  // In dev: proxy /api → local backend (or Render if VITE_API_URL is set in .env)
  const backendTarget = env.VITE_API_URL || 'http://localhost:8000';

  return {
    plugins: [react()],
    server: {
      port: 3000,
      proxy: {
        '/api': {
          target: backendTarget,
          changeOrigin: true,
          secure: backendTarget.startsWith('https'),
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: false,
    },
  };
});
