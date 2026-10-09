# Competitive Research — What This Project Should and Should Not Claim

**Research review date: 9 October 2026. This is a product-positioning note, not a comprehensive market census.**

## Established capabilities found in primary sources

| Organisation / product | Publicly documented capability | Implication for Project Impact Lab |
|---|---|---|
| Autodesk Construction IQ / Autodesk Forma | Applies analytics and machine learning to help prioritise project, subcontractor, design, RFI, quality and safety risks. | Do not pitch a generic AI risk dashboard as the innovation. |
| Oracle Primavera Cloud | CPM forward/backward passes, total float, critical and sub-critical float paths; risk response actions can be tracked and prioritised using score improvement, response effectiveness, finish impact and cost impact. | Both the scheduling algorithm and much of the response-action comparison exist in mature products. Do not claim feature-level novelty; position this as a narrow, easy-to-demo explanation workflow. |
| Bentley Infrastructure Cloud / SYNCHRO | Connects engineering/construction data, 4D scheduling, project progress, field information and digital twins. | Do not pretend a small HTML dashboard competes with an enterprise digital-twin stack. |
| China State Construction Engineering Corporation (CSCEC) | Publicly describes intelligent construction, industrial software, smart factories and intelligentised construction sites. Its 2024 website figures list about RMB 4.5 trillion in new contract amount and about RMB 2.19 trillion in business income. | Large Chinese contractors are building integrated software/hardware and lifecycle capabilities; the sensible prototype scope must be much narrower. |
| China Communications Construction Company (CCCC) | Described an IoT-enabled digital-twin management decision platform on the Zaodu Reservoir project, including water/rainfall forecasting and early warnings. | Digital twins, IoT and forecast-driven site decision support already exist in real projects. |
| China National Railway Administration | In May 2026, published a railway-construction BIM information-model application standard covering project data organisation, model creation, platform integration and digital delivery. | Lifecycle interoperability and data governance are important; the prototype cannot claim to solve them without schedule import/integration. |

## Prestige-specific context — state this carefully

April 2026 trade-press coverage reported a three-year strategic enterprise collaboration between Prestige Group and Autodesk. The reports describe adoption of Autodesk Forma (the construction cloud is now branded as part of Forma), the AEC Collection, and a broader connected design-to-execution environment with 4D/5D workflows. Relevant coverage: [First Construction Council, 14 April 2026](https://firstconstructioncouncil.com/article/915057) and [Commercial Design India, 13 April 2026](https://www.commercialdesignindia.com/insights/prestige-group-is-set-to-partner-with-autodesk-to-enhance-design-led-digital-transformation). Autodesk's own [March 2026 announcement](https://adsknews.autodesk.com/en/news/autodesk-construction-cloud-is-now-autodesk-forma/) confirms the product-brand transition from Autodesk Construction Cloud to Autodesk Forma.

These Prestige-specific details are **secondary-source reporting**, not confirmation of Prestige's internal workflow or a first-party statement about any missing capability. I did not locate an official company-hosted source in the searches used for this note. In the interview, say "I read industry coverage reporting..." and ask the interviewer what tools and workflows their team actually uses. Do not assert that Prestige lacks float analysis or needs a new risk platform.

**Implication for this prototype:** describe it as a small learning / decision-explanation experiment that could sit alongside an existing system if a user finds it useful. Never pitch it as a replacement for the Autodesk ecosystem, Primavera, or project-controls professionals.

## Lessons from large Chinese construction and infrastructure organisations

- **China State Construction Engineering Corporation (CSCEC):** its official 2026 technology-exhibition article describes examples including 5G smart tower cranes, digital monitoring equipment, tethered drones, a BIM+GIS project-management platform, and a digital-tunnel platform used to track hazards and support project management. This demonstrates the breadth of smart-site and integrated project-control work already underway, rather than proving an unserved need for a small schedule dashboard. [CSCEC, September 2026](https://en.cscec.com/english_cscec/CompanyNews/CorporateNews/202609/3961316.html).
- **China Communications Construction Company (CCCC):** its official report describes an IoT-enabled digital twin for the Zaodu Reservoir project, combining water/rainfall forecasting with early warnings to support construction decisions. [CCCC, 28 February 2025](https://en.ccccltd.cn/xwzx/ztbd/202502/t20250228_219358.html).
- **China's railway construction research:** a peer-reviewed paper describes a wider system spanning BIM standards, BIM+GIS lifecycle management, IoT perception, cloud/big-data construction management and intelligent machinery. It is a 2019 overview, not proof that every listed system is in use on every project. [Lu et al., *Frontiers of Engineering Management*, 2019](https://journal.hep.com.cn/fem/EN/10.1007/s42524-019-0073-9).

These examples are benchmarks for ambition and integration—not templates to copy into a six-hour student demo. The sensible choice here is to make one small decision easy to inspect and defend.

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
- Oracle Primavera Cloud response-action prioritisation: https://primavera.oraclecloud.com/help/en/user/278357.htm
- Prestige / Autodesk partnership coverage (secondary reporting): https://firstconstructioncouncil.com/article/915057 ; https://www.commercialdesignindia.com/insights/prestige-group-is-set-to-partner-with-autodesk-to-enhance-design-led-digital-transformation
- Autodesk official rebrand announcement, 24 March 2026: https://adsknews.autodesk.com/en/news/autodesk-construction-cloud-is-now-autodesk-forma/
- CSCEC smart-construction technologies shown in September 2026: https://en.cscec.com/english_cscec/CompanyNews/CorporateNews/202609/3961316.html
- Bentley Infrastructure Cloud: https://www.bentley.com/products/bentley-infrastructure-cloud
- CSCEC English site and 2024 corporate figures: https://en.cscec.com/
- CSCEC Intelligent Construction: https://en.cscec.com/english_cscec/ChineseConstruction/PromotingChinabuilt/IntelligentConstruction/
- CCCC smart-construction digital twin article, 28 February 2025: https://en.ccccltd.cn/xwzx/ztbd/202502/t20250228_219358.html
- China National Railway Administration BIM model application standard, 8 May 2026 (Chinese): https://source.nra.gov.cn/xwzx/xwxx/gdxw/202605/t20260508_351199.shtml
- U.S. GAO, Schedule Assessment Guide (GAO-16-89G), 22 December 2015: https://www.gao.gov/products/gao-16-89g
