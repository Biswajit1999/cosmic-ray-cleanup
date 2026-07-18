import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    // The procedural detector is lazy-loaded; its isolated graphics chunk is intentionally
    // larger than the immediately loaded application shell.
    chunkSizeWarningLimit: 900,
  },
});
