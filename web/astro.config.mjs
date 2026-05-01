import { defineConfig } from "astro/config";
import svelte from "@astrojs/svelte";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  // Update if a custom domain ships; canonical/og:url meta tags follow this.
  site: "https://behavtaskatlas.vercel.app",
  integrations: [svelte()],
  // Stable redirects for routes that have moved. /atlas-health → /project-health
  // (the page is contributor-facing operational state, not scientist-facing,
  // so the URL signals that explicitly without forcing existing inbound
  // links to break).
  redirects: {
    "/atlas-health": "/project-health",
  },
  vite: {
    plugins: [tailwindcss()],
  },
});
