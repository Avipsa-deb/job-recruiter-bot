import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server on 5173, which the FastAPI CORS config already allows.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, host: "localhost" },
});
