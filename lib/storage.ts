import {
  DEFAULT_SETTINGS,
  Settings,
  SettingsSchema,
  migrateSettings,
} from "@/types";
import { browserApi } from "@/lib/browser-api";

const KEY = "settings";

export async function getSettings(): Promise<Settings> {
  const raw = (await browserApi.storage.sync.get(KEY)) ?? {};
  const migrated = migrateSettings(raw[KEY]);
  const parsed = SettingsSchema.safeParse(migrated);
  if (!parsed.success) return DEFAULT_SETTINGS;
  // Persist the migrated shape so future reads skip the migration step
  // and the storage doesn't keep stale flat fields forever.
  if (
    raw[KEY] &&
    typeof raw[KEY] === "object" &&
    (raw[KEY] as Record<string, unknown>).tier === undefined
  ) {
    browserApi.storage.sync.set({ [KEY]: parsed.data }).catch(() => undefined);
  }
  return parsed.data;
}

export async function setSettings(patch: Partial<Settings>): Promise<Settings> {
  const current = await getSettings();
  const next = SettingsSchema.parse({ ...current, ...patch });
  await browserApi.storage.sync.set({ [KEY]: next });
  return next;
}

export function watchSettings(cb: (s: Settings) => void): () => void {
  const listener = (
    changes: Record<string, chrome.storage.StorageChange>,
    area: chrome.storage.AreaName,
  ) => {
    if (area !== "sync" || !(KEY in changes)) return;
    const parsed = SettingsSchema.safeParse(
      migrateSettings(changes[KEY]?.newValue),
    );
    if (parsed.success) cb(parsed.data);
  };
  browserApi.storage.onChanged.addListener(listener);
  return () => browserApi.storage.onChanged.removeListener(listener);
}
