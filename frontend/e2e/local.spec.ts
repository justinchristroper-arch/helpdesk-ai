import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";

type Credentials = { email: string; password: string };

function demo(role: "admin" | "employee"): Credentials {
  const local = JSON.parse(
    readFileSync(resolve(process.cwd(), "../.demo-credentials.json"), "utf8"),
  );
  return local[role];
}

async function signIn(page: import("@playwright/test").Page, role: "admin" | "employee") {
  const account = demo(role);
  await page.goto("/");
  await page.getByRole("button", { name: "Sign in to HelpDesk AI" }).click();
  await page.getByRole("textbox", { name: "Email" }).fill(account.email);
  await page.getByLabel("Password").fill(account.password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("button", { name: "Sign in to HelpDesk AI" })).toHaveCount(0);
}

test("admin sees indexed documents, source text, analytics, and direct routes", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await signIn(page, "admin");
  await page.getByRole("link", { name: "Knowledge base" }).click();
  await expect(page.locator(".document-card")).toHaveCount(8);
  await page.getByRole("button", { name: /Read source/ }).first().click();
  await expect(page.locator(".document-detail")).toContainText("Demo / Synthetic IT Policy");
  await page.goto("/documents");
  await page.reload();
  await expect(page.getByRole("heading", { name: "Manage documents" })).toBeVisible();
  await expect(page.getByLabel("Upload document")).toBeVisible();
  await page.getByRole("link", { name: "Analytics" }).click();
  await expect(page.getByText("Actual demo usage. No estimated business impact.")).toBeVisible();
  expect(errors).toEqual([]);
});

test("employee sees approved sources, no admin tools, and safe missing-provider error", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await signIn(page, "employee");
  await expect(page.getByRole("link", { name: "Manage documents" })).toHaveCount(0);
  await page.getByRole("link", { name: "Knowledge base" }).click();
  await expect(page.locator(".document-card")).toHaveCount(8);
  await page.goto("/");
  await page.getByRole("button", { name: /How do I request VPN access/ }).click();
  await page.getByRole("button", { name: "Send question" }).click();
  await expect(page.getByRole("alert")).toContainText("AI provider is not configured");
  await expect(page.locator(".message.assistant")).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("mobile navigation and document grid fit the viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await signIn(page, "employee");
  await page.getByRole("link", { name: "Knowledge base" }).click();
  await expect(page.locator(".document-card")).toHaveCount(8);
  const width = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(width).toBeLessThanOrEqual(390);
});
