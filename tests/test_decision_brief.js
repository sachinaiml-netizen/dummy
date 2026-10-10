const assert = require("node:assert/strict");
const fs = require("node:fs");

const html = fs.readFileSync("static/index.html", "utf8");
const match = html.match(
  /function buildCsvDecisionBrief\(result\)\s*\{([\s\S]*?)\n\}\nfunction downloadCsvDecisionBrief\(\)/
);
assert.ok(match, "Decision-brief builder must exist as a standalone function");

const buildBrief = new Function("result", match[1]);
const validScenario = {
  activity_count: 8,
  disrupted_task_id: "PR-01",
  delay_days: 14,
  disrupted_task_baseline_total_float_days: 15,
  disrupted_task_scenario_total_float_days: 1,
  disrupted_task_float_consumed_days: 14,
  baseline_finish_day: 119,
  scenario_finish_day: 119,
  handover_slip_days: 0,
  baseline_critical_path_count: 1,
  scenario_critical_path_count: 1,
  key_insight: "The 14-day delay consumed 14 of 15 float days; one day remains.",
  baseline_critical_paths: [["AP-01", "DS-01", "ST-01", "FC-01", "IN-01", "HO-01"]],
  scenario_critical_paths: [["AP-01", "DS-01", "ST-01", "FC-01", "IN-01", "HO-01"]],
  critical_paths_truncated: false,
  validation_scope: "Required fields, task IDs, durations and predecessor links were validated.",
  format_note: "This is the prototype's simplified CSV format, not native P6 XER/XML.",
  activities: [
    {
      task_id: "PR-01",
      task_name: "Long-lead procurement",
      baseline_early_finish_day: 56,
      scenario_early_finish_day: 70,
      baseline_total_float_days: 15,
      scenario_total_float_days: 1,
      on_scenario_critical_path: false
    },
    {
      task_id: "ME-01",
      task_name: "MEP rough-in",
      baseline_early_finish_day: 83,
      scenario_early_finish_day: 88,
      baseline_total_float_days: 6,
      scenario_total_float_days: 1,
      on_scenario_critical_path: false
    }
  ]
};

const brief = buildBrief(validScenario);
for (const required of [
  "PROJECT IMPACT LAB — DECISION BRIEF",
  "Activities analysed: 8",
  "Activity: PR-01 — Long-lead procurement",
  "Added delay: 14 day(s)",
  "Total float: 15d -> 1d",
  "Float consumed: 14 day(s)",
  "Baseline finish: Day 119",
  "Scenario finish: Day 119",
  "Handover slip: 0 day(s)",
  "CP1: AP-01 -> DS-01 -> ST-01 -> FC-01 -> IN-01 -> HO-01",
  "VALIDATION SCOPE",
  "not native P6 XER/XML",
  "This model uses finish-to-start links",
  "CSV contents are sent to this app API for validation and calculation",
  "not a confidentiality or host/provider non-retention guarantee",
  "Review this brief with project controls"
]) {
  assert.ok(brief.includes(required), `Decision brief missing: ${required}`);
}

const baselineBrief = buildBrief({
  ...validScenario,
  disrupted_task_id: null,
  delay_days: 0
});
assert.ok(baselineBrief.includes("Activity delay: none (baseline validation only)."));
assert.ok(baselineBrief.includes("Baseline finish: Day 119"));

const hostileBrief = buildBrief({
  ...validScenario,
  key_insight: "Normal finding.\nFAKE RECOMMENDATION: approved for release",
  validation_scope: "Graph validated.\nFAKE SCOPE: no checks were run",
  baseline_critical_paths: [["AP-01\nFAKE PATH: safe"]],
  activities: [{
    ...validScenario.activities[0],
    task_name: "Long-lead procurement\nFAKE SECTION: approved\nSECOND LINE"
  }]
});
assert.ok(hostileBrief.includes("Long-lead procurement FAKE SECTION: approved SECOND LINE"));
const hostileLines = hostileBrief.split("\n");
for (const fakeLine of [
  "FAKE RECOMMENDATION: approved for release",
  "FAKE SCOPE: no checks were run",
  "FAKE PATH: safe",
  "FAKE SECTION: approved",
  "SECOND LINE"
]) {
  assert.ok(!hostileLines.includes(fakeLine), "Control-character injection created a standalone line: " + fakeLine);
}
assert.ok(hostileBrief.includes("Normal finding. FAKE RECOMMENDATION: approved for release"));
console.log("Decision brief output tests passed (baseline, scenario, data-flow note and line-injection cases).");
