import { test, expect } from "@playwright/test";

async function ready(page) {
  await page.goto("/");
  await expect(page.locator('canvas[data-ready="true"]')).toBeVisible({
    timeout: 60000,
  });
  await expect(page.locator("#loading")).toBeHidden();
}

test("desktop exploration, search, images, interior and navigation work without runtime errors", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const failedRequests = [];
  page.on("response", (response) => {
    if (response.status() >= 400)
      failedRequests.push(`${response.status()} ${response.url()}`);
  });
  await ready(page);
  await expect(page.locator(".building-row")).toHaveCount(31);
  await page.screenshot({ path: "result/web/desktop-overview.png" });
  const canvas = page.locator("canvas");
  const initialView = await canvas.screenshot();
  const rectangle = await canvas.boundingBox();
  await page.mouse.move(
    rectangle.x + rectangle.width * 0.6,
    rectangle.y + rectangle.height * 0.6,
  );
  await page.mouse.down();
  await page.mouse.move(
    rectangle.x + rectangle.width * 0.7,
    rectangle.y + rectangle.height * 0.55,
    { steps: 12 },
  );
  await page.mouse.up();
  await page.waitForTimeout(300);
  expect((await canvas.screenshot()).equals(initialView)).toBe(false);
  await page.locator("#overview").click();
  await page.waitForTimeout(1100);
  await page.locator('.map-label[data-code="MAR"]').click();
  await expect(page.locator("#detail-panel h2")).toHaveText(
    "Marshall Building",
  );
  await page.locator("#overview").click();
  await page.locator("#detail-filter").click();
  await expect(page.locator(".building-row")).toHaveCount(14);
  await page.locator("#building-search").fill("zzmissing");
  await expect(page.locator("#empty-search")).toBeVisible();
  await page.locator("#building-search").fill("MAR");
  await page.locator('.building-row[data-code="MAR"]').click();
  await expect(page).toHaveURL(/#MAR$/);
  await expect(page.locator("#detail-panel h2")).toHaveText(
    "Marshall Building",
  );
  await page.locator(".detail-photo").click();
  await expect(page.locator("#gallery-dialog")).toBeVisible();
  await page.locator("#gallery-next").click();
  await expect(page.locator("#gallery-position")).toHaveText("2 / 4");
  await page.keyboard.press("Escape");
  await expect(page.locator("#gallery-dialog")).toBeHidden();
  await page.locator("#interior-view").click();
  await expect(page.locator("#interior-view")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await expect(page.locator("#view-mode")).toHaveText("公共内部");
  await page.waitForTimeout(1100);
  await page.screenshot({ path: "result/web/desktop-interior.png" });
  await page.locator("#exterior-view").click();
  await expect(page.locator("#view-mode")).toHaveText("建筑外观");
  await page.locator("#overview").click();
  await page.locator("#detail-filter").click();
  await page.locator("#building-search").fill("49L");
  await page.locator('.building-row[data-code="49L"]').click();
  await expect(page.locator("#detail-panel")).toContainText("沿街立面研究");
  await expect(page.locator("canvas")).toHaveAttribute("data-detail-ready", "exterior-49L", { timeout: 45000 });
  await page.locator("#overview").click();
  await page.locator("#labels-toggle").click();
  await expect(page.locator("#labels-toggle")).toHaveAttribute(
    "aria-pressed",
    "false",
  );
  await expect(page.locator(".map-label:visible")).toHaveCount(0);
  await page.locator("#context-toggle").click();
  await expect(page.locator("#context-toggle")).toHaveAttribute(
    "aria-pressed",
    "false",
  );
  await page.locator("#about-open").click();
  await expect(page.locator("#about-dialog")).toContainText("无官方隶属关系");
  await page.keyboard.press("Escape");
  expect(errors).toEqual([]);
  expect(failedRequests).toEqual([]);
});

test("mobile map and detail sheet remain usable without horizontal overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await ready(page);
  await expect(page.locator("#sidebar")).toBeHidden();
  await page.screenshot({ path: "result/web/mobile-overview.png" });
  await page.locator("#index-toggle").click();
  await page.locator("#building-search").fill("OCS");
  await page.locator('.building-row[data-code="OCS"]').click();
  await expect(page.locator("#detail-panel h2")).toHaveText(
    "Old Curiosity Shop",
  );
  await page.waitForTimeout(1100);
  await page.screenshot({ path: "result/web/mobile-detail.png" });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const toolbar = await page.locator(".map-toolbar").boundingBox();
  const sheet = await page.locator("#sidebar").boundingBox();
  expect(toolbar.y + toolbar.height).toBeLessThanOrEqual(sheet.y);
  await page.locator(".detail-photo").click();
  await expect(page.locator("#gallery-dialog")).toBeVisible();
  await page.locator("#gallery-dialog [data-close]").click();
  await expect(page.locator(".detail-photo")).toBeFocused();
  await page.locator("#overview").click();
  await expect(page.locator("#sidebar")).toBeHidden();
});

test("model network failure preserves gallery access and retry recovers", async ({
  page,
}) => {
  await page.route("**/models/campus.glb*", (route) => route.abort());
  await page.goto("/");
  await expect(page.locator("#fallback")).toBeVisible({ timeout: 60000 });
  await page.locator('.building-row[data-code="OCS"]').click();
  await page.locator(".detail-photo").click();
  await expect(page.locator("#gallery-dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await page.unroute("**/models/campus.glb*");
  await page.locator("#retry").click();
  await expect(page.locator('canvas[data-ready="true"]')).toBeVisible({
    timeout: 60000,
  });
  await expect(page.locator("#fallback")).toBeHidden();
});

test("deep links, keyboard controls and reduced motion work", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/#LRB");
  await expect(page.locator('canvas[data-ready="true"]')).toBeVisible({
    timeout: 60000,
  });
  await expect(page.locator("#detail-panel h2")).toContainText("Library");
  await page.locator("canvas").focus();
  await page.keyboard.press("+");
  await page.keyboard.press("ArrowLeft");
  await page.keyboard.press("Home");
  await expect(page.locator("#scene-title")).toHaveText("伦敦的这一角");
  await expect(page).not.toHaveURL(/#LRB$/);
});

test("every additional public-interior model loads with its reviewed viewpoint", async ({
  page,
}) => {
  await ready(page);
  for (const code of ["CBG", "CKK", "LRB", "SAW"]) {
    await page.locator(`#building-search`).fill(code);
    await page.locator(`.building-row[data-code="${code}"]`).click();
    await page.locator("#interior-view").click();
    await expect(page.locator("#interior-view")).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await page.waitForTimeout(1100);
    await page.screenshot({
      path: `result/web/interior-${code.toLowerCase()}.png`,
    });
    await page.locator("#overview").click();
  }
});
