# Monday Interview Playbook — Project Impact Lab

## The problem statement to lead with

“On a construction schedule, an activity can be delayed without moving handover immediately because it still has total float. But once that buffer is used up, the activity can become critical and a further delay can move handover. Project Impact Lab lets a project-controls user inject a delay, see remaining float and the affected path, then compare a few recovery options with explicit assumptions. The example is synthetic, and the purpose is to test whether this simple explanation adds value alongside the team's existing scheduling tools.”

This is the core problem; do not start with AI or the dashboard. AI is not the engine of the current CPM simulation.

## The 30-second pitch

“I started with an AI project-risk dashboard, then noticed that risk dashboards already exist in construction software. I changed the question: when an activity is delayed, does it actually move the project handover date, and which recovery action is worth paying for? Project Impact Lab models a dependency network, injects a delay, propagates the effect to dependent work, then compares candidate actions using transparent cost assumptions. Everything in this demo is synthetic. I want to validate whether this decision-rehearsal layer would be useful on approved historical schedules.”

Do not call it a trained prediction model. The current decision engine is a deterministic critical-path simulator.

## The demo's strongest, easiest-to-explain case

Choose **Test schedule float** and inject a 14-day procurement delay. Baseline total float is 15 days; the new scenario shows one day left. The project finish remains Day 119, but the buffer is almost gone. At 15 days, that path becomes co-critical; at 16 days, the simplified model moves handover to Day 120. This is the clearest story because the user can explain all three outcomes with one concept: float.

Do not call this market-unique. Oracle Primavera Cloud already supports critical paths, total float and multiple float paths. The hypothesis is whether this particular transparent delay-to-decision flow is useful beside existing tools.

## Study this before the interview

Follow the [six-hour learning guide](SIX_HOUR_LEARNING_GUIDE.md) and read the [problem statement](PROBLEM_STATEMENT.md). Those two documents are the priority; do not begin by memorising the entire codebase.

## The three-minute demo

### 1. Start with the business decision (20 seconds)

“An activity can be late without delaying the whole project. The critical question is whether it changes the controlling path to handover.”

### 2. Run the critical-path case (60 seconds)

- Keep the disruption at ST-01, Structure works.
- Keep the delay at 14 days and daily exposure at ₹4.5 lakh.
- Point to baseline handover Day 119 and no-action handover Day 133.
- Show the activity impact trace: the structure delay shifts facade closure, interiors and handover.
- Show the ranked actions. The assumed structural recovery crew saves 6 days at an assumed cost of ₹8 lakh. The arithmetic is 6 × ₹4.5L − ₹8L = ₹19L net modeled value.

Say clearly: “These numbers are synthetic. The value is not the ₹19 lakh itself; the value is that I can show every assumption and how the decision changes if we change it.”

### 3. Run the schedule-float case (45 seconds)

- Click “Test schedule float”.
- The disruption moves to long-lead procurement with a 14-day delay.
- Handover remains at Day 119 because the facade chain still controls the modeled finish.
- The system should select no paid action for finish-date recovery under these assumptions.

Say: “This is the counterexample. A late task is not automatically a project-level delay. Spending ₹12 lakh to expedite a task that does not move the finish date is not justified by this model.”

### 4. Show recommendation stability (30 seconds)

- Point to the new “Recommendation stability · stress test” panel.
- In the critical-path case, the same recovery action should remain the choice across the nearby tested assumptions. Explain that this is stability within a small test grid, not a probability guarantee.
- Click “Test schedule float”. Show that the no-action recommendation can change when the assumed procurement delay is extended and daily exposure rises. Explain that the model marks this decision as sensitive and should not hide the uncertainty.
- State that the stress grid varies the delay by ±4 days and the daily-exposure assumption by ±25%; it is deterministic and not Monte Carlo.

### 5. Close with a realistic pilot (30 seconds)

“I would not connect this to live systems without permission. The next step is to validate the dependency model with project controls using one approved historical schedule, compare the simulated finish against actual outcomes, and have the team review the recovery actions and cost assumptions. If it does not outperform the current planning baseline on agreed metrics, we should not deploy it.”

## If the interviewer asks difficult questions

### “Isn't this already available in Autodesk or Primavera?”

“Those platforms already provide risk analytics and schedule/risk simulation. I am not claiming to replace them or that this capability is unique globally. My hypothesis is narrower: an explainable layer that compares a small set of recovery actions against the actual dependency path and transparent cost assumptions may help a decision-maker compare options. That hypothesis needs to be validated against the team's current workflow.”

### “Where is the AI?”

“In this version, the decision engine is not an AI model; it is deterministic graph and critical-path logic. That is deliberate because I have no authorized, labelled Prestige project history to train or validate a model. The separate /risk endpoint uses a bounded, deterministic rule-based deviation indicator, not an ML anomaly detector or a probability. I removed the synthetic Isolation Forest because a model fitted to generated 'normal' data gives no evidence of real-world validity and adds substantial deployment dependencies. With permissioned historical data, I would first test whether a calibrated ML approach improves on this transparent baseline. With permissioned historical data, I would first build a basic schedule-variance baseline, use time-aware validation, then test whether ML improves decision quality over that baseline.”

### “How does the calculation work?”

“The engine validates the activity graph and topologically sorts it, so the input rows do not have to already be ordered. In the forward pass, an activity starts at the latest finish of its predecessors. In the backward pass, latest dates are traced back from the modeled project finish. Total float is late start minus early start. Zero-float activities and the dependency edges that drive them define critical paths. If two paths tie, the API preserves both rather than choosing a single predecessor. I inject delay into one task, recompute the network, then apply each action's assumed duration reduction one at a time. I calculate days recovered relative to the no-action scenario, cap the credit at the delay introduced, then subtract the action cost from recovered days multiplied by the editable daily exposure assumption.”

### “Where did ₹4.5 lakh per day come from?”

“It is a user-editable placeholder, not company data or a benchmark. A real pilot would need finance and project-controls teams to define what a delay day means for that project—overheads, financing or carrying cost, contractual exposure and other agreed components—without double-counting. If that input is unreliable, the value ranking is unreliable.”

### “What happens if two paths are equally critical?”

“The earlier version displayed one path and could silently choose one predecessor when two paths finished at the same time. I changed the engine to calculate total float with a backward pass and preserve tied critical paths. For example, a 15-day procurement delay exhausts the procurement path's modeled float and can make the procurement/MEP path tie with the structural/facade path. The demo now exposes both paths and each task's baseline and scenario float. It still assumes finish-to-start links and no work calendars or resource constraints.”

### “What if the data is wrong or incomplete?”

“Then the output can be wrong. The next engineering step is data-quality gating: identify missing predecessors, stale updates, inconsistent activity IDs and incomplete baselines; show which inputs are missing; and refuse to rank interventions when key data is unreliable. A production model also needs source lineage, versioned assumptions, access controls, audit logs and human approval.”

### “Why not use Monte Carlo simulation?”

“Monte Carlo is useful when we have credible uncertainty distributions and need a range of finish dates rather than one deterministic scenario. This small prototype intentionally isolates the dependency and intervention logic first. A pilot could add probabilistic durations after the team can justify those distributions from historical data and expert review.”

### “Why don't you use computer vision or a digital twin?”

“Those are possible data sources, not a reason to add complexity on day one. A BIM model or site image only helps this decision if it produces a reliable, timestamped signal that maps to a schedule activity and changes the action choice. I would start with approved schedule exports and validate the decision engine before adding vision or richer 4D/5D connections.”

### “What would you measure in a pilot?”

“Before testing, I would agree on metrics with project controls: predicted versus actual finish-date error, warning lead time, percentage of alerts that lead to a verified action, false-positive burden, quality of intervention ranking, and whether the recommended action improves the schedule after accounting for cost. I'd compare it against the existing planning process, not just report a model accuracy score.”

### “Can you guarantee this will save money?”

“No. This proof of concept cannot make that claim. It exposes assumptions and makes counterfactuals easy to compare. Savings would only be established through back-testing and a controlled pilot using real, approved inputs.”

## Honest limitations you should volunteer

- The recommendation stress test is a small deterministic grid; it does not produce a statistical confidence interval or probability.
- The dependency network is a small synthetic DAG, not a Prestige schedule.
- It uses simplified finish-to-start logic; no work calendars, resources, contract conditions, lags, weather, uncertainty distributions or change orders.
- Recovery days and action costs are assumed.
- There is no live integration with Autodesk, Primavera, ERP or RERA.
- The legacy snapshot-risk route is a weighted heuristic; its field named `anomaly_score` is a compatibility label for a bounded rule-based indicator.
- The app is not a trained, validated delay-prediction model.
- The value estimate is sensitive to the daily-exposure assumption.

Showing that you understand these limits is stronger than overclaiming.

## How to talk about compensation and the role

Do not ask the interviewer to pay a large package because of a prototype. That sounds disconnected from the evidence and risks undermining the project. First establish what problem the interviewer owns, show the demo, and demonstrate that you can reason technically and take feedback.

A useful close is:

“If this problem is relevant, I would like to work with the technology or project-controls team on a short validation exercise. I am open to the appropriate entry route—internship, trainee role or project-based assignment—where I can prove the value with real engineering work. What would you need to see from me to be considered for that?”

Discuss compensation after the role scope, employment type, expected contribution and selection process are clear.

## Interviewer questions for you to ask

1. “Where do your teams lose the most time today: getting visibility into project status, finding dependencies, or selecting a recovery action?”
2. “Which scheduling and project-data sources are approved for integration, and who owns their quality?”
3. “How do you currently determine whether a proposed recovery action is worth its added cost?”
4. “What evidence would make a small proof of concept worth a pilot to your team?”

## Before Monday, 5 p.m.

- Run the app locally and click both demo scenarios without referring to notes.
- Explain the forward-pass/critical-path method on paper.
- Be ready to calculate 6 × ₹4.5L − ₹8L = ₹19L aloud.
- Practice the Autodesk/Primavera objection until you can state the differentiation without claiming novelty the market does not support.
- Show how the recommendation stability panel distinguishes a stable choice from a decision that changes under nearby assumptions.
- Check that the GitHub branch / pull request is available and that the app runs on the laptop you will use.
- Do not describe synthetic project names or costs as Prestige facts.
