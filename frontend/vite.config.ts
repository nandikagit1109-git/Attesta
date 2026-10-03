import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies /api to the FastAPI backend so the SPA can use relative
// URLs in development; VITE_API_BASE overrides for other setups.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        // The three heavyweight libraries ship as their own cacheable chunks.
        manualChunks: {
          ethers: ["ethers"],
          flow: ["@xyflow/react"],
          charts: ["recharts"],
        },
      },
    },
  },
});
