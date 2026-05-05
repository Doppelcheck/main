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
      // offscreen is also Chromium-only; we use it to host MLC web-llm
      // (the SW can't access WebGPU / `navigator.gpu`). Firefox MV2
      // background pages already have full page-context access.
      ...(browser === "firefox" ? [] : ["offscreen"]),
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
    // WebAssembly compilation in MV3 extension pages requires explicit
    // `wasm-unsafe-eval`. Used by the local-bundle tier — MLC web-llm's
    // tokenizer and the engine's compiled libraries instantiate WASM
    // modules in the offscreen document. Firefox MV2 ignores this and
    // allows WASM by default.
    ...(browser === "firefox"
      ? {}
      : {
          content_security_policy: {
            extension_pages:
              "script-src 'self' 'wasm-unsafe-eval'; object-src 'self';",
          },
        }),
  }),
  vite: () => ({
    plugins: [react()],
  }),
});
