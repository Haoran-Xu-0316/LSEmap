/** Require a settled compositor frame before comparing WebGL architecture. */
export async function captureSettledCanvas(page, canvas) {
  let previous;
  for (let attempt = 0; attempt < 8; attempt++) {
    await page.evaluate(() => new Promise(resolve => {
      requestAnimationFrame(() => requestAnimationFrame(resolve));
    }));
    const current = await canvas.screenshot();
    if (previous?.equals(current)) return current;
    previous = current;
  }
  throw new Error('Building canvas did not settle to two identical frames');
}
