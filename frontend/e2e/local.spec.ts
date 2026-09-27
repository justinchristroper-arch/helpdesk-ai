import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test, type Page } from "@playwright/test";

async function ask(page: Page, question: string) {
  const count = await page.locator(".message.assistant").count();
  await page.getByRole("textbox", { name: "Ask an IT question" }).fill(question);
  await page.getByRole("button", { name: "Send question" }).click();
  await expect(page.locator(".message.assistant")).toHaveCount(count + 1);
  return page.locator(".message.assistant").last();
}

async function admin(page: Page) {
  const { admin: account } = JSON.parse(readFileSync(resolve(process.cwd(), "../.demo-credentials.json"), "utf8"));
  await page.goto("/");
  await page.getByRole("button", { name: "Sign in to HelpDesk AI" }).click();
  await page.getByRole("textbox", { name: "Email" }).fill(account.email);
  await page.getByLabel("Password").fill(account.password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("link", { name: "Manage documents" })).toBeVisible();
}

test("anonymous answer, evidence, feedback, follow-up and refresh history", async ({ page }) => {
  const errors: string[] = [];
  const external: string[] = [];
  page.on("pageerror", e => errors.push(e.message));
  page.on("request", r => { if (!/^https?:\/\/(localhost|127\.0\.0\.1)(:|\/)/.test(r.url())) external.push(r.url()); });
  await page.goto("/");
  const reply = await ask(page, "How do I request VPN access?");
  await expect(reply).toContainText("manager's approval");
  await reply.locator(".citations button").first().click();
  await expect(page.locator(".source-panel")).toContainText("Request VPN access");
  await page.getByRole("button", {name: "Close source"}).click();
  await reply.getByRole("button", {name: "Helpful", exact: true}).click();
  await ask(page, "What are the requirements?");
  await page.reload();
  await expect(page.locator(".message.assistant")).toHaveCount(2);
  await expect(page.locator(".message.assistant").last()).toContainText("MFA enrollment");
  await page.screenshot({path: "../screenshots/local-semantic-desktop.png", fullPage: true});
  expect(errors).toEqual([]);
  expect(external).toEqual([]);
});

test("unsupported fallback, clarification selection, and multi-source answer", async ({ page }) => {
  await page.goto("/");
  await expect(await ask(page, "What is the laptop reimbursement limit?")).toContainText("couldn't find enough information");
  const ambiguous = await ask(page, "I need access");
  await expect(ambiguous).toContainText("Choose a topic");
  await ambiguous.getByRole("button", {name: "VPN access", exact: true}).click();
  await page.getByRole("button", {name: "Send question"}).click();
  await expect(page.locator(".message.assistant")).toHaveCount(3);
  const combined = await ask(page, "My MFA is broken while I'm working remotely. What should I do?");
  await expect(combined.locator(".citations button")).toHaveCount(2);
  await expect(combined).toContainText("automatic time");
  await expect(combined).toContainText("managed laptop");
});

test("anonymous library and mobile source panel fit viewport", async ({ page }) => {
  await page.setViewportSize({width: 390, height: 844});
  await page.goto("/knowledge");
  await page.reload();
  await expect(page.locator(".document-card")).toHaveCount(8);
  await page.getByRole("button", {name: /Read source/}).first().click();
  await expect(page.locator(".document-detail")).toBeVisible();
  await page.goto("/");
  const reply = await ask(page, "My authenticator stopped working");
  await reply.locator(".citations button").first().click();
  await expect(page.locator(".source-panel")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.screenshot({path: "../screenshots/local-semantic-mobile.png", fullPage: true});
});

test("admin document upload, local reindex, removal and analytics", async ({ page }) => {
  await admin(page);
  await page.goto("/documents");
  await expect(page.locator(".document-card")).toHaveCount(8);
  await page.getByLabel("Upload document").setInputFiles({name: "browser-regression.txt", mimeType: "text/plain", buffer: Buffer.from("Synthetic browser regression document. Contact IT support for this demonstration.")});
  const card = page.locator(".document-card").filter({hasText: "browser-regression"});
  await expect(card).toBeVisible();
  await card.getByRole("button", {name: "Re-index"}).click();
  await expect(card.getByRole("button", {name: "Re-index"})).toBeEnabled();
  page.once("dialog", dialog => dialog.accept());
  await card.getByRole("button", {name: "Remove", exact: true}).click();
  await expect(page.locator(".document-card")).toHaveCount(8);
  await page.goto("/analytics");
  await page.reload();
  await expect(page.getByRole("heading", {name: "Top detected intents"})).toBeVisible();
  await expect(page.getByText("Clarifications", {exact: true})).toBeVisible();
});
