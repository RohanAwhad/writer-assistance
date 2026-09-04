import { useEffect, useState } from "react";

// INT-009 width classes (SD-31): phone 320-767, tablet 768-1023, desktop >= 1024
// CSS px, decided by viewport width alone. The query strings are exported so the
// vitest matchMedia mock (src/test/matchMediaMock.ts) evaluates the same tiers.
export const PHONE_MEDIA_QUERY = "(max-width: 767px)";
export const TABLET_MEDIA_QUERY = "(min-width: 768px) and (max-width: 1023px)";
export const DESKTOP_MEDIA_QUERY = "(min-width: 1024px)";

export type DeviceClass = "phone" | "tablet" | "desktop";

/**
 * matchMedia-driven media-query hook (SD-34). jsdom-safe: a missing
 * `window.matchMedia` (jsdom default) yields `false` so callers fall back to
 * their desktop/wide arrangement; subscriptions use the modern
 * addEventListener("change") API with effect-driven cleanup.
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState<boolean>(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false;
    return window.matchMedia(query).matches;
  });

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    const mql = window.matchMedia(query);
    setMatches(mql.matches);
    const onChange = (event: MediaQueryListEvent): void => {
      setMatches(event.matches);
    };
    mql.addEventListener("change", onChange);
    return () => {
      mql.removeEventListener("change", onChange);
    };
  }, [query]);

  return matches;
}

/**
 * Resolves the SD-31 device class from viewport width alone (no UA sniffing).
 * When `matchMedia` is absent the desktop class is returned, keeping the
 * existing wide layout the default.
 */
export function useDeviceClass(): DeviceClass {
  const phone = useMediaQuery(PHONE_MEDIA_QUERY);
  const tablet = useMediaQuery(TABLET_MEDIA_QUERY);
  const desktop = useMediaQuery(DESKTOP_MEDIA_QUERY);
  if (phone) return "phone";
  if (tablet) return "tablet";
  if (desktop) return "desktop";
  return "desktop";
}
