import { expect, test, type Page } from "@playwright/test";
import { HERO_SKU } from "./helpers";

const ROUTES = ["/", "/demo", "/kiosk", "/manager", "/manager/gaps", `/manager/sku?code=${HERO_SKU}`, "/about"];

/** Collect errors a user would never see but a harness must: console errors, uncaught exceptions, 4xx/5xx. */
function watch(page: Page) {
  const problems: string[] = [];
  page.on("console", (m) => m.type() === "error" && problems.push(`console: ${m.text().slice(0, 200)}`));
  page.on("pageerror", (e) => problems.push(`pageerror: ${e.message.slice(0, 200)}`));
  page.on("response", (r) => {
    if (r.status() >= 400 && !r.url().includes("firestore.googleapis.com")) problems.push(`HTTP ${r.status()} ${r.url()}`);
  });
  return problems;
}

const kioskInput = (page: Page) => page.getByRole("textbox", { name: "Type the product you are looking for" });
const sendButton = (page: Page) => page.getByRole("button", { name: "Send", exact: true });

test.describe("every route renders cleanly", () => {
  for (const route of ROUTES) {
    test(`${route}: no console errors, has h1, title set, loads < 5s`, async ({ page }) => {
      const problems = watch(page);
      const t0 = Date.now();
      await page.goto(route, { waitUntil: "domcontentloaded" });
      await expect(page.locator("h1").first()).toBeVisible();
      expect(Date.now() - t0).toBeLessThan(5000);
      await expect(page).toHaveTitle(/.{3,}/);
      await page.waitForTimeout(1500); // let data hooks / Firestore listeners settle
      expect(problems).toEqual([]);
    });
  }

  test("no horizontal scroll on a phone viewport", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    for (const route of ROUTES) {
      await page.goto(route, { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(800);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(overflow, `${route} overflows by ${overflow}px`).toBeLessThanOrEqual(1);
    }
  });
});

test.describe("kiosk (shopper agent) through the UI", () => {
  test("quick tag -> assistant answer with a stockout card and a way out", async ({ page }) => {
    await page.goto("/kiosk");
    const tag = page.getByRole("button", { name: "Santan Kotak 65ml" });
    await expect(tag).toBeEnabled({ timeout: 20_000 });
    await tag.click();
    await expect(page.getByText("Santan Kotak 65ml").first()).toBeVisible();
    // the typing indicator goes away and the input is usable again
    await expect(kioskInput(page)).toBeEnabled({ timeout: 60_000 });
    await expect(page.getByText("Out of stock").first()).toBeVisible();
    await expect(page.getByText("Alternatives in this store, ready to pick up")).toBeVisible();
    await expect(page.getByText(/Nearest branch with stock/)).toBeVisible();
  });

  test("input is locked while the agent is typing: no double send", async ({ page }) => {
    await page.goto("/kiosk");
    await expect(kioskInput(page)).toBeEnabled({ timeout: 20_000 });
    await kioskInput(page).fill("minyak goreng 2L");
    await kioskInput(page).press("Enter");
    await expect(kioskInput(page)).toBeDisabled();
    await expect(sendButton(page)).toBeDisabled();
    await expect(kioskInput(page)).toBeEnabled({ timeout: 60_000 });
    await expect(page.getByText("minyak goreng 2L", { exact: true })).toHaveCount(1);
  });

  test("HTML in shopper text is rendered as text, never executed", async ({ page }) => {
    await page.goto("/kiosk");
    await expect(kioskInput(page)).toBeEnabled({ timeout: 20_000 });
    const payload = `<img src=x onerror="window.__xss=1"><b>bold</b>`;
    await kioskInput(page).fill(payload);
    await kioskInput(page).press("Enter");
    await expect(page.getByText(payload, { exact: true })).toBeVisible();
    await expect(kioskInput(page)).toBeEnabled({ timeout: 60_000 });
    expect(await page.evaluate(() => (window as unknown as { __xss?: number }).__xss)).toBeUndefined();
    expect(await page.locator("main img[src='x']").count()).toBe(0);
  });

  test('"Mulai baru" clears the conversation and starts a fresh session', async ({ page }) => {
    await page.goto("/kiosk");
    await expect(kioskInput(page)).toBeEnabled({ timeout: 20_000 });
    await kioskInput(page).fill("gula pasir 1kg");
    await kioskInput(page).press("Enter");
    await expect(kioskInput(page)).toBeEnabled({ timeout: 60_000 });
    await page.getByRole("button", { name: "New chat" }).click();
    await expect(page.getByText("gula pasir 1kg", { exact: true })).toHaveCount(0);
    await expect(page.getByText(/Mau cari barang apa hari ini/)).toBeVisible();
    await expect(kioskInput(page)).toBeEnabled({ timeout: 20_000 });
  });

  test("API failure shows a friendly error with a working retry", async ({ page }) => {
    await page.goto("/kiosk");
    await expect(kioskInput(page)).toBeEnabled({ timeout: 20_000 });
    let failed = false;
    await page.route("**/api/kiosk/sessions/*/messages", (route) => {
      if (!failed) {
        failed = true;
        return route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ error: { code: "x", message: "down" } }) });
      }
      return route.continue();
    });
    await kioskInput(page).fill("telur ayam negeri");
    await kioskInput(page).press("Enter");
    await expect(page.getByText(/Sorry, something went wrong/)).toBeVisible();
    await page.getByRole("button", { name: "Try again" }).click();
    await expect(page.getByText(/Sorry, something went wrong/)).toHaveCount(0, { timeout: 60_000 });
    await expect(page.getByText("telur ayam negeri", { exact: true })).toHaveCount(1); // not duplicated by retry
  });

});

test.describe("manager dashboard", () => {
  test("hero decision is on top and drills into SKU detail", async ({ page }) => {
    const problems = watch(page);
    await page.goto("/manager");
    await expect(page.getByRole("heading", { name: /Santan Kotak Kara 65 ml: order \d+, not \d+/ })).toBeVisible({ timeout: 30_000 });
    await page.getByRole("link", { name: /See why/ }).click();
    await expect(page).toHaveURL(/\/manager\/sku\/?\?code=SKU-0001/);
    await expect(page.getByRole("img", { name: /Daily sales of Santan Kotak Kara 65 ml/ })).toBeVisible({ timeout: 30_000 });
    expect(problems).toEqual([]);
  });

  test("dashboard number agrees with the API's recommended quantities", async ({ page, request }) => {
    const recs = await (await request.get("/api/manager/S01/recommendations", { headers: { "X-Sandbox-Id": crypto.randomUUID() } })).json();
    const hero = recs.items.find((i: { sku: string }) => i.sku === HERO_SKU);
    await page.goto("/manager");
    await expect(page.getByRole("heading", { name: new RegExp(`order ${hero.recommendedQtyB}, not ${hero.recommendedQtyA}`) })).toBeVisible({ timeout: 30_000 });
  });

  test("evidence drawer labels shopper quotes as simulated", async ({ page }) => {
    await page.goto(`/manager/sku?code=${HERO_SKU}`);
    await page.getByRole("button", { name: "See all conversations" }).click();
    await expect(page.getByText(/Simulated conversations/i)).toBeVisible({ timeout: 30_000 });
  });

  test("unknown SKU code degrades to an error state, not a crash", async ({ page }) => {
    const problems = watch(page);
    await page.goto("/manager/sku?code=DOES-NOT-EXIST");
    await expect(page.getByText("Could not load this product")).toBeVisible({ timeout: 30_000 });
    expect(problems.filter((p) => p.startsWith("pageerror"))).toEqual([]);
  });

  test("'Ask why' agent: sample question -> cited answer, no raw [E#] markers", async ({ page }) => {
    await page.goto(`/manager/sku?code=${HERO_SKU}`);
    await page.getByRole("button", { name: "Ask why" }).click();
    const sample = page.getByRole("button", { name: /“.+”/ }).first();
    await expect(sample).toBeVisible();
    await sample.click();
    await expect(page.getByText("Menganalisis…")).toBeVisible();
    await expect(page.getByText("Menganalisis…")).toHaveCount(0, { timeout: 90_000 });
    const answer = await page.locator("p.leading-relaxed").last().innerText();
    expect(answer.length).toBeGreaterThan(20);
    expect(answer).not.toMatch(/\[E\d+\]/);
  });

  test("store selector switches the whole dashboard", async ({ page }) => {
    await page.goto("/manager");
    await expect(page.getByRole("heading", { level: 1, name: "Radar Mart Cipete" })).toBeVisible({ timeout: 30_000 });
    await page.getByRole("combobox", { name: "Choose store" }).selectOption({ label: "Radar Mart BSD" });
    await expect(page.getByRole("heading", { level: 1, name: "Radar Mart BSD" })).toBeVisible();
  });
});

test.describe("assortment gaps", () => {
  test("lists what shoppers asked for but the store does not carry (oat milk)", async ({ page }) => {
    await page.goto("/manager/gaps");
    await expect(page.getByText("Oat Milk").first()).toBeVisible({ timeout: 30_000 });
  });

  test("category chip and text filter narrow the list", async ({ page }) => {
    await page.goto("/manager/gaps");
    const items = page.getByRole("listitem").filter({ hasText: /“/ });
    await expect(items.first()).toBeVisible({ timeout: 30_000 });
    const all = await items.count();
    await page.getByRole("button", { name: "Beverages" }).click();
    await expect.poll(async () => items.count()).toBeLessThan(all);
    await page.getByRole("button", { name: "All", exact: true }).click();
    await page.getByRole("textbox", { name: "Filter gaps" }).fill("kimchi");
    await expect.poll(async () => items.count()).toBe(1);
  });
});

test.describe("about / judge page", () => {
  test("names the Google services it claims to use", async ({ page }) => {
    await page.goto("/about");
    for (const term of ["Firebase", "Firestore", "Cloud Run", "Gemini"]) {
      await expect(page.getByText(term).first(), term).toBeVisible();
    }
  });

  test("home page states that all data is simulated", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText(/simulated/i).first()).toBeVisible();
  });
});
