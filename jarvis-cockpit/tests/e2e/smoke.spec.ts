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
        // ネットワーク遮断環境ではGoogle Fontsの読み込み失敗がconsole.errorとして
        // 記録されるが、アプリのJSエラーではないため除外する。
        if (msg.type() === "error" && !/Failed to load resource/.test(msg.text())) {
          errors.push(msg.text());
        }
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

  await expect(page.getByRole("dialog").getByText("承認モーダル")).toBeVisible();
  await expect(page.getByText("レビュー件数")).toBeVisible();
  await page.getByRole("button", { name: "Reject" }).click();
  await expect(page.getByText("承認モーダル")).not.toBeVisible();
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

test("Dashboard: risk_scoreが低いチケットは承認なしでステータス遷移できる", async ({ page }) => {
  await page.goto("/#/");
  const row = page.getByRole("listitem").filter({ hasText: "Cockpit Dashboard画面の実装" });
  await expect(row).toBeVisible();
  await row.getByRole("button", { name: "→ Done" }).click();
  await expect(page.getByText("を Done に更新しました")).toBeVisible({ timeout: 5000 });
  await expect(row.getByText("Done", { exact: true })).toBeVisible();
});

test("Dashboard: risk_score>=3.0のチケット遷移は承認モーダル必須", async ({ page }) => {
  await page.goto("/#/");
  const row = page.getByRole("listitem").filter({ hasText: "A社との提携レート再交渉の方針を決める" });
  await expect(row).toBeVisible();
  await row.getByRole("button", { name: "→ Done" }).click();

  await expect(page.getByRole("dialog").getByText("承認モーダル")).toBeVisible();
  await page.getByRole("button", { name: "Approve" }).click();
  await expect(page.getByText("承認モーダル")).not.toBeVisible();
  await expect(page.getByText("を Done に更新しました")).toBeVisible({ timeout: 5000 });
  await expect(row.getByText("Done", { exact: true })).toBeVisible();
});

test("Dashboard: Mockモードでは実行ボタンが無効化されている", async ({ page }) => {
  await page.goto("/#/");
  const row = page.getByRole("listitem").filter({ hasText: "Cockpit Dashboard画面の実装" });
  await expect(row.getByRole("button", { name: "実行" })).toBeDisabled();
});

test("Settings: ブリッジ接続設定がlocalStorageへ永続化されリロード後も残る", async ({ page }) => {
  await page.goto("/#/settings");
  const urlInput = page.getByLabel(/^URL/);
  await urlInput.fill("http://127.0.0.1:9999");
  await urlInput.blur();
  await expect(page.getByText("ブリッジ接続設定を保存しました")).toBeVisible({ timeout: 5000 });

  await page.reload();
  await expect(page.getByLabel(/^URL/)).toHaveValue("http://127.0.0.1:9999");

  // 後続テストへ影響しないよう元に戻す。
  await page.evaluate(() => localStorage.removeItem("jarvis.bridgeUrl"));
});
