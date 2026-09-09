# R02 — Usability & Interaction Benchmark Model

- **Research ID:** R02
- **Version:** 1.0.0
- **Date:** 2026-09-09
- **Issue:** #5
- **Repository:** `Creynox/software-quality-benchmark`
- **Governing methodology:** `research/R00-research-methodology/R00-research-methodology.md`
- **Depends on:** `research/R01-quality-model/R01-generic-software-quality-model.md`
- **Research type:** standards-led structured review with measurement-boundary analysis
- **Status:** COMPLETE

## 1. Question / objective

Define the generic usability and interaction evaluation model that the Software Quality Benchmark Framework (SQBF) should use for software products, especially for AI-driven black-box evaluation of real user tasks.

R02 answers:

1. What exactly should be measured under usability and interaction quality?
2. How should product interaction properties be separated from actual task outcomes in context of use?
3. Which aspects can an AI computer-use evaluator observe directly, and which require human participants?
4. How should discoverability, navigation, comprehensibility, learnability, error handling, help, control, feedback and consistency be represented without double-counting?
5. How should information-heavy surfaces such as dashboards, analytics, reports and decision-support screens be tested?
6. How should novice, trained and experienced use differ at the test-design level without making role-specific assumptions in the generic core?
7. Which task/scenario families should later project profiles instantiate?
8. Which raw observations should be collected now even though their score normalization belongs to R03/R04?
9. What belongs to R07 accessibility rather than general usability?
10. What must be deferred to human validation because an AI evaluator cannot validly self-report human satisfaction, confidence, trust or workload?

The purpose is a **generic evaluation contract**. R02 does not define final 0–100 weights or thresholds.

---

## 2. Scope

R02 covers:

- usability as an outcome of use;
- interaction design principles;
- navigation and information presentation;
- task effectiveness and false-success detection;
- discoverability and orientation;
- comprehensibility and information interpretation;
- conformity with user expectations and consistency;
- controllability and flexibility;
- use-error avoidance, tolerance and recovery;
- learnability and repeat-use behaviour;
- in-product help, guidance, training and assistance;
- observable interaction efficiency signals such as unnecessary steps, backtracking and rework;
- AI-observable versus human-subjective measures;
- generic scenario families for benchmark design;
- reporting/evidence expectations for usability evaluations;
- boundaries with R03 time/performance, R05 AI evaluator reproducibility, R07 accessibility/reliability and R08 persona/scenario modelling.

---

## 3. Explicitly out of scope

R02 does **not** define:

- final score weights;
- 0–100 normalization formulas;
- pass/fail thresholds;
- task-time normalization or performance targets;
- statistical aggregation across repeated runs;
- AI evaluator calibration/repeatability rules;
- detailed WCAG conformance testing;
- detailed reliability/resilience testing beyond use-error recovery;
- detailed security controls;
- BLE-specific personas, tasks, routes or terminology;
- human-study sample-size planning;
- final adoption of SUS, UMUX-LITE, SEQ or NASA-TLX for human studies;
- benchmark runner implementation;
- future dashboard/web-application implementation.

---

## 4. Research protocol

### 4.1 Expected source families

R02 required coverage of:

1. current ISO usability definitions and context-of-use concepts;
2. current ISO interaction principles;
3. current ISO information-presentation/navigation guidance;
4. current ISO usability-evaluation reporting guidance;
5. current ISO context-of-use and user-needs reporting standards;
6. quality-in-use boundary from ISO/IEC 25019;
7. established public-sector usability benchmarking guidance;
8. established specialist heuristic guidance for complementary diagnostic categories;
9. human-subjective instruments only to establish the boundary between AI-observable and human-only constructs;
10. accessibility/usability boundary guidance.

### 4.2 Search terms / repositories / standards bodies

Primary discovery was performed against ISO, W3C/WAI, GOV.UK Service Manual, NASA and scholarly/ACM-indexed sources. Specialist guidance from Nielsen Norman Group was used as non-normative diagnostic support.

Representative queries:

- `ISO 9241-11:2018 usability effectiveness efficiency satisfaction context of use`
- `ISO 9241-110:2020 interaction principles`
- `ISO 9241-115:2024 navigation design`
- `ISO 9241-112:2025 presentation of information`
- `ISO 25062:2025 usability evaluation report`
- `ISO TR 25060:2023 usability related information`
- `ISO IEC 25063 context of use description`
- `ISO IEC 25064 user needs report`
- `ISO IEC 25019 quality in use usability acceptability`
- `GOV.UK usability benchmarking task success time false success`
- `Nielsen usability heuristics system status error prevention recognition recall help`
- `NASA TLX subjective workload`
- `System Usability Scale SUS`
- `UMUX-LITE CHI`
- `single ease question post-task usability`
- `accessibility usability inclusion W3C`

### 4.3 Inclusion rules

Included sources had to satisfy one or more of the following:

- current published standard or official standard-family guidance;
- official government/public-sector usability benchmark guidance;
- official instrument owner/source for subjective human measures;
- peer-reviewed or well-established methodological publication;
- established specialist guidance with explicit non-normative status.

### 4.4 Exclusion rules

Excluded from authoritative use:

- generic UX blogs without methodology;
- AI-generated summaries of standards;
- obsolete ISO editions when a current edition exists, except for version-history context;
- full copyrighted standards text not licensed for AI use;
- claims that subjective human states can be validly measured by asking an AI agent to pretend to feel them;
- arbitrary click-count, time or task-success thresholds without empirical/project baseline support.

### 4.5 Data to extract

For each relevant source:

- construct being defined;
- whether the construct is product property, outcome of use or subjective perception;
- context-of-use dependency;
- task/goal dependency;
- evaluation/reporting implications;
- observable raw signals;
- human-only signals;
- overlap with other dimensions;
- current/withdrawn/draft status;
- downstream owner (R03/R04/R05/R07/R08).

### 4.6 Synthesis method

The synthesis used four layers:

1. **Outcome layer** — what happened when a specified user attempted a specified goal/task in a specified context;
2. **Interaction-property layer** — observable properties of the user-system interaction that plausibly contributed to the outcome;
3. **Subjective-human layer** — perceptions/responses that require real humans;
4. **Diagnostic scenario layer** — reusable task families for finding why a system succeeds or fails.

This avoids flattening every UX observation into one score and prevents double-counting the same failure under several labels.

---

## 5. Search log

| Date | Source/database/site | Query / action | Result / note |
|---|---|---|---|
| 2026-09-09 | ISO | ISO 9241-11:2018 | Current usability definitions standard confirmed; usability treated as outcome of use |
| 2026-09-09 | ISO | ISO 9241-110:2020 | Current interaction-principles standard confirmed in 2025 |
| 2026-09-09 | ISO | ISO 9241-115:2024 | Current conceptual/UI/navigation design guidance found |
| 2026-09-09 | ISO | ISO 9241-112 | 2017 edition found withdrawn; 2025 edition found current |
| 2026-09-09 | ISO | ISO 25062 | 2006 edition withdrawn; ISO 25062:2025 is current usability-evaluation reporting standard |
| 2026-09-09 | ISO | ISO/TR 25060:2023 | Current CIF framework for usability-related information found |
| 2026-09-09 | ISO | ISO/IEC 25063 | 2014 edition still current but revision/FDIS in progress; version status recorded |
| 2026-09-09 | ISO | ISO/IEC 25064:2013 | User-needs reporting standard found |
| 2026-09-09 | ISO | ISO/IEC 25019:2023 | Quality-in-use model/context dependency confirmed |
| 2026-09-09 | GOV.UK | usability benchmarking | Task success, task time, abandonment and false-success guidance found |
| 2026-09-09 | GOV.UK | make service simple to use | First-time success/minimum-help principle found as public-sector guidance |
| 2026-09-09 | NN/g | 10 usability heuristics | Complementary diagnostic heuristic set reviewed; explicitly non-normative |
| 2026-09-09 | W3C WAI | accessibility usability inclusion | Overlap and distinction between accessibility and usability documented |
| 2026-09-09 | NASA | NASA-TLX | Official source confirms subjective workload nature |
| 2026-09-09 | ACM / CHI | UMUX-LITE | Human subjective questionnaire evidence located |
| 2026-09-09 | CHI / Sauro-Dumas | one-question post-task questionnaires | Evidence found that post-task ease/difficulty ratings are human subjective measures |
| 2026-09-09 | SUS literature | System Usability Scale | Human post-study subjective usability instrument identified for later human phase |

### 5.1 Counter-evidence / alternative-model search

The research explicitly checked for the following risks:

- treating usability as a static UI property rather than an outcome in context;
- treating heuristic compliance as equivalent to task success;
- treating quality in use as synonymous with usability;
- treating AI-generated subjective ratings as equivalent to human ratings;
- counting accessibility only as generic usability;
- assuming click count alone represents efficiency;
- assuming one successful task proves discoverability, comprehension or learnability;
- assuming a successful end state is valid when the evaluator only *believes* it succeeded.

These risks materially affected the adopted model.

---

## 6. Source register

| ID | Source | Class | Version/status | Applicability | AI/copyright note | Used for |
|---|---|---|---|---|---|---|
| S01 | ISO 9241-11:2018, *Usability: Definitions and concepts* — https://www.iso.org/standard/63500.html | NORMATIVE_STANDARD | CURRENT / CONFIRMED 2023 | DIRECT | Use official abstract/metadata only; ISO AI/copyright restrictions apply | usability as outcome, context of use, effectiveness/efficiency/satisfaction boundary |
| S02 | ISO 9241-110:2020, *Interaction principles* — https://www.iso.org/standard/75258.html | NORMATIVE_STANDARD | CURRENT / CONFIRMED 2025 | DIRECT | Official metadata/abstract; detailed principle names corroborated from public standard previews/secondary sources, no full-text ingestion | interaction-property taxonomy |
| S03 | ISO 9241-115:2024, *Conceptual design, user-system interaction, UI and navigation design* — https://www.iso.org/standard/80773.html | NORMATIVE_STANDARD | CURRENT / PUBLISHED | DIRECT | Official abstract/OBP public preview only | navigation, information architecture, UI design boundary |
| S04 | ISO 9241-112:2025, *Principles for presentation of information* — https://www.iso.org/standard/87518.html | NORMATIVE_STANDARD | CURRENT / PUBLISHED | DIRECT | Official abstract only | perception/understanding of presented information |
| S05 | ISO 9241-210:2019, *Human-centred design for interactive systems* — https://www.iso.org/standard/77520.html | NORMATIVE_STANDARD | CURRENT | DIRECT | Official abstract only | user/context-driven design process boundary |
| S06 | ISO/TR 25060:2023, *CIF framework for usability-related information* — https://www.iso.org/standard/83763.html | OFFICIAL_TECHNICAL_REPORT | CURRENT / PUBLISHED | DIRECT | Public abstract/OBP terms used; ISO restrictions apply | systematic documentation of context, needs, requirements and evaluations |
| S07 | ISO 25062:2025, *CIF for reporting usability evaluations* — https://www.iso.org/standard/84255.html | NORMATIVE_STANDARD | CURRENT / PUBLISHED | DIRECT | Official abstract only | structured evaluation-report requirement and predefined-task scope |
| S08 | ISO/IEC 25063:2014, *Context of use description* — https://www.iso.org/standard/35789.html | NORMATIVE_STANDARD | CURRENT BUT REVISION/FDIS IN PROGRESS | DIRECT | Official abstract/OBP; revision status recorded | users, goals, tasks, environment, resources/context |
| S09 | ISO/IEC 25064:2013, *User needs report* — https://www.iso.org/standard/35790.html | NORMATIVE_STANDARD | CURRENT / PUBLISHED | DIRECT | Official abstract only | user-needs evidence and consolidation |
| S10 | ISO/IEC 25019:2023, *Quality-in-use model* — https://www.iso.org/standard/78177.html | NORMATIVE_STANDARD | CURRENT / PUBLISHED | DIRECT | Official abstract only | outcome/context boundary beyond usability |
| S11 | GOV.UK Service Manual, *Usability benchmarking a website or whole service* — https://www.gov.uk/service-manual/measuring-success/usability-benchmarking-a-website-or-whole-service | OFFICIAL_GUIDANCE | CURRENT WEB GUIDANCE | DIRECT | Open Government Licence unless stated | repeatable task benchmarks, success/time/abandonment/false success |
| S12 | GOV.UK Service Standard, *Make the service simple to use* — https://www.gov.uk/service-manual/service-standard/point-4-make-the-service-simple-to-use | OFFICIAL_GUIDANCE | CURRENT WEB GUIDANCE | DIRECT | Open Government Licence unless stated | first-time success/minimum-help orientation |
| S13 | Nielsen Norman Group, *10 Usability Heuristics for User Interface Design* — https://www.nngroup.com/articles/ten-usability-heuristics/ | SPECIALIST_GUIDANCE | REVIEWED 2024 | SUPPORTING | Public article, no normative authority | system status, user language, control, consistency, error prevention/recovery, recognition, help |
| S14 | W3C WAI, *Accessibility, Usability, and Inclusion* — https://www.w3.org/WAI/fundamentals/accessibility-usability-inclusion/ | OFFICIAL_GUIDANCE | CURRENT WEB GUIDANCE | DIRECT FOR BOUNDARY | Public W3C guidance | usability/accessibility overlap and separation |
| S15 | NASA, *NASA Task Load Index (TLX)* — https://www.nasa.gov/human-systems-integration-division/nasa-task-load-index-tlx/ | OFFICIAL_INSTRUMENT_GUIDANCE | CURRENT/HISTORICAL TOOL | HUMAN-ONLY BOUNDARY | NASA states tool available for use; instrument is subjective | workload cannot be directly measured by AI pretending to be a human |
| S16 | Brooke (1996), *System Usability Scale* | PEER/INDUSTRY MEASUREMENT INSTRUMENT | ESTABLISHED | HUMAN-ONLY BOUNDARY | questionnaire content/licensing to be reviewed before implementation | post-study subjective usability |
| S17 | Lewis, Utesch & Maher (2013), *UMUX-LITE: when there’s no time for the SUS*, CHI, DOI 10.1145/2470654.2481287 | PEER_REVIEWED_PRIMARY | PUBLISHED | HUMAN-ONLY BOUNDARY | bibliographic use | short subjective usability measure |
| S18 | Sauro & Dumas (2009), *Comparison of three one-question, post-task usability questionnaires*, CHI, DOI 10.1145/1518701.1518946 | PEER_REVIEWED_PRIMARY | PUBLISHED | HUMAN-ONLY BOUNDARY | bibliographic use | post-task perceived ease/difficulty |

### 6.1 Source-status cautions

1. ISO 9241-112:2017 is withdrawn and replaced by ISO 9241-112:2025. R02 uses the 2025 edition as current authority.
2. ISO/IEC 25062:2006 is withdrawn and replaced by ISO 25062:2025. R02 uses the 2025 edition.
3. ISO/IEC 25063:2014 is still published but a replacement is in final-draft processing in 2026. R08 must re-check status before Foundation 1.0 freeze.
4. Detailed metric operationalization should not be inferred from publicly visible ISO abstracts. R02 uses standards for construct boundaries, not unlicensed detailed formula extraction.

---

## 7. Confirmed facts

### FACT F02-01 — Usability is an outcome in a specified context, not a context-free visual property

ISO 9241-11 states that usability is an outcome of use and frames it around specified users achieving specified goals with effectiveness, efficiency and satisfaction in a specified context of use. [S01]

**Implication:** A benchmark result without user/skill profile, goal/task and context cannot validly claim general usability.

**Confidence:** HIGH.

### FACT F02-02 — Context of use includes more than device type

ISO/IEC 25063 describes context using user/stakeholder groups and their characteristics, goals, tasks and environments. ISO/TR 25060 uses context-of-use information as a core usability information item. [S06, S08]

**Implication:** `Desktop` versus `Tablet` is only one part of context. Skill, role, environment, available resources and task are also relevant.

**Confidence:** HIGH.

### FACT F02-03 — Interaction design has general principles distinct from measured task outcomes

ISO 9241-110 provides general interaction principles for design/evaluation and is current after 2025 confirmation. Publicly corroborated principle categories include task suitability, self-descriptiveness, conformity with user expectations, learnability, controllability, robustness against use errors and user engagement. [S02]

**Implication:** SQBF should record both task outcome and the interaction-property findings that explain the outcome.

**Confidence:** HIGH for the existence/scope of the principles; HIGH for the principle names based on consistent public corroboration, while detailed normative recommendations are intentionally not reproduced.

### FACT F02-04 — Navigation and information presentation are explicit interaction-design concerns

ISO 9241-115 covers conceptual design, user-system interaction design, user-interface design and navigation design. ISO 9241-112:2025 covers presentation of information specifically for perception and understanding. [S03, S04]

**Implication:** Findability/navigation and comprehension of presented information deserve explicit benchmark treatment; they should not be hidden inside a generic “looks good” score.

**Confidence:** HIGH.

### FACT F02-05 — User needs are an input to usable-system design and evaluation

ISO/IEC 25064 specifies the collection, documentation, analysis and integration of information relevant to user needs. ISO/TR 25060 positions user-needs and context-of-use information as lifecycle information items. [S06, S09]

**Implication:** Benchmark tasks should represent real user goals rather than UI functions chosen because they are easy to test.

**Confidence:** HIGH.

### FACT F02-06 — Usability-evaluation reporting is itself standardized

ISO 25062:2025 defines a common industry format for reporting usability evaluations and supports multiple evaluation approaches for products/services used for predefined tasks. [S07]

**Implication:** SQBF reports should preserve enough context, task, method and result metadata to be auditable rather than output only a score.

**Confidence:** HIGH.

### FACT F02-07 — Task success and false success are distinct benchmark outcomes

GOV.UK’s usability benchmarking guidance explicitly recommends measuring whether a task was successfully completed, whether it was abandoned, and whether a user believed it was completed successfully when it was not. [S11]

**Implication:** SQBF needs a first-class `FALSE_SUCCESS` result, not only PASS/FAIL.

**Confidence:** HIGH for the guidance; framework adoption is a recommendation below.

### FACT F02-08 — Repeatable benchmark tasks should be realistic, stable and have clear success criteria

GOV.UK recommends tasks that are relevant/believable, representative of common user needs, have a clear correct answer and remain consistent enough for repeated benchmarking. It also recommends periodic repetition to compare improvement. [S11]

**Implication:** Scenarios must be versioned, but stable benchmark scenarios should not be casually rewritten after every UI change.

**Confidence:** HIGH.

### FACT F02-09 — Accessibility and usability overlap but are not interchangeable

W3C WAI explicitly distinguishes accessibility, usability and inclusion while noting substantial overlap. Accessibility focuses on equivalent access for people with disabilities; ordinary usability practice can fail to include those needs. [S14]

**Implication:** R02 can record general interaction barriers, but technical accessibility conformance and disability-specific coverage belong to R07.

**Confidence:** HIGH.

### FACT F02-10 — Human satisfaction and workload are subjective constructs

ISO 9241-11 includes satisfaction as part of usability. NASA explicitly defines TLX as a subjective workload assessment tool. SUS, UMUX-LITE and post-task ease instruments are questionnaires answered by human participants. [S01, S15, S16, S17, S18]

**Implication:** An AI agent cannot produce a valid human satisfaction/workload questionnaire result merely by role-playing a user.

**Confidence:** HIGH.

### FACT F02-11 — Heuristics are diagnostic guidance, not a substitute for usability outcomes

Nielsen Norman Group explicitly describes its ten heuristics as broad principles/rules of thumb. They cover system status, real-world language, control, consistency, error prevention/recovery, recognition rather than recall, efficiency and help. [S13]

**Implication:** Heuristic findings may explain failures or identify risks, but a heuristic checklist cannot replace task-success evidence.

**Confidence:** HIGH.

### FACT F02-12 — Quality in use is broader than the usability slice evaluated here

ISO/IEC 25019 defines a separate quality-in-use model with context-dependent characteristics. R01 already established that quality in use cannot be collapsed into interaction capability or ordinary usability only. [S10; R01]

**Implication:** R02 does not claim to fully measure quality in use. Risk, broader acceptability and domain benefit remain separate concerns.

**Confidence:** HIGH.

---

## 8. Derived conclusions

### INFERENCE I02-01 — SQBF needs two usability planes: `TASK OUTCOME` and `INTERACTION DIAGNOSTICS`

A benchmark that only scores design heuristics can miss whether users actually succeed. A benchmark that only records task success cannot explain why a task was difficult or fragile.

**Derived from:** F02-01, F02-03, F02-06, F02-07, F02-11.

**Conclusion:** Every task-based usability run should preserve both:

- **Outcome evidence**: what happened;
- **Interaction diagnostic evidence**: what properties of the interaction contributed.

**Confidence:** HIGH.

### INFERENCE I02-02 — `FALSE_SUCCESS` must be treated as more severe than an ordinary failed attempt in many domains

If a user fails and knows they failed, recovery can begin. If the system/user believes success occurred when the required outcome was not achieved, incorrect decisions or missing work can propagate.

**Derived from:** F02-07 and general safety/data-integrity reasoning from R01.

**Conclusion:** `FALSE_SUCCESS` is a separate raw outcome and a candidate hard-gate trigger when a project profile marks the task/result as critical.

**Confidence:** HIGH for separation; project-specific severity remains OPEN until R04/R09.

### INFERENCE I02-03 — Discoverability is not the same as task completion

A user can complete a task after searching, guessing, backtracking or using help. That task may technically PASS while the interface still has a findability problem.

**Derived from:** F02-03, F02-04, F02-11.

**Conclusion:** SQBF should record discoverability/orientation separately from final completion.

**Confidence:** HIGH.

### INFERENCE I02-04 — Comprehension must be tested with questions about meaning, not only by observing clicks

Information-heavy enterprise software can allow users to navigate successfully while misunderstanding the displayed status, trend, scope or recommended action. ISO 9241-112 explicitly makes perception/understanding part of information presentation quality.

**Derived from:** F02-04.

**Conclusion:** SQBF needs dedicated `INFORMATION_COMPREHENSION` scenarios where the evaluator must state what the UI means, what is current/historical, what requires action, and which context the information belongs to.

**Confidence:** HIGH.

### INFERENCE I02-05 — “AI usability” must not counterfeit human subjective ratings

An AI evaluator can observe visible UI, attempt tasks, count steps, detect confusion through its own action path and answer comprehension questions. It cannot authentically experience satisfaction, frustration, confidence, workload or trust as a human user.

**Derived from:** F02-10 plus R00’s evidence rule.

**Conclusion:** SQBF must tag measures as `AI_OBSERVABLE`, `HUMAN_SUBJECTIVE`, or `HYBRID/VALIDATION_REQUIRED`. AI may make an expert diagnostic judgement about signals associated with trust or workload, but it must not label that result as a human SUS/SEQ/TLX response.

**Confidence:** HIGH.

### INFERENCE I02-06 — Help use is not automatically a failure

ISO 9241-110 includes learning/support principles; interactive-system definitions in the usability family include documentation, online/human help, support and training as relevant system elements. A novice user may legitimately use integrated help as part of successful operation.

**Derived from:** F02-03, F02-05 and S06.

**Conclusion:** Benchmarks need at least two assistance conditions later formalized in R08:

- **UNAIDED**: measure how far the UI itself carries the user;
- **ASSISTED**: allow product-integrated help/training/search and measure whether it resolves the knowledge gap.

Using product help is evidence, not automatic failure. Requiring external support may be scored differently by the project profile.

**Confidence:** HIGH.

### INFERENCE I02-07 — Learnability requires repeated exposure, not a one-time first-use rating

A single first-use run can reveal discoverability but not retention or improvement with experience. Learnability includes discovery/exploration/retention concerns in ISO 9241-110.

**Derived from:** F02-03.

**Conclusion:** Learnability needs at least one repeated scenario under a stable persona/evaluator configuration; exact run count/statistics belong to R05.

**Confidence:** HIGH.

### INFERENCE I02-08 — Click count is a diagnostic raw metric, not an intrinsic usability score

A two-click flow can be confusing, risky or error-prone; a six-step regulated workflow can be appropriate if each step protects the user and the task. Task suitability requires alignment with the task, not simply minimum interactions.

**Derived from:** F02-03 and F02-01.

**Conclusion:** Clicks/interactions, navigation depth, backtracks and re-entry counts should be recorded, but R04 must not normalize them without task/context baselines.

**Confidence:** HIGH.

### INFERENCE I02-09 — Search/findability and navigation should be scenario families, not global UI-only properties

Whether something is “easy to find” depends on what the user is trying to find and what terminology/mental model they bring.

**Derived from:** F02-01, F02-02, F02-04.

**Conclusion:** Later profiles should instantiate FIND/LOCATE scenarios for important entities, records, settings and help topics rather than assigning one abstract “search score”.

**Confidence:** HIGH.

### INFERENCE I02-10 — Novice and expert usability can conflict and therefore should be observed separately

Design that maximizes explanation and guidance can slow expert users; expert shortcuts can make first-use operation harder. ISO 9241-110 includes both learnability and controllability/flexibility, and ISO 9241-11 makes users/context explicit.

**Derived from:** F02-01, F02-02, F02-03.

**Conclusion:** R08 should model experience/skill level explicitly. R02 should never average novice and expert runs into one unexplained result.

**Confidence:** HIGH.

### INFERENCE I02-11 — A usability benchmark must test negative and recovery states, not only the happy path

Use-error robustness is a core interaction concern, and real software users encounter invalid input, missing data, permissions, errors and interrupted workflows.

**Derived from:** F02-03, F02-11.

**Conclusion:** `ADVERSE_STATE / ERROR_RECOVERY` is a mandatory generic scenario family for any project where such states exist.

**Confidence:** HIGH.

### INFERENCE I02-12 — The benchmark report should preserve raw evidence even when a score is available

ISO 25062’s reporting focus and R00 traceability make a single score insufficient for auditability.

**Derived from:** F02-06 and R00.

**Conclusion:** Every scored usability result should remain traceable to scenario version, context, observed actions, completion outcome, errors, help usage and evidence snapshots/logs.

**Confidence:** HIGH.

---

## 9. Recommendations

### RECOMMENDATION R02-01 — Adopt a layered generic usability model

SQBF should use the following structure.

#### Layer A — Task outcome

Raw result states:

- `PASS_CORRECT`
- `PASS_WITH_RECOVERY`
- `PARTIAL`
- `FAIL_KNOWN`
- `FALSE_SUCCESS`
- `ABANDONED`
- `BLOCKED_BY_SYSTEM`
- `BLOCKED_BY_PERMISSION_EXPECTED`

The exact score impact is deferred to R04/project profiles.

#### Layer B — Interaction diagnostic dimensions

1. **Task Fit** — does the interaction support the real task rather than expose unnecessary system/technology complexity?
2. **Orientation & Discoverability** — can the user determine where they are, what the surface is for and where to begin/find the target?
3. **Comprehensibility & Information Clarity** — can the user interpret labels, states, values, hierarchy, scope and consequences correctly?
4. **Predictability & Consistency** — does behaviour match established expectations and remain internally coherent?
5. **Control & Flexibility** — can the user proceed, interrupt, go back, adjust or use appropriate shortcuts without losing control?
6. **Error Prevention & Recovery** — does the system prevent avoidable errors, tolerate recoverable mistakes and support recovery?
7. **Learnability & Retention** — can a new user discover how the system works and improve/retain capability across repeated use?
8. **Assistance & Guidance** — can in-product help, contextual guidance, search or training resolve uncertainty without requiring source code or external developer knowledge?
9. **Interaction Efficiency Signals** — unnecessary steps, duplicate entry, avoidable navigation, repeated work, backtracking and path complexity; timing formulas remain in R03.

#### Layer C — Human-subjective measures (future)

Reserved for real human testing:

- satisfaction;
- perceived ease/difficulty;
- confidence;
- trust;
- frustration/workload;
- overall perceived usability/acceptability.

These are **not** to be filled by AI role-play as if they were human questionnaire responses.

**Evidence basis:** F02-01 through F02-12; I02-01 through I02-12.

### RECOMMENDATION R02-02 — Make `Comprehensibility` a first-class dimension

For enterprise, analytics, compliance and management software, benchmark scenarios should test whether the evaluator correctly understands:

- page purpose;
- current scope/context;
- important status;
- whether action is required;
- meaning of key values/KPIs;
- current versus historical state;
- why an item is in warning/error state when the UI exposes the reason;
- where to drill down for evidence.

A UI that renders data correctly but leads the evaluator to an incorrect interpretation should fail the comprehension part even if navigation succeeds.

### RECOMMENDATION R02-03 — Adopt generic scenario families

R08 should formalize these schemas, but R02 proposes the following required families:

| Scenario family | Core question |
|---|---|
| `ORIENT` | Can the user tell where they are, what this is, and what matters? |
| `FIND` | Can the user locate an entity/function/information item from a realistic starting point? |
| `SINGLE_TASK` | Can the user complete one bounded task correctly? |
| `WORKFLOW` | Can the user complete an end-to-end multi-step job across surfaces? |
| `INTERPRET` | Can the user correctly explain data/status/meaning/required action? |
| `ASSIST` | Can the user resolve a knowledge gap through product-integrated help/training/search? |
| `ERROR_RECOVERY` | Can the user recover from invalid input, wrong path or system/user error? |
| `EMPTY_STATE` | Does a valid no-data state explain what it means and what can be done? |
| `DENIED_STATE` | Does lack of permission fail safely and intelligibly? |
| `REPEAT_LEARN` | Does the same user/evaluator improve or retain capability on repeated use? |
| `MULTI_TASK_SESSION` | Can the user switch between realistic tasks without losing context? |

Project profiles choose which are relevant; they do not need to execute every family for every feature.

### RECOMMENDATION R02-04 — Define a “10-second orientation” as a diagnostic scenario, not a normative threshold

For dashboards, cockpits and overview pages, a short no-action orientation test is useful:

- identify page purpose;
- active context/scope;
- primary status or risk;
- likely next action;
- whether data is current/historical/empty/error.

The literal 10 seconds is a practical benchmark convention, **not** an ISO requirement and should remain configurable until R03/R04 validates timing semantics.

### RECOMMENDATION R02-05 — Preserve observable raw metrics now, score later

R02 recommends collecting at least:

```yaml
outcome:
  status:
  correct_end_state:
  false_success:
  abandonment:
interaction:
  first_action:
  total_interactions:
  meaningful_interactions:
  unnecessary_interactions:
  navigation_transitions:
  navigation_depth_max:
  backtracks:
  dead_ends:
  repeated_actions:
  duplicate_data_entry:
  invalid_attempts:
  validation_errors:
  recovery_attempts:
  recovery_success:
assistance:
  help_opened:
  help_queries:
  training_used:
  external_help_required:
comprehension:
  page_purpose_correct:
  context_scope_correct:
  status_interpretation_correct:
  next_action_correct:
  data_meaning_correct:
learnability:
  repeat_run_id:
  previously_seen:
```

R03 adds precise time fields. R04 decides normalization/scoring. R05 defines repeated-run reliability.

### RECOMMENDATION R02-06 — Distinguish `UNAIDED`, `ASSISTED`, and later `HUMAN` evaluation modes

- **UNAIDED AI:** visible product UI only; no source code, database, repository, devtools or hidden route knowledge; product help may be disallowed except when task explicitly tests help.
- **ASSISTED AI:** product-integrated help, training, tooltips, in-app search and user-facing documentation are allowed; still no source code, database, repository or developer-only tooling.
- **HUMAN:** future mode using real participants and subjective instruments.

Exact leakage control belongs to R05; persona/skill setup belongs to R08.

### RECOMMENDATION R02-07 — Record “external support dependency” separately from product help usage

Using in-product help can be desirable, especially for novices. Needing a developer/service desk for a normal task is a different signal.

Record at minimum:

- product help used;
- help resolved question;
- human service/support required;
- task completed after support;
- support topic.

This later supports business metrics such as administrative self-service or support avoidance without contaminating usability definitions.

### RECOMMENDATION R02-08 — Use finding severity separate from task score

A finding should record at least:

- frequency/reproducibility in runs;
- impact on task outcome;
- recoverability;
- persistence across repeated use;
- affected scenario/persona/context;
- gate relevance.

Nielsen’s frequency/impact/persistence model can inform the diagnostic taxonomy, but R04 must design the final severity formula.

### RECOMMENDATION R02-09 — Keep accessibility as a linked but independent quality track

General usability runs should record obvious accessibility blockers encountered during normal use, but formal keyboard/focus/zoom/contrast/assistive-technology conformance belongs to R07.

Do not “award” accessibility merely because an average agent can use the UI.

### RECOMMENDATION R02-10 — Do not call AI confusion “human cognitive load”

AI path complexity, repeated reading, uncertainty, excessive options and backtracking can be recorded as interaction signals. They may suggest cognitive burden, but they are not a human NASA-TLX workload score.

Human workload remains future validation.

### RECOMMENDATION R02-11 — Usability benchmark tasks should be goal-based, not click-script-based

Scenario instructions should state the user goal and necessary business context, not the expected UI path.

Bad benchmark instruction:

`Click Products > New > enter X > Save.`

Preferred benchmark instruction:

`A new product must be available for work at Site A. Create it with the supplied business data and confirm it is ready for use.`

The evaluator may find a better path than expected. That is useful evidence rather than a test failure.

### RECOMMENDATION R02-12 — Benchmark stable journeys separately from exploratory UX review

Two modes should coexist:

- **Benchmark scenario:** versioned and stable enough for longitudinal comparison;
- **Exploratory UX review:** free exploration to discover new issues and candidate scenarios.

Exploratory findings can create new benchmark scenarios, but should not silently rewrite historical benchmark tasks.

---

## 10. Open questions

### OPEN-02-01 — Final boundary between `Interaction Capability` and R02 diagnostic dimensions

**Why unresolved:** ISO/IEC 25010:2023 uses Interaction Capability at product-quality level, while ISO 9241-110 provides interaction principles and ISO 9241-11 describes usability outcome. Detailed measurement mapping requires R04 and potentially licensed standard access.

**Blocking:** NO.

**Unblock condition:** R04 maps each normalized measure to one authoritative construct and verifies no double counting.

### OPEN-02-02 — Exact human subjective instrument set

**Why unresolved:** SUS, UMUX-LITE, SEQ and NASA-TLX address different levels/constructs; the project is AI-first and human testing is deliberately later.

**Blocking:** NO for AI MVP.

**Unblock condition:** future Human Benchmark module compares licensing, validity, task/study-level use and burden.

### OPEN-02-03 — Exact repeated-run design for learnability

**Why unresolved:** number/order of repeats interacts with model/evaluator variability and memory contamination.

**Blocking:** NO for taxonomy.

**Unblock condition:** R05 AI evaluator reproducibility.

### OPEN-02-04 — Navigation/search metric normalization

**Why unresolved:** click count and path length are task-dependent; no universal “good number of clicks” is justified.

**Blocking:** NO.

**Unblock condition:** R03/R04 plus project baselines.

### OPEN-02-05 — ISO/IEC 25063 replacement status

**Why unresolved:** 2014 edition remains published while a final draft replacement is in process in 2026.

**Blocking:** NO.

**Unblock condition:** re-check before Foundation 1.0 freeze.

### OPEN-02-06 — Whether engagement should become a standalone SQBF score

**Why unresolved:** observable engagement-related design signals overlap with motivation/trust/acceptability and are difficult to validate with AI-only testing.

**Blocking:** NO.

**Unblock condition:** R04 synthesis plus later human evidence. Until then, engagement findings remain diagnostic, not a standalone authoritative score.

---

## 11. Contradictions / disagreements

| Conflict ID | Source A | Source B | Type | Resolution | Impact |
|---|---|---|---|---|---|
| C02-01 | ISO 9241-11 usability outcome | Heuristic-style UI inspection | construct mismatch | Both are useful but different: heuristics diagnose interaction properties; task evaluation measures outcomes | Adopt two-plane model |
| C02-02 | ISO usability includes satisfaction | AI-first benchmark requirement | measurement capability mismatch | Satisfaction remains human-subjective; AI records observable task/interaction evidence only | Prevents fake human ratings |
| C02-03 | Accessibility can be included through specified users/context | W3C says ordinary usability often omits disability needs | coverage gap | Keep accessibility linked but independently verified in R07 | Avoids false accessibility claims |
| C02-04 | Desire to minimize interactions | task suitability/error prevention | optimization conflict | Fewer steps are not automatically better; measure unnecessary work relative to task/risk | Click count stays raw metric |
| C02-05 | Stable benchmark scenarios | evolving software/user behaviour | longitudinal validity tension | Version scenarios; preserve historical versions; change deliberately when task meaning changes | Enables trend comparison without fossilizing bad tasks |
| C02-06 | Product help usage may imply friction | learnability/support principles | interpretation conflict | Separate unaided and assisted modes; product help is neither automatic success nor automatic failure | Supports novice-learning use cases |
| C02-07 | First-use simplicity | expert efficiency | persona conflict | Measure experience levels separately; do not average without profile weighting | R08 owns skill model |

---

## 12. Rejected alternatives

### 12.1 Rejected: one generic “UX score” based only on AI opinion

Reason: non-reproducible, mixes outcome and subjective judgement, hides root causes and cannot represent human satisfaction validly.

### 12.2 Rejected: Nielsen heuristics as the benchmark backbone

Reason: useful diagnostic guidance, but explicitly heuristic and not equivalent to context-bound usability outcomes.

### 12.3 Rejected: task completion alone

Reason: hides discoverability, false success, recovery cost, comprehension and help dependency.

### 12.4 Rejected: minimum click count as efficiency score

Reason: ignores task complexity, safety, required confirmation and domain controls.

### 12.5 Rejected: simulated SUS/SEQ/NASA-TLX answered by AI personas

Reason: these are subjective human instruments; AI role-play would produce evaluator-model output, not participant perception.

### 12.6 Rejected: all help use counts as UX failure

Reason: novice learning and user assistance are legitimate interactive-system capabilities. More useful distinction is product help versus external support dependency and whether help resolves the problem.

### 12.7 Rejected: accessibility folded entirely into usability

Reason: overlap exists, but disability-specific and technical conformance needs independent coverage.

### 12.8 Rejected: one scenario per page

Reason: user goals commonly span multiple surfaces. Pages are implementation structure; benchmark scenarios should represent goals/tasks/workflows.

---

## 13. Risks and limitations

1. **ISO copyright/AI restrictions:** R02 did not ingest full ISO publications. Official abstracts/metadata and public standard-family previews were used for scope/status, with secondary corroboration for some principle names. Detailed conformance claims require licensed human review where necessary.
2. **AI evaluator anthropomorphism:** Future prompts could accidentally ask the model to “feel” confidence/frustration. R05 must prohibit treating such answers as human data.
3. **Model competence bias:** A stronger AI may find a function that a real novice would not. This is an evaluator-reproducibility problem for R05, not evidence that the usability construct is invalid.
4. **Task-definition bias:** Poorly written scenarios can make good software look bad or leak the solution. R08 must standardize task wording and allowed knowledge.
5. **Over-observation:** Counting every cursor action may create noisy metrics. R03/R04 need a definition of meaningful versus incidental interactions.
6. **Cross-device context:** R02 is generic; project phase 1 currently prioritizes PC/tablet, but the generic model must remain device-independent.
7. **Enterprise complexity:** Some complex workflows legitimately require confirmation and traceability. “Simple” cannot mean removal of necessary controls.
8. **Information comprehension scoring:** Objective questions require project/domain truth definitions; generic core can define the mechanism but not the correct answers.
9. **Human validation postponed:** AI-only results can support regression and structured quality review, but cannot establish population-level human usability claims.
10. **Current 25063 transition:** Context-of-use standard revision status should be checked again before Foundation 1.0.

---

## 14. Confidence per major conclusion

| Conclusion | Confidence | Main reason |
|---|---|---|
| Usability requires specified user/goal/context | HIGH | Direct ISO 9241-11 / 25063 basis |
| Outcome and interaction diagnostics must be separate | HIGH | Strong construct distinction across ISO usability/interaction standards |
| Discoverability/comprehension require explicit evaluation | HIGH | ISO 9241-110/112/115 scope plus task-evaluation logic |
| False success must be a first-class outcome | HIGH | Explicit GOV.UK benchmark guidance plus safety rationale |
| AI cannot validly generate human subjective usability/workload scores | HIGH | subjective nature of satisfaction/TLX/questionnaires |
| UNAIDED and ASSISTED modes should be separate | HIGH | learnability/help are legitimate system capabilities and support different questions |
| Click count should remain raw before baseline/normalization | HIGH | task/context dependence |
| Repeated runs are required to assess learnability | HIGH | learnability includes discovery/exploration/retention; exact design deferred |
| Accessibility should remain linked but independently verified | HIGH | W3C explicitly distinguishes the fields |
| Generic scenario-family set is sufficient for first SQBF version | MEDIUM-HIGH | strong coverage rationale, but requires validation against BLE and another future project |
| 10-second orientation convention is useful | MEDIUM | practical diagnostic convention, not normative evidence |
| Engagement should not yet be a standalone AI score | MEDIUM-HIGH | strong overlap/subjectivity concern, limited AI-valid measurement evidence |

---

## 15. Implications for later modules

### R03 — Time, efficiency & performance

Must define precise timing events for R02 scenarios, including at least orientation/start, interaction, help, recovery, wait/system time and completion/abandonment. It must determine which interaction counts are meaningful and how to separate human/agent work from system wait.

### R04 — Scoring, normalization & statistics

Must map raw R02 observations to dimensions without double counting. It must treat `FALSE_SUCCESS`, critical task failure and project gates separately from compensable scores. It must not assign universal penalties to click count/path length without baselines.

### R05 — AI evaluator reproducibility

Must define evaluator identity/version, leakage controls, repeated runs, memory reset, allowed tools, UI-only constraints and calibration. It also must determine how learnability testing can occur without uncontrolled model-memory contamination.

### R07 — Accessibility, reliability & resilience

Must define independent accessibility conformance/functional testing and system-failure/resilience scenarios. R02’s ordinary use-error recovery remains user-interaction focused; infrastructure/session/data recovery goes to R07.

### R08 — Persona, skill & scenario model

Must encode experience level, domain knowledge, procedure knowledge, regulatory knowledge, software familiarity, general IT skill, permissions, goals, device and assistance mode. It should formalize the scenario families proposed by R02.

### R09 — ELVA-BLE evidence inventory

Must identify real workflows and user goals without scoring them yet. It should map candidate BLE tasks to R02 scenario families and mark required correct outcomes/comprehension truths.

### R10 — Foundation synthesis

Should preserve the distinction:

`Task Outcome -> Interaction Diagnostics -> Human Subjective (future)`

rather than flattening all usability evidence into one uncontrolled number.

### Future Human Benchmark module

Must evaluate subjective instruments (e.g. SEQ/SUS/UMUX-LITE/TLX where appropriate), sample design and population inference. AI benchmark scores should never be relabelled as human usability scores.

---

## 16. Acceptance criteria verification

- [x] Research question and scope explicit
- [x] Expected source families covered or gap documented
- [x] Search log present
- [x] Source status/version checked
- [x] Normative vs informative claims separated
- [x] FACT / INFERENCE / RECOMMENDATION / OPEN / PROJECT-SPECIFIC separated
- [x] Counterevidence / contradiction search performed for high-impact conclusions
- [x] Copyright / licensing / AI-use constraints checked
- [x] Major conclusions have confidence
- [x] Open questions documented
- [x] Downstream implications documented
- [x] Usability outcome vs interaction properties separated
- [x] AI-observable vs human-subjective measures separated
- [x] Discoverability/navigation/comprehension explicitly represented
- [x] Help/learning/error-recovery explicitly represented
- [x] Generic scenario families proposed
- [x] No numeric score formula made authoritative
- [x] Time formulas deferred to R03
- [x] Accessibility details deferred to R07
- [x] BLE-specific logic excluded

---

## 17. Research completion gate

```text
RESEARCH STATUS: COMPLETE
PRIMARY SOURCES COVERED: YES
CONTRADICTIONS RESOLVED OR DOCUMENTED: YES
FACTS / INFERENCES / RECOMMENDATIONS SEPARATED: YES
OPEN QUESTIONS DOCUMENTED: YES
CONFIDENCE: HIGH
READY FOR SYNTHESIS: YES
```

R02 is ready to inform R03, R04, R05, R07, R08, R09 and R10. It does not authorize final scoring weights, human-usability claims or project-specific pass thresholds.
