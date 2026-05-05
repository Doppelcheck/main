/**
 * Chrome MV3 offscreen document. Hosts MLC web-llm because MV3
 * service workers can't use WebGPU (or DOM, or `navigator.gpu`).
 *
 * The background SW creates exactly one of these on demand and keeps
 * a long-lived port to it (`RUNNER_PORT`). On Firefox MV2 this file
 * is unused — `entrypoints/background.ts` installs the same handler
 * directly (its background page already has `navigator.gpu`).
 */

import { installEngineHostHandler } from "@/lib/llm/web-llm/host";

installEngineHostHandler();
