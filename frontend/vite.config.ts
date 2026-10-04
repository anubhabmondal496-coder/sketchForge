import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/analyze': 'http://localhost:8000',
      '/generate': 'http://localhost:8000',
      '/generate-from-photo': 'http://localhost:8000',
      '/job': 'http://localhost:8000',
      '/model': 'http://localhost:8000',
      '/models': 'http://localhost:8000',
      '/refine': 'http://localhost:8000',
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    chunkSizeWarningLimit: 1200,
  },
});
