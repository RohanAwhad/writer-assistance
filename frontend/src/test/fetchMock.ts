import { vi } from "vitest";

export interface FetchCall {
  url: string;
  method: string;
  body: unknown;
}

export interface StubResponse {
  status?: number;
  json?: unknown;
  text?: string;
}

type Handler = (call: FetchCall, index: number) => StubResponse;

export function stubFetch(handler: Handler): { calls: FetchCall[] } {
  const calls: FetchCall[] = [];
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    const method = init?.method ?? "GET";
    let body: unknown = null;
    if (typeof init?.body === "string" && init.body.length > 0) {
      try {
        body = JSON.parse(init.body);
      } catch {
        body = init.body;
      }
    }
    const call: FetchCall = { url, method, body };
    calls.push(call);
    const response = handler(call, calls.length - 1);
    const status = response.status ?? 200;
    if (response.text !== undefined) {
      return new Response(response.text, {
        status,
        headers: { "Content-Type": "text/markdown" },
      });
    }
    if (status === 204) {
      return new Response(null, { status });
    }
    const jsonBody = response.json !== undefined ? JSON.stringify(response.json) : "{}";
    return new Response(jsonBody, {
      status,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fn as unknown as typeof fetch);
  return { calls };
}

export function ok<T>(json: T): StubResponse {
  return { status: 200, json };
}

export function created<T>(json: T): StubResponse {
  return { status: 201, json };
}

export function noContent(): StubResponse {
  return { status: 204, json: null };
}

export function error(status: number, detail: string): StubResponse {
  return { status, json: { detail } };
}

export function lastJson<T>(calls: FetchCall[]): T {
  const last = calls[calls.length - 1];
  if (last === undefined) throw new Error("no fetch call recorded");
  return last.body as T;
}
