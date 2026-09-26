// @vitest-environment jsdom
import { afterEach, expect, test } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { App } from "./main";

afterEach(() => {
  cleanup();
  sessionStorage.clear();
});
test("example question populates composer and guest submission requires login", () => {
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
  expect(
    screen.getByRole("heading", { name: "Sign in to HelpDesk AI" }),
  ).toBeTruthy();
});
test("guest cannot see administrator document controls", () => {
  render(
    <MemoryRouter initialEntries={["/documents"]}>
      <App />
    </MemoryRouter>,
  );
  expect(screen.queryByLabelText("Upload document")).toBeNull();
  expect(screen.queryByRole("link", { name: "Manage documents" })).toBeNull();
});
