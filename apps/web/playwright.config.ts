import { defineConfig, devices } from "@playwright/test";

/**
 * E2E against the deployed app (default) or any other URL: BASE_URL=http://localhost:3000 npm run e2e
 *
 * Two projects:
 *  - harness: invariants the AI harness must hold. Must stay green.
 *  - gaps:    probes for suspected holes (guards, isolation, abuse, UX recovery). A failure here is a finding,
 *             not a regression; fix the product and move the test to `harness`.
 *
 * Always headless. LLM replies are nondeterministic, so tests assert invariants (grounding, isolation,
 * no leaks), never exact wording.
 */
const baseURL = process.env.BASE_URL ?? "https://riverside-511503.web.app";

export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  expect: { timeout: 20_000 },
  fullyParallel: true,
  workers: Number(process.env.E2E_WORKERS ?? 2), // each LLM test costs real Gemini calls: keep the burst small
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never", outputFolder: "e2e-report" }]],
  outputDir: "e2e-results",
  use: {
    baseURL,
    headless: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    // Firestore listeners keep a connection open, so "networkidle" never fires: wait on elements instead.
  },
  projects: [
    { name: "harness", testMatch: /.*\.spec\.ts/, testIgnore: /.*\.gaps\.spec\.ts/, use: { ...devices["Desktop Chrome"], headless: true } },
    { name: "gaps", testMatch: /.*\.gaps\.spec\.ts/, use: { ...devices["Desktop Chrome"], headless: true } },
  ],
});
