import { defineConfig } from "wxt";
import react from "@vitejs/plugin-react";

export default defineConfig({
  modules: [],
  srcDir: ".",
  outDir: ".output",
  manifest: ({ browser }) => ({
    name: "DoppelCheck",
    description:
      "Extracts claims from the page, finds independent sources, surfaces contradictions.",
    version: "1.0.0",
    permissions: [
      "storage",
      "activeTab",
      "scripting",
      // sidePanel is Chromium-only; Firefox uses sidebar_action declared below.
      ...(browser === "firefox" ? [] : ["sidePanel"]),
    ],
    host_permissions: ["<all_urls>"],
    action: {
      default_title: "DoppelCheck",
      default_icon: {
        "16": "icon/16.png",
        "48": "icon/48.png",
        "128": "icon/128.png",
      },
    },
    icons: {
      "16": "icon/16.png",
      "48": "icon/48.png",
      "128": "icon/128.png",
    },
    ...(browser === "firefox"
      ? {
          sidebar_action: {
            default_title: "DoppelCheck",
            default_panel: "sidepanel.html",
            default_icon: "icon/48.png",
          },
          browser_specific_settings: {
            gecko: { id: "doppelcheck@doppelcheck.dev", strict_min_version: "128.0" },
          },
        }
      : {
          side_panel: { default_path: "sidepanel.html" },
        }),
    options_ui: { page: "options.html", open_in_tab: true },
  }),
  vite: () => ({
    plugins: [react()],
  }),
});
