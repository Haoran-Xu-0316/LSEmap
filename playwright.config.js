import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./web/tests",
  timeout: 90000,
  expect: { timeout: 20000 },
  workers: 1,
  outputDir: "./result/web/test-results",
  reporter: [["list"], ["json", { outputFile: "result/web/tests.json" }]],
  use: {
    launchOptions: {
      args:
        process.platform === "darwin"
          ? ["--use-angle=metal"]
          : ["--enable-unsafe-swiftshader"],
    },
    baseURL: "http://127.0.0.1:4174",
    viewport: { width: 1440, height: 1000 },
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "npm run preview -- --port 4174",
    url: "http://127.0.0.1:4174",
    reuseExistingServer: false,
  },
});
