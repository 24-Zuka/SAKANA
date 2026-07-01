import { expect, test } from "@playwright/test";

const SCREENS: { path: string; heading: RegExp }[] = [
  { path: "/#/", heading: /Dashboard/ },
  { path: "/#/agents", heading: /Agents/ },
  { path: "/#/build", heading: /Build/ },
  { path: "/#/memory", heading: /Memory/ },
  { path: "/#/schedule", heading: /Schedule/ },
  { path: "/#/research", heading: /Research/ },
  { path: "/#/quota", heading: /Quota/ },
  { path: "/#/settings", heading: /Settings/ },
];

test.describe("8画面のスモークテスト", () => {
  for (const screen of SCREENS) {
    test(`${screen.path} が表示され、コンソールエラーがないこと`, async ({ page }) => {
      const errors: string[] = [];
      page.on("pageerror", (err) => errors.push(err.message));
      page.on("console", (msg) => {
        if (msg.type() === "error") errors.push(msg.text());
      });

      await page.goto(screen.path);
      await expect(page.getByRole("heading", { name: screen.heading })).toBeVisible();
      expect(errors, `console errors on ${screen.path}: ${errors.join("\n")}`).toEqual([]);
    });
  }
});

test("Dashboardにモックのチケットタイトルが表示される", async ({ page }) => {
  await page.goto("/#/");
  await expect(page.getByText("A社との提携レート再交渉の方針を決める").first()).toBeVisible();
});

test("Build画面: ビルド実行→mainへマージでApprovalModalが開閉する", async ({ page }) => {
  await page.goto("/#/build");
  await page.getByRole("button", { name: "ビルド実行" }).first().click();
  await expect(page.getByText("ビルドログ")).toBeVisible();
  await expect(page.getByText("codex exec --json でビルド開始")).toBeVisible({ timeout: 5000 });

  const mergeButton = page.getByRole("button", { name: "mainへマージ" }).first();
  await expect(mergeButton).toBeEnabled({ timeout: 5000 });
  await mergeButton.click();

  await expect(page.getByRole("dialog", { name: "" }).getByText("承認が必要です")).toBeVisible();
  await page.getByRole("button", { name: "Reject" }).click();
  await expect(page.getByText("承認が必要です")).not.toBeVisible();
});

test("⌘Kコマンドパレットがキーボードショートカットで開閉する", async ({ page }) => {
  await page.goto("/#/");
  await expect(page.getByRole("button", { name: /コマンド/ })).toBeVisible();
  await page.keyboard.down("Control");
  await page.keyboard.press("k");
  await page.keyboard.up("Control");
  await expect(page.getByPlaceholder("コマンドを検索… (⌘K)")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByPlaceholder("コマンドを検索… (⌘K)")).not.toBeVisible();
});

test("⌘Kからスクリーン遷移できる", async ({ page }) => {
  await page.goto("/#/");
  await expect(page.getByRole("button", { name: /コマンド/ })).toBeVisible();
  await page.keyboard.down("Control");
  await page.keyboard.press("k");
  await page.keyboard.up("Control");
  await page.getByPlaceholder("コマンドを検索… (⌘K)").fill("Build");
  await page.getByText("Build へ移動").click();
  await expect(page.getByRole("heading", { name: /Build/ })).toBeVisible();
});
