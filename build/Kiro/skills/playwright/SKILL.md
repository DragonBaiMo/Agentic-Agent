---
name: playwright
description: "Playwright browser automation: test authoring, page interaction, locator strategy, network interception, screenshot testing, Page Object Model, CI headless config. Use when writing or debugging Playwright tests, browser automation scripts, or configuring Playwright in a project."
argument-hint: "[TARGET]: URL or feature to test  [TASK]: write tests | debug selector | mock network | screenshot | configure CI"
---

# Playwright Browser Automation

## Setup

```bash
# Install
npm init playwright@latest

# Run all tests
npx playwright test

# Run specific file
npx playwright test tests/login.spec.ts

# Run with UI mode (headed, interactive)
npx playwright test --ui

# Run headed (see browser)
npx playwright test --headed

# Debug single test
npx playwright test --debug tests/login.spec.ts

# Show report
npx playwright show-report
```

Windows: use `npx playwright test` — no `./node_modules/.bin` prefix needed.

---

## Test structure

```ts
import { test, expect } from "@playwright/test"

test.describe("Login flow", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login")
  })

  test("valid credentials redirect to dashboard", async ({ page }) => {
    await page.getByLabel("Email").fill("user@example.com")
    await page.getByLabel("Password").fill("secret")
    await page.getByRole("button", { name: "Sign in" }).click()
    await expect(page).toHaveURL("/dashboard")
  })

  test("invalid credentials show error", async ({ page }) => {
    await page.getByLabel("Email").fill("bad@example.com")
    await page.getByLabel("Password").fill("wrong")
    await page.getByRole("button", { name: "Sign in" }).click()
    await expect(page.getByRole("alert")).toContainText("Invalid credentials")
  })
})
```

---

## Selector priority (use in this order)

1. **Role** — most resilient to markup changes
   ```ts
   page.getByRole("button", { name: "Submit" })
   page.getByRole("textbox", { name: "Email" })
   page.getByRole("combobox", { name: "Country" })
   page.getByRole("checkbox", { name: "Remember me" })
   ```

2. **Label / accessible name**
   ```ts
   page.getByLabel("Password")
   page.getByPlaceholder("Search...")
   ```

3. **Text content**
   ```ts
   page.getByText("Welcome back")
   page.getByText(/error/i)           // regex
   ```

4. **Test ID** (add `data-testid` to DOM when role/text is ambiguous)
   ```ts
   page.getByTestId("submit-btn")     // reads data-testid attribute
   ```

5. **CSS / XPath** — last resort, breaks on structure changes
   ```ts
   page.locator(".modal .close-btn")
   page.locator("xpath=//button[@type='submit']")
   ```

---

## Locator operations

```ts
const btn = page.getByRole("button", { name: "Buy" })

// Assertion (auto-waits up to timeout)
await expect(btn).toBeVisible()
await expect(btn).toBeEnabled()
await expect(btn).toBeDisabled()
await expect(btn).toHaveText("Buy now")
await expect(btn).toHaveAttribute("aria-pressed", "true")
await expect(btn).toHaveCount(3)      // multiple matches

// Action
await btn.click()
await btn.dblclick()
await btn.hover()

// Forms
await page.getByLabel("Email").fill("user@example.com")
await page.getByRole("combobox").selectOption("value")
await page.getByRole("checkbox").check()
await page.getByRole("checkbox").uncheck()

// Chaining locators
const row = page.getByRole("row", { name: "Alice" })
await row.getByRole("button", { name: "Edit" }).click()

// Filter
const items = page.getByRole("listitem")
await items.filter({ hasText: "Active" }).count()
```

---

## Navigation & waiting

```ts
// Navigate
await page.goto("https://example.com")
await page.goto("/relative", { waitUntil: "networkidle" })
await page.goBack()
await page.goForward()
await page.reload()

// Wait for specific state
await page.waitForURL("**/dashboard")
await page.waitForSelector(".spinner", { state: "hidden" })
await page.waitForLoadState("networkidle")
await page.waitForTimeout(500)       // avoid in tests — use assertions instead

// Frames
const frame = page.frameLocator("#embed-frame")
await frame.getByRole("button", { name: "Play" }).click()
```

---

## Network interception

```ts
// Mock API response
await page.route("**/api/users", async (route) => {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify([{ id: 1, name: "Alice" }]),
  })
})

// Abort specific requests (e.g., analytics)
await page.route("**/analytics/**", (route) => route.abort())

// Modify request headers
await page.route("**/api/**", async (route) => {
  const headers = { ...route.request().headers(), "x-test": "true" }
  await route.continue({ headers })
})

// Capture request/response
page.on("request", (req) => console.log(req.url()))
page.on("response", (res) => console.log(res.status(), res.url()))

// Wait for specific request
const [response] = await Promise.all([
  page.waitForResponse("**/api/submit"),
  page.getByRole("button", { name: "Save" }).click(),
])
expect(response.status()).toBe(200)
```

---

## Screenshots & visual testing

```ts
// Full page screenshot
await page.screenshot({ path: "screenshots/home.png", fullPage: true })

// Element screenshot
await page.getByRole("dialog").screenshot({ path: "dialog.png" })

// Visual comparison (snapshot testing)
await expect(page).toHaveScreenshot("homepage.png")
await expect(page.getByRole("dialog")).toHaveScreenshot("modal.png")

// Update snapshots
// npx playwright test --update-snapshots
```

Snapshots stored in `__snapshots__/` next to the test file. Commit them to VCS.

---

## Page Object Model

```ts
// pages/login-page.ts
import { type Page, type Locator } from "@playwright/test"

export class LoginPage {
  readonly emailInput: Locator
  readonly passwordInput: Locator
  readonly submitBtn: Locator
  readonly errorAlert: Locator

  constructor(private page: Page) {
    this.emailInput = page.getByLabel("Email")
    this.passwordInput = page.getByLabel("Password")
    this.submitBtn = page.getByRole("button", { name: "Sign in" })
    this.errorAlert = page.getByRole("alert")
  }

  async goto() {
    await this.page.goto("/login")
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email)
    await this.passwordInput.fill(password)
    await this.submitBtn.click()
  }
}

// tests/login.spec.ts
import { test, expect } from "@playwright/test"
import { LoginPage } from "../pages/login-page"

test("login redirects to dashboard", async ({ page }) => {
  const loginPage = new LoginPage(page)
  await loginPage.goto()
  await loginPage.login("user@example.com", "secret")
  await expect(page).toHaveURL("/dashboard")
})
```

---

## Fixtures (shared state, auth)

```ts
// fixtures.ts
import { test as base } from "@playwright/test"
import { LoginPage } from "./pages/login-page"

type Fixtures = { loginPage: LoginPage; authenticatedPage: void }

export const test = base.extend<Fixtures>({
  loginPage: async ({ page }, use) => {
    await use(new LoginPage(page))
  },
  // Reuse signed-in state across tests
  authenticatedPage: [
    async ({ page }, use) => {
      await page.goto("/login")
      await page.getByLabel("Email").fill("user@example.com")
      await page.getByLabel("Password").fill("secret")
      await page.getByRole("button", { name: "Sign in" }).click()
      await page.waitForURL("/dashboard")
      await use()
    },
    { scope: "test" },
  ],
})

export { expect } from "@playwright/test"
```

Save authenticated state to file (avoids re-login per test):

```ts
// playwright.config.ts
export default defineConfig({
  globalSetup: "./global-setup.ts",
})

// global-setup.ts
import { chromium } from "@playwright/test"

export default async function globalSetup() {
  const browser = await chromium.launch()
  const page = await browser.newPage()
  await page.goto("http://localhost:3000/login")
  await page.getByLabel("Email").fill("user@example.com")
  await page.getByLabel("Password").fill("secret")
  await page.getByRole("button", { name: "Sign in" }).click()
  await page.context().storageState({ path: "auth.json" })
  await browser.close()
}
```

---

## playwright.config.ts

```ts
import { defineConfig, devices } from "@playwright/test"

export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? "github" : "html",
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
    video: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "firefox", use: { ...devices["Desktop Firefox"] } },
    { name: "webkit", use: { ...devices["Desktop Safari"] } },
    // Mobile
    { name: "mobile-chrome", use: { ...devices["Pixel 5"] } },
  ],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
  },
})
```

---

## CI configuration

GitHub Actions (Windows runner):

```yaml
- name: Install Playwright browsers
  run: npx playwright install --with-deps chromium

- name: Run Playwright tests
  run: npx playwright test
  env:
    CI: true

- uses: actions/upload-artifact@v4
  if: always()
  with:
    name: playwright-report
    path: playwright-report/
    retention-days: 30
```

Headless is the default in CI — no extra flag needed. Set `CI=true` and Playwright auto-configures retries and single-worker mode (via `retries: process.env.CI ? 2 : 0`).

Linux CI requires system dependencies:

```bash
npx playwright install-deps chromium
```

---

## Common patterns

### Dialogs

```ts
page.on("dialog", (dialog) => dialog.accept())
await page.getByRole("button", { name: "Delete" }).click()
```

### File upload

```ts
const [fileChooser] = await Promise.all([
  page.waitForEvent("filechooser"),
  page.getByRole("button", { name: "Upload" }).click(),
])
await fileChooser.setFiles("./fixtures/document.pdf")
```

### Download

```ts
const [download] = await Promise.all([
  page.waitForEvent("download"),
  page.getByRole("button", { name: "Export CSV" }).click(),
])
const path = await download.path()
```

### New tab / popup

```ts
const [newPage] = await Promise.all([
  page.context().waitForEvent("page"),
  page.getByRole("link", { name: "Open in new tab" }).click(),
])
await newPage.waitForLoadState()
await expect(newPage).toHaveURL(/external/)
```

### Clipboard

```ts
await page.evaluate(() => navigator.clipboard.writeText("copied"))
const text = await page.evaluate(() => navigator.clipboard.readText())
```

### Keyboard shortcuts

```ts
await page.keyboard.press("Control+a")
await page.keyboard.press("Escape")
await page.keyboard.type("hello world")
```

---

## Debugging

```bash
# Open Playwright Inspector
npx playwright test --debug

# Pause test at specific point
await page.pause()

# Codegen: record interactions as test code
npx playwright codegen https://example.com

# Trace viewer (after test run with trace enabled)
npx playwright show-trace trace.zip
```

PWDEBUG env var enables step-through in Inspector:

```bash
$env:PWDEBUG=1; npx playwright test tests/login.spec.ts
```
