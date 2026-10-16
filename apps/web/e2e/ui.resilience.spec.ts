import { expect, test } from "@playwright/test";

const kioskInput = (page: import("@playwright/test").Page) => page.getByRole("textbox", { name: "Type the product you are looking for" });

test.describe("kiosk resilience (Cloud Run keeps sessions in instance memory, max-instances=3)", () => {
  test("a dead session (404 session_not_found, e.g. request hit another instance) self-heals", async ({ page }) => {
    let deadId = "";
    page.on("response", async (r) => {
      if (!deadId && r.url().endsWith("/api/kiosk/sessions") && r.request().method() === "POST") {
        deadId = (await r.json()).sessionId;
      }
    });
    await page.route("**/api/kiosk/sessions/*/messages", (route) => {
      if (deadId && route.request().url().includes(deadId)) {
        return route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ error: { code: "session_not_found", message: "session_not_found" } }) });
      }
      return route.continue();
    });
    await page.goto("/kiosk");
    await expect(kioskInput(page)).toBeEnabled({ timeout: 20_000 });
    await kioskInput(page).fill("santan kotak 65");
    await kioskInput(page).press("Enter");
    // Desired: client notices the dead session, opens a new one, and the answer arrives without user action.
    await expect(page.getByText(/Out of stock|kosong|habis/i).first(), "stuck on error with a retry that reuses the dead session").toBeVisible({ timeout: 60_000 });
  });

  test("switching store mid-chat does not leave the old store's answers on screen", async ({ page }) => {
    await page.goto("/kiosk");
    await expect(kioskInput(page)).toBeEnabled({ timeout: 20_000 });
    await kioskInput(page).fill("gula pasir 1kg");
    await kioskInput(page).press("Enter");
    await expect(kioskInput(page)).toBeEnabled({ timeout: 60_000 });
    await page.getByRole("combobox", { name: "Choose store" }).selectOption({ index: 1 });
    await expect(page.getByText("gula pasir 1kg", { exact: true }), "old store's chat still shown under the new store").toHaveCount(0);
  });

  test("a hung API call surfaces an error instead of typing forever", async ({ page }) => {
    await page.goto("/kiosk");
    await expect(kioskInput(page)).toBeEnabled({ timeout: 20_000 });
    await page.route("**/api/kiosk/sessions/*/messages", () => new Promise(() => {})); // never answers
    await kioskInput(page).fill("beras");
    await kioskInput(page).press("Enter");
    await expect(page.getByText(/Sorry, something went wrong/), "no client-side timeout: spinner never ends").toBeVisible({ timeout: 45_000 });
  });
});
