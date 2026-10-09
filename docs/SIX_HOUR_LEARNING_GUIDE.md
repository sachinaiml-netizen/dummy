# Six-Hour Learning Guide — Project Impact Lab

**Goal:** after 5 hours 40 minutes of focused study, explain the problem, demo and algorithm honestly without pretending to be an experienced construction scheduler or claiming to have written every line unaided.

Use the live preview and the linked files. Do not try to memorise the whole repository.

## Study plan (5 hours 40 minutes)

### Block 1 — Problem and construction context (35 minutes)

Read Problem Statement.

You must be able to explain:
- What an activity is: a piece of work with a duration.
- What a dependency is: one activity must finish before another can start.
- What handover means in this simplified example: the final modeled milestone.
- What total float means: in this model, how much an activity's timing can move before it changes the modeled project finish, under the assumed logic.
- Why "activity delayed" and "project finish delayed" are not the same statement.

Repeat the 45–60 second problem statement out loud until it sounds like your own explanation.

### Block 2 — Frontend (40 minutes)

Open static/index.html.

Know these parts:
- **HTML:** the page structure and labels, such as the scenario controls and activity table.
- **CSS:** the colors, layout, spacing and small-screen styles. It changes how the page looks, not the schedule maths.
- **JavaScript:** reads the selected activity/delay, sends a request to the API using fetch, and puts the returned values into the page.
- **Event handlers:** the button actions that run a scenario or choose a ready-made example.

Be ready to answer: “If I change the delay slider, who calculates the new finish date?” Answer: “The browser sends the changed input to the FastAPI backend; the Python decision engine recomputes the scenario and returns JSON. JavaScript displays that response.”

### Block 3 — Backend and API (45 minutes)

Read app/main.py and app/schemas.py.

Understand:
- **FastAPI** defines URL routes the browser or another program can call.
- GET /api/scenario returns the default scenario.
- POST /api/scenario accepts a chosen activity, number of delay days and illustrative daily-exposure assumption.
- POST /api/schedule/analyze-csv accepts a bounded CSV text payload, optional activity ID and delay. Its CSV parser validates the task network before calling the same CPM engine.
- GET /sample-schedule.csv downloads an invented eight-activity example. The accepted CSV schema is not a native Primavera export format.
- **Pydantic** checks incoming fields and their ranges before the endpoint calls the engine.
- JSON is the format used to send structured results from Python back to JavaScript.
- requirements.txt contains packages needed by the running app; requirements-dev.txt contains extra packages used for tests.

### Block 4 — The scheduling engine (70 minutes)

Read app/decision_engine.py, focusing on analyze_schedule, analyze_schedule_csv, _schedule and simulate_project.

Use this mental model:
1. **Validate:** every task ID must be unique; every predecessor must exist; duration must be positive; dependencies cannot contain a loop.
2. **Topological sort:** arrange activities so predecessors are calculated before their successors, regardless of the row order in the input.
3. **Forward pass:** early start = latest early finish among predecessors; early finish = early start + duration.
4. **Project finish:** the latest early finish among all terminal activities.
5. **Backward pass:** calculate latest dates from successors toward predecessors.
6. **Total float:** late start − early start. In this simplified model, zero-float activities are critical.
7. **Tied critical paths:** if two paths both control the same finish date, keep both rather than selecting just one.

Practice the three procurement cases: 14, 15 and 16 days of added delay. You need to explain the change from 15 days of baseline float to 1 day, then 0 days, then a one-day finish slip.

### Block 5 — Recovery actions, assumptions and tests (45 minutes)

Read the intervention definitions in app/decision_engine.py and the tests in tests/test_scenario.py.

Know this formula:
- Illustrative net value = (modeled days recovered × assumed cost exposure per day) − assumed action cost.

For the default case: 6 × ₹4.5 lakh − ₹8 lakh = ₹19 lakh of *illustrative modeled net value*. It is not actual savings.

Tests are executable examples of expected behaviour. The suite checks ordinary cases and edge cases, such as missing dependencies, cycles, tied paths, float exhaustion, long input chains and CSV import errors. CI runs those tests automatically when code changes are pushed.

### Block 6 — Competitive context and interview rehearsal (45 minutes)

Read the competitive comparison in Problem Statement. Do not claim global uniqueness. Autodesk, Oracle Primavera, Bentley and large construction groups already use advanced risk analysis, CPM, BIM, 4D planning or digital-twin systems.

Ask yourself:
- What does this demo do that I can show live in under three minutes?
- Which values are invented assumptions?
- What would we need from a real project team before calling this useful?
- When would the prototype's answer be wrong or incomplete?

Optional CSV demo: click “Load sample”, then “Validate & load”. Choose PR-01 and test 14, 15 and 16 days. Explain that this endpoint accepts a documented CSV schema only; it does not read native Primavera XER/XML, and imported data is not treated as validated project truth.

## The pitch to practise

“Project Impact Lab tests one project-controls question: when a construction activity is delayed, is the delay still within schedule float, or is it starting to threaten handover? I built a small explainable scenario workflow. It recalculates a dependency network, shows remaining float and critical paths, and compares a few assumed recovery actions. The sample schedule and costs are synthetic. The next step would be to test whether this workflow adds value against the company's existing scheduling process using approved data.”

## Three-minute demo sequence

1. Open the live preview: https://project-impact-lab.vercel.app/
2. Use **Procurement +14d · 1d left**. Handover stays at Day 119, but float falls from 15 days to 1 day.
3. Click **Procurement +15d · zero float**: procurement becomes co-critical with structure/facade, while handover still remains Day 119.
4. Click **Procurement +16d · handover +1d**: modeled handover moves to Day 120.
5. Click **Recalculate impact** after changing a value. Point out that the dashboard reports modeled output, not a prediction about Prestige.
6. Switch to **Structure +14d · recovery case** to compare an assumed recovery action. State that the ₹19 lakh figure is an illustrative calculation, not a saving claim.

## Questions you should be able to answer

**“Where is the AI?”**  
“This version's core scheduling is deterministic CPM, not trained AI. I used AI-assisted coding to build the prototype. To justify a predictive model, we would need approved historical schedule data and evidence that ML improves over a transparent baseline.”

**“Isn't this already in Primavera?”**  
“Primavera already supports CPM, total float and multiple float paths. I am not claiming to replace it. The hypothesis is that a small, explicit delay-to-action explanation may be useful in a particular workflow. We would need to compare it with the team's current tools to find out.”

**“Where did the ₹4.5 lakh per day come from?”**  
“It is a placeholder chosen for the demo, not a Prestige metric. A real value estimate needs project controls and finance to define approved cost inputs and avoid double-counting.”

**“What is not modeled?”**  
“Working calendars, lags, resource constraints, actual site conditions, contractual obligations, uncertainty and live project data. Those omissions mean it is not production scheduling software.”

**“How much code did you write yourself?”**  
Be honest. If you used AI tools to generate or revise the code, say so. Explain your own work through the choices you can defend: defining a narrow decision problem, researching the existing market, examining the algorithm, running tests and understanding the limitations. Do not claim manual authorship of code you did not write.

## Final self-test before the interview

Without reading your notes, explain in plain language:
1. The problem in 45 seconds.
2. The difference between frontend and backend in 20 seconds.
3. The 14 / 15 / 16-day procurement example in 60 seconds.
4. The cost formula in 20 seconds.
5. Two limitations and one way to validate the concept in 40 seconds.

If you cannot explain one of these, reread that section instead of adding another feature.
