# Competitive Research — What This Project Should and Should Not Claim

**Research review date: 9 October 2026. This is a product-positioning note, not a comprehensive market census.**

## Established capabilities found in primary sources

| Organisation / product | Publicly documented capability | Implication for Project Impact Lab |
|---|---|---|
| Autodesk Construction IQ / Autodesk Forma | Applies analytics and machine learning to help prioritise project, subcontractor, design, RFI, quality and safety risks. | Do not pitch a generic AI risk dashboard as the innovation. |
| Oracle Primavera Cloud | CPM forward/backward passes, total float, critical path and multiple critical/sub-critical float paths. | CPM and near-critical paths are established functions, not unique inventions. |
| Bentley Infrastructure Cloud / SYNCHRO | Connects engineering/construction data, 4D scheduling, project progress, field information and digital twins. | Do not pretend a small HTML dashboard competes with an enterprise digital-twin stack. |
| China State Construction Engineering Corporation (CSCEC) | Publicly describes intelligent construction, industrial software, smart factories and intelligentised construction sites. Its 2024 website figures list about RMB 4.5 trillion in new contract amount and about RMB 2.19 trillion in business income. | Large Chinese contractors are building integrated software/hardware and lifecycle capabilities; the sensible prototype scope must be much narrower. |
| China Communications Construction Company (CCCC) | Described an IoT-enabled digital-twin management decision platform on the Zaodu Reservoir project, including water/rainfall forecasting and early warnings. | Digital twins, IoT and forecast-driven site decision support already exist in real projects. |
| China National Railway Administration | In May 2026, published a railway-construction BIM information-model application standard covering project data organisation, model creation, platform integration and digital delivery. | Lifecycle interoperability and data governance are important; the prototype cannot claim to solve them without schedule import/integration. |

## The hypothesis we can test

A user who is not spending the day inside a scheduling tool could benefit from a small, transparent walkthrough that links:

**Delay reported → float consumed → path becomes critical → handover effect → possible recovery action and assumptions.**

This is not a proven market gap. It is a proposed user experience that needs to be compared with the actual workflow of the project-controls team.

## How it compares to conventional alternatives

- **Spreadsheet:** inexpensive and flexible, but the user must calculate/maintain the dependency logic and explain thresholds manually.
- **Primavera or another schedule system:** more mature and broader. This prototype should not attempt to replace those systems; its potential value is a focused demonstration and explanation layer.
- **Autodesk Construction IQ:** focuses on ML/analytics-driven risk prioritisation. Our current engine does not predict risk from real data; it runs deterministic what-if schedule scenarios.
- **Digital twin / 4D platform:** integrates models, time and potentially site progress. Our prototype has no 3D/4D model, site telemetry or live integration.

## What would disprove our value hypothesis?

If a project-controls user can already identify the same near-critical buffer, understand the future handover effect, and compare recovery alternatives just as quickly and clearly in their current system, then Project Impact Lab adds little value. That is a valid outcome; we should not build functionality merely to keep the idea alive.

## Primary sources (accessed 9 October 2026)

- Autodesk Construction IQ documentation: https://help.autodesk.com/cloudhelp/ENG/Docs-Insight/files/Insight_Construction_IQ.html
- Autodesk Forma Construction IQ product overview: https://construction.autodesk.com/tools/construction-iq/
- Oracle Primavera Cloud Scheduling Overview: https://primavera.oraclecloud.com/help/en/user/88251.htm
- Oracle Primavera Cloud Schedule a Project / multiple float paths: https://primavera.oraclecloud.com/help/en/user/88257.htm
- Bentley Infrastructure Cloud: https://www.bentley.com/products/bentley-infrastructure-cloud
- CSCEC English site and 2024 corporate figures: https://en.cscec.com/
- CSCEC Intelligent Construction: https://en.cscec.com/english_cscec/ChineseConstruction/PromotingChinabuilt/IntelligentConstruction/
- CCCC smart-construction digital twin article, 28 February 2025: https://en.ccccltd.cn/xwzx/ztbd/202502/t20250228_219358.html
- China National Railway Administration BIM model application standard, 8 May 2026 (Chinese): https://source.nra.gov.cn/xwzx/xwxx/gdxw/202605/t20260508_351199.shtml
- U.S. GAO, Schedule Assessment Guide (GAO-16-89G), 22 December 2015: https://www.gao.gov/products/gao-16-89g
