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
