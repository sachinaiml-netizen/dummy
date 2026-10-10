const assert = require("node:assert/strict");
const fs = require("node:fs");
const { spawn } = require("node:child_process");
const { chromium } = require("playwright");

const host = "127.0.0.1";
const port = 8765;
const baseUrl = "http://" + host + ":" + port;
const server = spawn(
  process.env.PYTHON || "python",
  ["-m", "uvicorn", "app.main:app", "--host", host, "--port", String(port)],
  { stdio: ["ignore", "pipe", "pipe"] }
);

let serverOutput = "";
server.stdout.on("data", (chunk) => { serverOutput += chunk.toString(); });
server.stderr.on("data", (chunk) => { serverOutput += chunk.toString(); });

async function waitForServer(timeoutMs = 20000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (server.exitCode !== null) {
      throw new Error("FastAPI exited before becoming ready.\n" + serverOutput);
    }
    try {
      const response = await fetch(baseUrl + "/health");
      if (response.ok) return;
    } catch (_) {
      // The local server may need a few seconds to bind its port.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error("FastAPI did not become ready.\n" + serverOutput);
}

async function main() {
  let browser;
  const pageErrors = [];
  try {
    await waitForServer();
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({ acceptDownloads: true });
    page.on("pageerror", (error) => pageErrors.push(error.message));

    await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() =>
      document.querySelector("#kpiScenario")?.textContent.includes("Long-lead procurement +14d") &&
      document.querySelector("#keyInsight")?.textContent.includes("1 day(s) of float remain")
    );
    assert.equal(await page.locator("#kpiBaseline").innerText(), "Day 119");
    assert.equal(await page.locator("#kpiSlip").innerText(), "0d");

    // Verify both sides of the threshold: float exhausted, then finish-date slip.
    await page.locator("#float15Case").click();
    await page.waitForFunction(() =>
      document.querySelector("#kpiScenario")?.textContent.includes("Long-lead procurement +15d") &&
      document.querySelector("#keyInsight")?.textContent.includes("consumed all")
    );
    assert.equal(await page.locator("#shockFinish").innerText(), "Day 119");
    assert.ok((await page.locator("#pathDiff").innerText()).includes("After disruption (2)"));

    await page.locator("#float16Case").click();
    await page.waitForFunction(() =>
      document.querySelector("#kpiScenario")?.textContent.includes("Long-lead procurement +16d") &&
      document.querySelector("#shockFinish")?.textContent === "Day 120"
    );
    assert.equal(await page.locator("#kpiSlip").innerText(), "+1d");

    // Evaluate the separate synthetic-risk model; verify a stressed and a healthy input.
    await page.locator("#runRiskModelButton").click();
    await page.waitForFunction(() =>
      document.querySelector("#riskModelStatus")?.textContent.includes("Experimental result ready") &&
      document.querySelector("#riskModelOutput")?.hidden === false
    );
    assert.match(await page.locator("#riskModelVersion").innerText(), /0\.1\.0-synthetic/);
    assert.equal((await page.locator("#riskModelBand").innerText()).trim(), "HIGH");
    assert.ok(parseFloat(await page.locator("#riskModelProbability").innerText()) > 90);
    assert.ok((await page.locator("#riskModelWarnings").innerText()).includes("not trained on Prestige data"));

    await page.locator("#riskPlannedProgress").fill("50");
    await page.locator("#riskActualProgress").fill("49");
    await page.locator("#riskBudgetVariance").fill("1");
    await page.locator("#riskVendorDelay").fill("0");
    await page.locator("#riskOpenIssues").fill("1");
    await page.locator("#riskQualityDefects").fill("0");
    await page.locator("#runRiskModelButton").click();
    await page.waitForFunction(() =>
      document.querySelector("#riskModelStatus")?.textContent.includes("Experimental result ready") &&
      document.querySelector("#riskModelBand")?.textContent === "LOW"
    );
    assert.ok(parseFloat(await page.locator("#riskModelProbability").innerText()) < 10);

    // Download the app's own fixture, then upload those exact bytes through the real file input.
    const sampleResponse = await page.request.get(baseUrl + "/sample-schedule.csv");
    assert.equal(sampleResponse.status(), 200);
    assert.match(sampleResponse.headers()["content-type"], /text\/csv/);
    const sampleCsv = await sampleResponse.text();
    assert.match(sampleCsv, /^task_id,task_name,duration_days,predecessors/m);

    await page.locator("#csvFile").setInputFiles({
      name: "project-impact-lab-sample.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(sampleCsv, "utf8")
    });
    await page.waitForFunction(() =>
      document.querySelector("#csvStatus")?.textContent.includes("File selected")
    );
    await page.locator("#validateCsvButton").click();
    await page.waitForFunction(() =>
      document.querySelector("#csvStatus")?.textContent.includes("CSV valid: 8 activities")
    );
    assert.equal((await page.locator("#csvCount").innerText()).trim(), "8");
    assert.equal((await page.locator("#csvBaselineFinish").innerText()).trim(), "Day 119");

    await page.locator("#csvDisruptedTask").selectOption("PR-01");
    await page.locator("#csvDelayDays").fill("14");
    await page.locator("#runCsvScenarioButton").click();
    await page.waitForFunction(() =>
      document.querySelector("#csvStatus")?.textContent.includes("Scenario recalculated from 8 validated activities")
    );
    assert.equal((await page.locator("#csvSlip").innerText()).trim(), "0d");
    assert.ok((await page.locator("#csvKeyInsight").innerText()).includes("1 day(s) remain"));

    const downloadPromise = page.waitForEvent("download");
    await page.locator("#downloadCsvBriefButton").click();
    const download = await downloadPromise;
    assert.equal(download.suggestedFilename(), "project-impact-lab-decision-brief.txt");
    const downloadPath = await download.path();
    assert.ok(downloadPath, "Decision brief should be downloaded to a temporary file");
    const brief = fs.readFileSync(downloadPath, "utf8");
    for (const expected of [
      "PROJECT IMPACT LAB — DECISION BRIEF",
      "Activities analysed: 8",
      "Activity: PR-01 — Long-lead procurement",
      "Added delay: 14 day(s)",
      "Total float: 15d -> 1d",
      "Float consumed: 14 day(s)",
      "Baseline finish: Day 119",
      "Scenario finish: Day 119",
      "Handover slip: 0 day(s)",
      "not parse native Primavera P6 XER/XML",
      "This model uses finish-to-start links",
      "Imported schedules are not saved by the application"
    ]) {
      assert.ok(brief.includes(expected), "Downloaded brief missing expected text: " + expected);
    }

    // Verify CSV-provided HTML is rendered as text, not executable markup.
    const hostileCsv = 'task_id,task_name,duration_days,predecessors\nA,"<img src=x onerror=window.__xss=1>",2,\n';
    await page.locator("#csvFile").setInputFiles({
      name: "label-escaping-check.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(hostileCsv, "utf8")
    });
    await page.waitForFunction(() =>
      document.querySelector("#csvStatus")?.textContent.includes("File selected")
    );
    await page.locator("#validateCsvButton").click();
    await page.waitForFunction(() =>
      document.querySelector("#csvStatus")?.textContent.includes("CSV valid: 1 activities")
    );
    assert.equal(await page.locator("#csvTaskRows img").count(), 0, "CSV task names must not create HTML elements");
    assert.equal(await page.evaluate(() => window.__xss || false), false, "CSV task names must not execute script");

    // An invalid dependency must show a readable error and invalidate the previous result.
    const invalidCsv = "task_id,task_name,duration_days,predecessors\nA,Approval,2,MISSING\n";
    await page.locator("#csvFile").setInputFiles({
      name: "invalid-missing-predecessor.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(invalidCsv, "utf8")
    });
    await page.waitForFunction(() =>
      document.querySelector("#csvStatus")?.textContent.includes("File selected")
    );
    await page.locator("#validateCsvButton").click();
    await page.waitForFunction(() =>
      document.querySelector("#csvStatus")?.className.includes("error") &&
      document.querySelector("#csvStatus")?.textContent.includes("Unknown predecessor")
    );
    assert.equal(await page.locator("#csvOutput").isHidden(), true, "Invalid schedule must not leave a stale report visible");
    assert.equal(await page.locator("#runCsvScenarioButton").isDisabled(), true, "Invalid schedule must not be available for scenario runs");
    assert.equal(await page.locator("#downloadCsvBriefButton").isVisible(), false, "Invalid schedule must not allow export of a stale decision brief");

    assert.deepEqual(pageErrors, [], "Unexpected browser exceptions: " + pageErrors.join("; "));
    console.log("Browser E2E passed: threshold boundaries, sample download/upload, CSV analysis, decision-brief download/content, and safe task-name rendering.");
  } finally {
    if (browser) await browser.close();
    server.kill("SIGTERM");
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
