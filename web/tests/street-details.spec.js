import { test, expect } from "@playwright/test";

for (const code of ["COL", "CON"]) {
  test(`${code} street study opens with both render views and working branding`, async ({ page }) => {
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    await page.goto(`/#${code}`);
    await expect(page.locator('canvas[data-ready="true"]')).toBeVisible({ timeout: 60000 });
    await expect(page.locator("#detail-panel")).toContainText(code === "COL" ? "Columbia House" : "Connaught House");
    await expect(page.locator("#detail-panel")).toContainText("估计");
    await expect(page.locator("#view-mode")).toHaveText("建筑外观");
    const mark = page.locator(".brand-mark");
    await expect(mark).toHaveJSProperty("naturalWidth", 80);
    const size = await mark.boundingBox();
    expect(size.width).toEqual(size.height);
    await page.waitForTimeout(1100);
    await page.screenshot({ path: `result/web/edition04-${code.toLowerCase()}.png` });
    await page.locator(".detail-photo").click();
    await expect(page.locator("#gallery-position")).toHaveText("1 / 2");
    await page.locator("#gallery-next").click();
    await expect(page.locator("#gallery-position")).toHaveText("2 / 2");
    await page.keyboard.press("Escape");
    await page.locator("#about-open").click();
    await expect(page.locator(".about-logo")).toHaveJSProperty("naturalWidth", 234);
    await expect(page.locator("#about-dialog")).toContainText("第05版");
    await expect(page.locator("#about-dialog")).toContainText("14栋");
    expect(errors).toEqual([]);
  });
}
