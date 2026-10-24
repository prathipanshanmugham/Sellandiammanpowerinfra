import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// Same-origin API: Caddy serves /api and the site together. In development the API runs on :8001.
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8001" } },
  build: {
    sourcemap: false,
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          if (id.includes("node_modules/react-dom") || id.includes("node_modules/react/") || id.includes("node_modules/scheduler")) return "react";
          if (id.includes("node_modules/@radix-ui") || id.includes("node_modules/cmdk")) return "ui";
          return undefined;
        },
      },
    },
  },
});
