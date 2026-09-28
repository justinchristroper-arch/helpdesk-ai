import { defineConfig } from "vitest/config";
import { loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");
  if (command === "build" && mode === "production") {
    const value = process.env.VITE_API_URL || env.VITE_API_URL || "/api";
    const url = value === "/api" ? null : new URL(value);
    if (url && (url.protocol !== "https:" || ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname)
      || url.username || url.password || url.pathname !== "/" || url.search || url.hash)) {
      throw new Error("Production VITE_API_URL must be /api or an HTTPS backend origin.");
    }
  }
  return {
  plugins: [react(), tailwindcss()],
  test: { exclude: ["e2e/**", "node_modules/**"] },
  };
});
