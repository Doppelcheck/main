import { describe, expect, it } from "vitest";
import { DEFAULT_SETTINGS, SettingsSchema, migrateSettings } from "@/types";

/**
 * Every blob here is a shape that really shipped. The point of the suite is
 * that a user upgrading from any of them lands on settings the schema accepts
 * — a migration that produces an invalid blob silently resets the user to
 * defaults in getSettings(), losing their API keys.
 */
const parsed = (raw: unknown) => SettingsSchema.parse(migrateSettings(raw));

describe("migrateSettings — original flat shape", () => {
  it("maps llmTier chrome-builtin to the browser-native tier", () => {
    expect(parsed({ llmTier: "chrome-builtin" }).tier).toBe("browser-native");
  });

  it("maps llmTier anthropic to network + anthropic, keeping the key", () => {
    const s = parsed({ llmTier: "anthropic", anthropicApiKey: "sk-ant-xyz" });
    expect(s.tier).toBe("network");
    expect(s.networkProvider).toBe("anthropic");
    expect(s.anthropic.apiKey).toBe("sk-ant-xyz");
  });

  it("maps llmTier ollama to network + ollama, keeping baseUrl and model", () => {
    const s = parsed({
      llmTier: "ollama",
      ollamaBaseUrl: "http://box:11434",
      ollamaModel: "gemma3:4b",
    });
    expect(s.networkProvider).toBe("ollama");
    expect(s.ollama.baseUrl).toBe("http://box:11434");
    expect(s.ollama.model).toBe("gemma3:4b");
  });

  it("moves the retired in-browser tier to network + anthropic", () => {
    const s = parsed({ llmTier: "local" });
    expect(s.tier).toBe("network");
    expect(s.networkProvider).toBe("anthropic");
  });

  it("drops the superseded flat fields", () => {
    const out = migrateSettings({
      llmTier: "anthropic",
      anthropicApiKey: "k",
      anthropicModel: "m",
      ollamaBaseUrl: "u",
      ollamaModel: "o",
    }) as Record<string, unknown>;
    for (const dead of [
      "llmTier",
      "anthropicApiKey",
      "anthropicModel",
      "ollamaBaseUrl",
      "ollamaModel",
    ]) {
      expect(out).not.toHaveProperty(dead);
    }
  });

  it("falls back to defaults for an unknown llmTier", () => {
    const s = parsed({ llmTier: "something-we-never-shipped" });
    expect(s.tier).toBe("browser-native");
    expect(s.networkProvider).toBe("anthropic");
  });
});

describe("migrateSettings — three-tier shape", () => {
  it("moves a local-bundle user to the network tier", () => {
    const s = parsed({ tier: "local-bundle", localBundleModel: "Llama-3-8B" });
    expect(s.tier).toBe("network");
    expect(s.networkProvider).toBe("anthropic");
  });

  it("keeps an explicit networkProvider when rescuing a local-bundle user", () => {
    const s = parsed({ tier: "local-bundle", networkProvider: "openai" });
    expect(s.networkProvider).toBe("openai");
  });

  it("drops the retired local-bundle fields", () => {
    const out = migrateSettings({
      tier: "network",
      localBundleModel: "x",
      localBundleDevice: "webgpu",
    }) as Record<string, unknown>;
    expect(out).not.toHaveProperty("localBundleModel");
    expect(out).not.toHaveProperty("localBundleDevice");
  });

  it("leaves an already-current blob's tier alone", () => {
    expect(parsed({ tier: "network", networkProvider: "google" }).tier).toBe(
      "network",
    );
  });
});

describe("migrateSettings — contract", () => {
  it("does not mutate the caller's object", () => {
    // getSettings() reads raw[KEY].tier AFTER calling migrateSettings on it to
    // decide whether to persist the migrated shape. If the migration mutates
    // its input, that check reads the post-migration value and the write-back
    // never happens — the user is re-migrated on every single read.
    const raw = { tier: "local-bundle", localBundleModel: "Llama-3-8B" };
    migrateSettings(raw);
    expect(raw).toEqual({ tier: "local-bundle", localBundleModel: "Llama-3-8B" });
  });

  it("passes through a null or non-object blob untouched", () => {
    expect(migrateSettings(null)).toBeNull();
    expect(migrateSettings(undefined)).toBeUndefined();
    expect(migrateSettings("nonsense")).toBe("nonsense");
  });

  it("produces a schema-valid blob from an empty object", () => {
    expect(parsed({})).toEqual(DEFAULT_SETTINGS);
  });
});
