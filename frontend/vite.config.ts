import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // In dev the browser talks to Vite, which forwards /api to Django (no CORS needed).
    proxy: { "/api": "http://localhost:8000" },
  },
  build: {
    // MapLibre is most of the bundle; its own chunk caches well and keeps app code small.
    rollupOptions: { output: { manualChunks: { maplibre: ["maplibre-gl"] } } },
    chunkSizeWarningLimit: 1100,
  },
  test: { environment: "node" },
});
