import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  // In Docker (Stage 6B) this will be http://backend:8000
  const target = env.API_PROXY_TARGET || "http://localhost:8000";

  return {
    plugins: [react()],
    server: {
      host: true,
      port: 5173,
      proxy: { "/api": { target, changeOrigin: true } },
    },
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["./src/test/setup.ts"],
      css: false,
    },
  };
});
