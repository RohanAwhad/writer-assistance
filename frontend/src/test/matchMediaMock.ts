import { vi } from "vitest";
import {
  DESKTOP_MEDIA_QUERY,
  PHONE_MEDIA_QUERY,
  TABLET_MEDIA_QUERY,
} from "../lib/useViewport";

// INT-009 (SD-34): jsdom ships no matchMedia, so the responsive-view suite
// installs this mock at phone/tablet/desktop widths. `setWidth` re-evaluates
// every media query list the app subscribed to and dispatches "change" events
// on the lists whose match flipped — exactly the reflow the hook must observe.
// Mirrors fetchMock.ts conventions: vi.stubGlobal per test + vi.unstubAllGlobals
// in afterEach.

export type MockViewportWidth = "phone" | "tablet" | "desktop";

export const VIEWPORT_PX: Record<MockViewportWidth, number> = {
  phone: 390,
  tablet: 820,
  desktop: 1280,
};

interface ChangeHandler {
  (event: MediaQueryListEvent): void;
}

class MockMediaQueryList {
  readonly media: string;
  matches: boolean;
  private readonly listeners = new Set<ChangeHandler>();

  constructor(query: string, widthPx: number) {
    this.media = query;
    this.matches = queryMatches(query, widthPx);
  }

  addEventListener(_type: string, handler: ChangeHandler): void {
    this.listeners.add(handler);
  }

  removeEventListener(_type: string, handler: ChangeHandler): void {
    this.listeners.delete(handler);
  }

  dispatchChange(widthPx: number): void {
    const next = queryMatches(this.media, widthPx);
    if (next === this.matches) return;
    this.matches = next;
    const event = { media: this.media, matches: next } as MediaQueryListEvent;
    for (const handler of [...this.listeners]) {
      handler(event);
    }
  }
}

export function queryMatches(query: string, widthPx: number): boolean {
  if (query === PHONE_MEDIA_QUERY) return widthPx <= 767;
  if (query === TABLET_MEDIA_QUERY) return widthPx >= 768 && widthPx <= 1023;
  if (query === DESKTOP_MEDIA_QUERY) return widthPx >= 1024;
  return false;
}

export interface MatchMediaInstall {
  setWidth: (width: MockViewportWidth) => void;
}

export function installMatchMedia(width: MockViewportWidth): MatchMediaInstall {
  let widthPx = VIEWPORT_PX[width];
  const lists: MockMediaQueryList[] = [];
  vi.stubGlobal(
    "matchMedia",
    vi.fn((query: string): MediaQueryList => {
      const list = new MockMediaQueryList(query, widthPx);
      lists.push(list);
      return list as unknown as MediaQueryList;
    }),
  );
  return {
    setWidth(next: MockViewportWidth): void {
      widthPx = VIEWPORT_PX[next];
      for (const list of lists) {
        list.dispatchChange(widthPx);
      }
    },
  };
}
