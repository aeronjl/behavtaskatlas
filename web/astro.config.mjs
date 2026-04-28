import { defineConfig } from "astro/config";
import svelte from "@astrojs/svelte";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  // Update if a custom domain ships; canonical/og:url meta tags follow this.
  site: "https://behavtaskatlas.vercel.app",
  integrations: [svelte()],
  vite: {
    plugins: [tailwindcss()],
  },
});
