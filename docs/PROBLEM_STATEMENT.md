# Problem Statement — Project Impact Lab

## Working title

**Float-Burn Watch: a small, explainable delay-to-decision rehearsal**

This is the focused workflow inside Project Impact Lab. The title describes what the prototype does; it is not a claim that the capability is globally unique.

## The problem in one sentence

**A construction activity can be delayed without moving handover straight away, because it still has schedule float; the important question is how much of that buffer has been used, when the activity becomes critical, and whether a recovery action is worth considering.**

## Interview-ready version (about 45–60 seconds)

“On a construction project, activities depend on one another. Some activities have spare time, called total float, so a short delay may be absorbed without changing the handover date. But as that buffer is used up, another workstream can become critical and a further delay can move handover.

I built Project Impact Lab to make that threshold visible. A project-controls user chooses an activity, adds a hypothetical delay, sees the change in total float and handover, and compares a few possible recovery actions using explicit cost assumptions. The demo uses invented data, so it shows how the decision works, not what Prestige will save. I want to test whether this simple, explainable workflow adds value alongside the tools a project team already uses.”

## Who has the problem?

A project manager or project-controls engineer reviewing a schedule update and deciding where to investigate first.

## When does it arise?

An update reports that a package—such as long-lead procurement—is behind plan. That does not automatically mean handover is late. The activity may still have float. But a shrinking float buffer is a warning that the delay is approaching the point where it could control a milestone.

## The one decision this prototype tests

**“Is this delay still inside the available buffer, or has it reached the point where handover is at risk—and what recovery option should we examine first?”**

The prototype models one disruption at a time. It does not know whether a real intervention is safe, contractually allowed, staffed or achievable; a real project lead must confirm those facts.

## Concrete synthetic example

The built-in example has an original project finish on Day 119. The procurement activity has 15 days of modeled total float.

| Procurement delay injected | Modeled handover | Procurement float after the delay | Interpretation |
|---:|---:|---:|---|
| 14 days | Day 119 | 1 day | Handover does not move yet; almost all buffer is consumed. |
| 15 days | Day 119 | 0 days | The procurement/MEP route becomes co-critical with the structure/facade route. |
| 16 days | Day 120 | 0 days | The delay exceeds the original float; modeled handover slips by 1 day. |

These are deterministic calculations on an invented eight-activity network with simplified finish-to-start links. They are not Prestige project data, calibrated forecasts or observed savings.

## How the application works

1. **Choose an activity and delay.** The user changes one activity's duration by a specified number of days.
2. **Recalculate the schedule.** The engine validates the links, orders tasks by dependency, then performs Critical Path Method (CPM) forward and backward passes.
3. **Explain the impact.** It shows modeled handover, activity total float, critical paths and a short message explaining whether float remains or the finish date moves. One-click presets let the user compare 14-, 15- and 16-day delays without manually adjusting controls.
4. **Compare hypothetical actions.** It applies one assumed recovery action at a time and compares schedule days recovered against an editable illustrative cost exposure. A project team must validate the feasibility and costs before acting.

## Why this is relevant to large construction organisations

- Autodesk Construction IQ already uses machine learning to help teams prioritise construction risks, including issues related to cost, schedule, quality and safety.
- Oracle Primavera Cloud already calculates critical paths, total float and multiple critical/sub-critical float paths.
- Bentley's infrastructure and construction portfolio connects engineering data, 4D planning, project progress, field information and digital twins.
- China State Construction describes industrial software, smart factories and intelligent construction-site systems as parts of its intelligent-construction work.
- China Communications Construction Company has described an IoT-enabled digital-twin platform used as a management decision tool on a reservoir project.

These examples show that advanced construction technology is already a mature and competitive area. They do **not** establish that Prestige has a missing feature or that the small prototype outperforms commercial platforms.

## What might be different about this prototype?

The proposal is deliberately narrow: put **float consumed → path becomes critical → potential handover effect → cost-assumption comparison** in one simple, inspectable teaching/demo workflow. A user can see the exact input that changed the result rather than treating a risk score as an answer.

This is a prototype-level product hypothesis, not a claim of exclusive capability. Oracle Primavera Cloud already provides multiple float paths, so our basic CPM and near-critical-path logic are established practice, not novel research.

## Prestige context: how to use the research responsibly

April 2026 trade-press coverage reported a three-year Prestige Group–Autodesk collaboration and described a connected design-to-execution environment, including 4D/5D workflows. This is relevant context, but the report is secondary coverage and does not reveal Prestige's internal project-controls process or prove a gap. Say that you read the coverage and ask how the interviewer's team currently handles float erosion and near-critical paths. Do not suggest the company lacks these capabilities.

The hypothesis is not "Prestige needs a new CPM tool." It is: **can this short, visual 14/15/16-day threshold demonstration help a user explain float burn quickly and consistently alongside existing scheduling software?** If their current system already does this well, the prototype has not demonstrated additional value.

## What evidence could prove or disprove the idea?

A controlled pilot would need an approved historical schedule and agreed action/cost assumptions. Compare the workflow with the team's existing scheduling process and ask project-controls users to complete the same delay-triage tasks. Measure whether it helps them identify the controlling path, notice float erosion sooner, explain the reason for a recommendation, and choose an appropriate follow-up faster or more consistently.

The hypothesis is disproved if the existing workflow already communicates these details just as clearly and the prototype does not improve decision quality, time-to-understand, or auditability.

## Explicit non-goals

- Predicting real delays with trained AI/ML.
- Claiming savings or probabilities from synthetic calculations.
- Replacing Autodesk, Primavera, BIM, project managers or site engineers.
- Integrating with Prestige systems or using company data without written permission.
- Modeling work calendars, relationship lags, constrained resources, contract terms, site safety, weather uncertainty or all real-world construction conditions.

## Sources reviewed (accessed 9 October 2026)

1. Autodesk, Construction IQ: https://help.autodesk.com/cloudhelp/ENG/Docs-Insight/files/Insight_Construction_IQ.html
2. Autodesk Forma, Construction IQ product overview: https://construction.autodesk.com/tools/construction-iq/
3. Oracle Primavera Cloud, Scheduling Overview: https://primavera.oraclecloud.com/help/en/user/88251.htm
4. Oracle Primavera Cloud, Schedule a Project / multiple float paths: https://primavera.oraclecloud.com/help/en/user/88257.htm
5. U.S. Government Accountability Office, *Schedule Assessment Guide: Best Practices for Project Schedules* (GAO-16-89G), published 22 December 2015; highlights the need to identify near-critical paths: https://www.gao.gov/products/gao-16-89g
6. Bentley Infrastructure Cloud, 4D planning, project delivery data and digital twins: https://www.bentley.com/products/bentley-infrastructure-cloud
7. China State Construction Engineering Corporation, Intelligent Construction: https://en.cscec.com/english_cscec/ChineseConstruction/PromotingChinabuilt/IntelligentConstruction/
8. China Communications Construction Company, “Smart construction: Digital twin technology drives modern management systems,” published 28 February 2025: https://en.ccccltd.cn/xwzx/ztbd/202502/t20250228_219358.html
9. China National Railway Administration, 2026 technical standard for railway construction management information models and end-to-end BIM application (Chinese): https://source.nra.gov.cn/xwzx/xwxx/gdxw/202605/t20260508_351199.shtml
10. Prestige / Autodesk collaboration, as reported by First Construction Council (secondary source), 14 April 2026: https://firstconstructioncouncil.com/article/915057
11. Autodesk official announcement: Autodesk Construction Cloud becomes Autodesk Forma, 24 March 2026: https://adsknews.autodesk.com/en/news/autodesk-construction-cloud-is-now-autodesk-forma/
12. China State Construction Engineering Corporation, 2026 intelligent construction showcase: https://en.cscec.com/english_cscec/CompanyNews/CorporateNews/202609/3961316.html

## How to talk about using AI

Be transparent: “I used AI as a coding assistant to accelerate a working prototype. I defined and narrowed the scenario, reviewed how the schedule logic should work, and tested edge cases such as float exhaustion and tied critical paths. I am treating this as a proof of concept, not pretending it is a production AI model.”

Only say you reviewed or tested something after you have worked through it yourself. The six-hour learning guide is designed to prepare you to explain the main code paths and assumptions.
