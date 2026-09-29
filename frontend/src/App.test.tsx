// @vitest-environment jsdom
import { afterEach, expect, test, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { App } from "./main";

afterEach(() => {
  cleanup();
  sessionStorage.clear();
  vi.unstubAllGlobals();
});
test("guest asks immediately and sees authoritative answer without login", async () => {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => ({ok: true, status: 200, json: async () =>
    url.endsWith("/auth/guest") ? {token: "guest", email: "guest@demo.invalid", role: "guest"} :
    url.endsWith("/chat") ? {conversation_id: "c1", message: {id: "m1", role: "assistant", content: "Submit an Access Request ticket. [1]", sources: [{id: "s1", title: "VPN policy", excerpt: "Submit an Access Request ticket.", relevance_score: .9, citation_number: 1}], outcome: "answered"}} : []
  })));
  render(
    <MemoryRouter>
      <App />
    </MemoryRouter>,
  );
  fireEvent.click(
    screen.getByRole("button", { name: /How do I request VPN access/ }),
  );
  expect(
    (
      screen.getByRole("textbox", {
        name: "Ask an IT question",
      }) as HTMLTextAreaElement
    ).value,
  ).toBe("How do I request VPN access?");
  fireEvent.click(screen.getByRole("button", { name: "Send question" }));
  await waitFor(() => expect(screen.getByText("Submit an Access Request ticket. [1]")).toBeTruthy());
  expect(screen.queryByRole("heading", {name: "Sign in to HelpDesk AI"})).toBeNull();
});
test("guest cannot see administrator document controls", () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({ok: true, status: 200, json: async () => []})));
  render(
    <MemoryRouter initialEntries={["/documents"]}>
      <App />
    </MemoryRouter>,
  );
  expect(screen.queryByLabelText("Upload document")).toBeNull();
  expect(screen.queryByRole("link", { name: "Manage documents" })).toBeNull();
});

test("saved feedback is visible when a conversation reloads", async () => {
  sessionStorage.setItem("helpdesk-session", JSON.stringify({token: "guest", email: "guest@demo.invalid", role: "guest"}));
  sessionStorage.setItem("helpdesk-conversation:guest@demo.invalid", "c1");
  vi.stubGlobal("fetch", vi.fn(async (url: string) => ({ok: true, status: 200, json: async () =>
    url.endsWith("/conversations/c1") ? [
      {id: "u1", role: "user", content: "VPN access?", sources: []},
      {id: "m1", role: "assistant", content: "Ask IT. [1]", sources: [], feedback_rating: 1},
    ] : [{id: "c1", title: "VPN access?"}]
  })));
  render(<MemoryRouter><App /></MemoryRouter>);
  expect(await screen.findByText("Ask IT. [1]")).toBeTruthy();
  expect(screen.getByRole("button", {name: "Helpful"}).getAttribute("aria-pressed")).toBe("true");
});

test("quota uses a source answer and explains rewriting is limited", async () => {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => ({ok: true, status: 200, json: async () =>
    url.endsWith("/auth/guest") ? {token: "guest", email: "guest@demo.invalid", role: "guest"} :
    url.endsWith("/chat") ? {conversation_id: "c1", message: {id: "m1", role: "assistant", content: "Contact IT. [1]", sources: [], outcome: "answered", synthesis_status: "limited"}} : []
  })));
  render(<MemoryRouter><App /></MemoryRouter>);
  fireEvent.change(screen.getByLabelText("Ask an IT question"), {target: {value: "MFA remote work"}});
  fireEvent.click(screen.getByLabelText("Send question"));
  await screen.findByText(/Optional answer rewriting is limited today/);
  expect(screen.getByText("Contact IT. [1]")).toBeTruthy();
});

test("network failure explains cold start without automatic retries", async () => {
  const fetch = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
  vi.stubGlobal("fetch", fetch);
  render(<MemoryRouter><App /></MemoryRouter>);
  fireEvent.change(screen.getByLabelText("Ask an IT question"), {target: {value: "VPN request"}});
  fireEvent.click(screen.getByLabelText("Send question"));
  await screen.findByRole("alert");
  expect(screen.getByRole("alert").textContent).toContain("has not been retried automatically");
  expect(fetch).toHaveBeenCalledTimes(1);
});
