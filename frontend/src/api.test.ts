import { afterEach, expect, test, vi } from "vitest";
import { api } from "./api";
afterEach(() => vi.unstubAllGlobals());
test("reports safe API errors", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue({
        ok: false,
        status: 503,
        json: async () => ({
          detail: "AI provider is temporarily unavailable.",
        }),
      }),
  );
  await expect(api("/chat")).rejects.toThrow(
    "AI provider is temporarily unavailable.",
  );
});
test("sets bearer authorization without placing token in URL", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValue({ ok: true, status: 200, json: async () => [] });
  vi.stubGlobal("fetch", fetch);
  await api("/conversations", "test-token");
  expect(fetch.mock.calls[0][0]).not.toContain("test-token");
  expect(fetch.mock.calls[0][1].headers.get("Authorization")).toBe(
    "Bearer test-token",
  );
});
