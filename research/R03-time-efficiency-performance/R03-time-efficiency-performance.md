# R03 — Time, Efficiency & Performance Measurement Model

- **Research ID:** R03
- **Version:** 1.0.0
- **Date:** 2026-09-09
- **Issue:** #7
- **Repository:** `Creynox/software-quality-benchmark`
- **Governing methodology:** `research/R00-research-methodology/R00-research-methodology.md`
- **Depends on:**
  - `research/R01-quality-model/R01-generic-software-quality-model.md`
  - `research/R02-usability-interaction/R02-usability-interaction.md`
- **Research type:** standards-led structured review with temporal-measurement, benchmark-design and statistical-method analysis
- **Status:** COMPLETE

---

## 1. Question / objective

Define the generic measurement contract for **time, task efficiency and software performance** in the Software Quality Benchmark Framework (SQBF), without inventing arbitrary universal time targets or prematurely converting raw temporal observations into 0–100 scores.

R03 answers:

1. Where does a timed task start and end?
2. How must timing depend on the task outcome so that a fast failure is not misclassified as high efficiency?
3. Which time constructs must be kept separate?
4. How should help, recovery, orientation, system waiting and external process waiting be represented without double counting?
5. How should AI computer-use timing be interpreted without pretending that model execution time is human time?
6. How does **task efficiency** differ from **product performance efficiency**?
7. Which system-performance measures belong in the generic framework?
8. How should workload, cold/warm state, environment and capacity be recorded?
9. Which statistical summaries are appropriate for skewed task-time and latency data?
10. How should failed, abandoned, interrupted and anomalous runs be handled?
11. Which baseline types are valid for comparison?
12. When may an external threshold be adopted and when must time remain only a raw/comparative measure?
13. Which decisions belong to R04 scoring, R05 AI evaluator reproducibility, R07 reliability, or project/platform profiles?

The goal is a **measurement contract**, not a score formula.

---

## 2. Scope

R03 covers four distinct measurement objects:

1. **Task elapsed time** — how long a specified actor/evaluator takes to reach a specified task outcome in a specified context.
2. **Interaction-efficiency timing diagnostics** — where elapsed time is spent during orientation, help, recovery, waiting and similar episodes.
3. **Product performance efficiency** — response/latency, throughput, resource utilization and capacity under specified conditions.
4. **Comparative timing** — current-vs-prior-version, legacy-process, target, external-reference and platform-specific comparisons.

R03 also defines:

- timing event semantics;
- outcome-conditioned timing;
- temporal partitioning and diagnostic tagging;
- raw timing record requirements;
- system-performance environment metadata;
- statistical reporting rules;
- outlier and invalid-run policy;
- cold/warm and load-state rules;
- baseline taxonomy;
- web-performance instrumentation as an optional platform extension;
- boundaries with later research modules.

---

## 3. Explicitly out of scope

R03 does **not** define:

- final 0–100 normalization formulas;
- final score weights;
- universal pass/fail thresholds;
- BLE-specific target times;
- final AI evaluator run-count/calibration policy;
- detailed load-test implementation;
- detailed retry/timeout/resilience policy;
- detailed service-level-objective design;
- human-study sample-size planning;
- final confidence interval policy for every benchmark mode;
- benchmark runner implementation;
- dashboard/web-application implementation.

Those belong primarily to R04, R05, R07, R08, R09/R10 and implementation phases.

---

## 4. Research protocol

### 4.1 Expected source families

R03 required evidence from:

1. current usability/efficiency standards;
2. current product-performance quality standards;
3. current measurement-framework standards;
4. current usability-evaluation reporting guidance;
5. software-system benchmark methodology;
6. task-time statistical literature;
7. latency-distribution and tail-latency operational guidance;
8. web-performance timing specifications and platform thresholds as non-universal examples;
9. research on familiarity/experience effects on task time;
10. current revision status of relevant measurement standards.

### 4.2 Search terms / sources

Research used official ISO metadata/status pages, W3C Web Performance specifications, GOV.UK Service Manual, ACM SIGSOFT Empirical Standards, Google SRE material, Google web.dev/Developer guidance, scholarly indexing and peer-reviewed usability/performance literature.

Representative searches:

- `ISO 9241-11 usability efficiency resources results achieved`
- `ISO IEC 25010 2023 performance efficiency time behaviour resource utilization capacity`
- `ISO IEC 25020 quality measurement framework validity`
- `ISO IEC 25022 quality in use measurement revision 2026`
- `ISO IEC 25023 product quality measurement revision 2026`
- `ISO IEC IEEE 15939 measurement process current 2026`
- `GOV UK usability benchmarking task success task time false success`
- `average task times usability geometric mean Sauro Lewis`
- `task time successful unsuccessful usability`
- `time on task familiarity expert novice CHI`
- `ACM SIGSOFT benchmarking repetitions workload raw data`
- `tail latency percentiles SRE`
- `W3C High Resolution Time User Timing Navigation Timing`
- `Core Web Vitals LCP INP thresholds 75th percentile`

### 4.3 Inclusion rules

Included evidence had to provide one or more of:

- authoritative quality/measurement model status;
- explicit benchmark methodology;
- empirical evidence about task-time distributions or experience effects;
- authoritative operational guidance on latency distributions;
- normative/public browser timing instrumentation;
- documented platform-specific performance thresholds.

### 4.4 Exclusion rules

Excluded from authoritative use:

- arbitrary UX blog claims such as universal seconds-per-task targets;
- unversioned performance advice without workload/context;
- unsupported claims that click count alone equals efficiency;
- claims that one AI agent's wall-clock time is a human task-time estimate;
- benchmarks that omit outcome correctness;
- silent outlier deletion;
- metrics collected only as aggregates when raw observations can be retained;
- current drafts treated as final standards.

### 4.5 Data extracted

For each source R03 extracted, where available:

- measured construct;
- object being measured;
- timing boundary;
- outcome dependency;
- context/workload dependency;
- distribution/statistical guidance;
- threshold status;
- benchmark repeatability implications;
- environment metadata requirements;
- current/draft/withdrawn status;
- downstream owner.

### 4.6 Synthesis method

R03 uses a five-layer model:

1. **Outcome** — what happened.
2. **Elapsed time** — how long the outcome took.
3. **Temporal attribution** — where time was spent.
4. **Product performance** — how the software/system itself behaved under load/conditions.
5. **Comparison reference** — what the observed value is being compared against.

This ordering is deliberate. A time value without an outcome, context and comparison reference is not sufficient evidence of software quality.

---

## 5. Search log

| Date | Source/site | Query/action | Result / note |
|---|---|---|---|
| 2026-09-09 | ISO | ISO 9241-11:2018 | Current usability concepts confirmed; efficiency is part of contextual usability outcome |
| 2026-09-09 | ISO | ISO/IEC 25010:2023 | Current product-quality model confirmed; performance efficiency is product-quality characteristic |
| 2026-09-09 | ISO / public corroboration | performance efficiency substructure | Time behaviour, resource utilization and capacity corroborated; no protected full-text ingestion |
| 2026-09-09 | ISO | ISO/IEC 25020:2019 | Current/confirmed quality measurement framework found; reliability/validity and normalized measurement concepts noted |
| 2026-09-09 | ISO | ISO/IEC 25022:2016 | Published but to be revised; aligned replacement work in progress |
| 2026-09-09 | ISO | ISO/IEC CD 25000-22 | Committee Draft in consultation, not final |
| 2026-09-09 | ISO | ISO/IEC 25023:2016 | Published but to be revised; explicitly does not set universal compliance ranges |
| 2026-09-09 | ISO | ISO/IEC DIS 25000-23 | Revision under development; not final measurement authority |
| 2026-09-09 | ISO/IEEE | ISO/IEC/IEEE 15939:2017 | Current/confirmed measurement process; new DIS under development |
| 2026-09-09 | ISO | ISO 25062:2025 | Current usability-evaluation reporting standard found |
| 2026-09-09 | GOV.UK | usability benchmarking | Success + task time + abandonment + false success required in benchmark guidance |
| 2026-09-09 | ACM SIGSOFT | benchmarking standard | Repeatability, representative workload, construct validity, raw data retention identified |
| 2026-09-09 | ACM/SPEC / Kistowski et al. | benchmark design | Representativeness and workload selection confirmed as benchmark-design concerns |
| 2026-09-09 | CHI / Sauro & Lewis | task-time distribution | Positive skew and geometric-mean recommendation for small human task-time samples found |
| 2026-09-09 | CHI / Suzuki et al. | familiarity and task time | Time becomes more strongly related to perceived usability with familiarity/experience |
| 2026-09-09 | Google SRE | tail latency | Percentile/tail latency recommended over mean-only monitoring |
| 2026-09-09 | W3C | High Resolution Time / User Timing / Navigation Timing | Browser timing instrumentation and monotonic/high-resolution timestamps identified |
| 2026-09-09 | Google web.dev | Core Web Vitals thresholds | Platform-specific web thresholds found; treated as web-profile evidence, not universal SQBF thresholds |

---

## 6. Source register

| ID | Source | Class | Version/status | Applicability | AI/copyright note | Used for |
|---|---|---|---|---|---|---|
| S01 | ISO 9241-11:2018, *Usability: Definitions and concepts* — https://www.iso.org/standard/63500.html | NORMATIVE_STANDARD | CURRENT | DIRECT | ISO metadata/abstract only; do not ingest protected full standard | usability efficiency/context boundary |
| S02 | ISO/IEC 25010:2023, *SQuaRE — Product quality model* — https://www.iso.org/standard/78176.html | NORMATIVE_STANDARD | CURRENT / PUBLISHED | DIRECT | ISO metadata/abstract only | product-performance quality backbone |
| S03 | ISO/IEC 25020:2019, *SQuaRE — Quality measurement framework* — https://www.iso.org/standard/72117.html | NORMATIVE_STANDARD | CURRENT / CONFIRMED 2025 | DIRECT | ISO metadata/abstract only | measurement reliability, validity, selection and normalization boundary |
| S04 | ISO/IEC 25022:2016, *Measurement of quality in use* — https://www.iso.org/standard/35746.html | NORMATIVE_STANDARD | PUBLISHED / TO BE REVISED | TRANSITIONAL | ISO metadata/abstract only | historical/current measurement context, no final new-model authority |
| S05 | ISO/IEC CD 25000-22, *Measurement of quality-in-use* — https://www.iso.org/standard/92688.html | DRAFT_STANDARD | CD / UNDER DEVELOPMENT | TRANSITIONAL | Draft; status only, not final authority | future measurement-model transition |
| S06 | ISO/IEC 25023:2016, *Measurement of system and software product quality* — https://www.iso.org/standard/35747.html | NORMATIVE_STANDARD | PUBLISHED / TO BE REVISED | DIRECT WITH VERSION CAUTION | ISO metadata/abstract only | no universal compliance ranges; product-measurement context |
| S07 | ISO/IEC DIS 25000-23, *Measurement of product quality* — ISO JTC 1/SC 7 catalogue / current DIS metadata | DRAFT_STANDARD | DIS / UNDER DEVELOPMENT | TRANSITIONAL | Draft; do not treat as final | future 25010:2023-aligned product measures |
| S08 | ISO/IEC/IEEE 15939:2017, *Measurement process* — https://www.iso.org/standard/71197.html | NORMATIVE_STANDARD | CURRENT / CONFIRMED 2022 | DIRECT | ISO/IEEE metadata/abstract only | measurement information need, validity, repeatable process |
| S09 | ISO/IEC/IEEE DIS 15939 — https://www.iso.org/standard/95100.html | DRAFT_STANDARD | DIS / UNDER DEVELOPMENT | TRANSITIONAL | Draft status only | future measurement-process revision |
| S10 | ISO 25062:2025, *CIF for reporting usability evaluations* — https://www.iso.org/standard/84255.html | NORMATIVE_STANDARD | CURRENT / PUBLISHED | DIRECT | ISO metadata/abstract only | predefined-task evaluation/reporting context |
| S11 | GOV.UK Service Manual, *Usability benchmarking a website or whole service* — https://www.gov.uk/service-manual/measuring-success/usability-benchmarking-a-website-or-whole-service | OFFICIAL_GUIDANCE | CURRENT WEB GUIDANCE | DIRECT | Open Government Licence unless stated | success, task time, abandonment, false success, repeated rounds |
| S12 | ACM SIGSOFT Empirical Standards, *Benchmarking (of Software Systems)* — https://www2.sigsoft.org/EmpiricalStandards/docs/standards | OFFICIAL_RESEARCH_GUIDANCE | CURRENT WEB STANDARD | DIRECT | Public methodological guidance | workload, repetitions, stability, construct validity, raw results |
| S13 | von Kistowski et al. (2015), *How to Build a Benchmark*, ICPE, DOI 10.1145/2668930.2688819 | PEER_REVIEWED_PRIMARY / METHODOLOGY | PUBLISHED | SUPPORTING | Bibliographic/abstract use | benchmark representativeness and workload design |
| S14 | Sauro & Lewis (2010), *Average task times in usability tests: what to report?*, CHI, DOI 10.1145/1753326.1753679 | PEER_REVIEWED_PRIMARY | PUBLISHED | DIRECT FOR HUMAN TASK-TIME STATISTICS | Bibliographic/abstract findings only | positive skew, geometric mean, small-sample central tendency |
| S15 | Suzuki et al. (2011), *Variation in importance of time-on-task with familiarity with mobile phone models*, CHI, DOI 10.1145/1978942.1979314 | PEER_REVIEWED_PRIMARY | PUBLISHED | SUPPORTING | Bibliographic/abstract use | experience/familiarity changes importance of task time |
| S16 | Google SRE, *Service Level Objectives* / *Monitoring Distributed Systems* — https://sre.google/sre-book/service-level-objectives/ and https://sre.google/sre-book/monitoring-distributed-systems/ | SPECIALIST_OPERATIONAL_GUIDANCE | CURRENT ONLINE BOOK | DIRECT FOR LATENCY REPORTING | Public web guidance | percentile/tail latency vs mean |
| S17 | W3C High Resolution Time Level 2 — https://www.w3.org/TR/hr-time-2/ ; W3C User Timing — https://www.w3.org/TR/user-timing/ ; Navigation Timing — https://www.w3.org/TR/navigation-timing-2/ | NORMATIVE/DRAFT WEB SPECIFICATIONS | MIXED: HR Time 2 Recommendation; newer work in progress | PLATFORM EXTENSION | W3C permissive document license | precise web timing instrumentation |
| S18 | Google web.dev, *How the Core Web Vitals thresholds were defined* — https://web.dev/articles/defining-core-web-vitals-thresholds | VENDOR/PLATFORM GUIDANCE WITH EMPIRICAL BASIS | CURRENT WEB GUIDANCE | WEB PLATFORM ONLY | Public web guidance | LCP/INP/CLS thresholds and p75 aggregation example |
| S19 | iso25000.com, *Performance Efficiency* — https://iso25000.com/index.php/en/component/content/article/22-english/iso-iec-25010/59-performance-efficiency | SPECIALIST_GUIDANCE | CURRENT WEB | CORROBORATING ONLY | Secondary; not normative | public naming of performance-efficiency subcharacteristics |
| S20 | Sauro & Lewis, *Quantifying the User Experience* task-time chapters / public summaries (ScienceDirect) | SCHOLARLY_METHOD_GUIDANCE | ESTABLISHED | SUPPORTING | Bibliographic/summary use | successful-task time vs time-to-failure distinction |

### 6.1 Source-status cautions

1. **ISO/IEC 25022:2016 is transitional.** It remains published, but ISO has started ISO/IEC CD 25000-22 to align quality-in-use measurement with the newer ISO/IEC 25019 model. R03 therefore does not freeze detailed 25022 formulas into Foundation 1.0.
2. **ISO/IEC 25023:2016 is also transitional.** A 25010:2023-aligned replacement is under development as ISO/IEC DIS 25000-23. R03 uses the published standard's high-level measurement principles and explicit lack of universal compliance ranges, but not as immutable future metric detail.
3. **ISO/IEC/IEEE 15939:2017 remains current**, while a new DIS is under development. Its measurement-process concepts remain relevant, but Foundation freeze must re-check status.
4. ISO copyright and AI-use restrictions are respected by recording bibliographic/status metadata and independent conclusions rather than ingesting/reproducing licensed standard text.
5. Google Core Web Vitals are **platform-specific guidance**, not a universal software-quality standard.

---

## 7. Confirmed facts

### FACT F03-01 — Task efficiency and product performance are related but different measurement objects

Usability standards frame efficiency around the resources expended by specified users to achieve specified goals in a specified context, while the product-quality model treats performance efficiency as a property/capability of the ICT/software product under specified conditions. [S01, S02, S03]

**Implication:** SQBF must not collapse `time-to-complete-a-user-task` and `system response latency` into one metric.

**Confidence:** HIGH.

### FACT F03-02 — Product performance efficiency includes time behaviour, resource utilization and capacity

The current ISO/IEC 25010 product-quality model includes performance efficiency as a top-level product-quality characteristic. Publicly available secondary material consistent with the standard identifies its stable substructure as time behaviour, resource utilization and capacity. [S02, S19]

**Confidence:** HIGH for the high-level structure; detailed normative wording is intentionally not reproduced.

### FACT F03-03 — Measurement requires explicit information needs, defined measures and validity checks

ISO/IEC 25020 and ISO/IEC/IEEE 15939 both treat measurement as a designed process: measures are selected/defined for information needs, measurement is planned/performed, and reliability/validity of measurement and analysis results must be considered. [S03, S08]

**Implication:** A metric is not useful merely because it is easy to collect.

**Confidence:** HIGH.

### FACT F03-04 — Current product-quality measurement guidance does not provide universal compliance ranges

ISO/IEC 25023:2016 explicitly states that it does not assign universal ranges/grades of compliance because acceptable values depend on the nature/category/integrity needs and users' needs of the product/system. [S06]

**Implication:** SQBF must not invent a universal rule such as `every business task must finish in <= 60 seconds`.

**Confidence:** HIGH.

### FACT F03-05 — Usability benchmarking must bind task time to task outcome

GOV.UK's usability benchmarking guidance recommends measuring whether the user completed the task, the time to complete it, whether the task was abandoned, and whether the participant believed they had succeeded when they had not. [S11]

**Implication:** Time without outcome state is incomplete benchmark evidence.

**Confidence:** HIGH.

### FACT F03-06 — Failed/abandoned-task time is analytically different from successful completion time

Usability measurement literature distinguishes successful task completion time from time until failure/give-up and total time on task. Failed-task duration can be highly variable and does not represent successful-task efficiency. [S20; corroborated by S11]

**Confidence:** HIGH.

### FACT F03-07 — Human usability task-time distributions are commonly positively skewed

Sauro & Lewis analyzed 61 large-sample usability tasks and reported positive skew in task-time data. Their simulations found the geometric mean to be a better estimator of the population center than the sample median for small samples, with the recommendation to use it at least alongside the median for small human task-time studies. [S14]

**Confidence:** HIGH for human usability task-time data; applicability to AI-agent repeated runs is a separate inference, not a human-population claim.

### FACT F03-08 — The importance of time-on-task changes with user familiarity

A CHI experiment comparing novice and familiar users found the relationship between perceived usability and time-on-task strengthened with familiarity; task time mattered more as users gained experience. [S15]

**Implication:** Expert/experienced workflow benchmarks may legitimately emphasize time more heavily than first-use/novice scenarios, but weighting belongs to R04/R08/project profiles.

**Confidence:** MEDIUM-HIGH because the evidence is specific to the studied devices/context and should not be universalized beyond the direction of the finding.

### FACT F03-09 — Software-system benchmarks require a defined workload/context and sufficient repetition/stability evidence

ACM SIGSOFT's benchmarking standard requires defined context, automated/repeatable procedure, specified workload/usage profile, construct-validity discussion and sufficient repetitions/duration to assess stability. It also flags storing only aggregated measurements instead of raw results as an antipattern. [S12]

Kistowski et al. likewise treat representativeness and workload selection as central benchmark-design concerns. [S13]

**Confidence:** HIGH.

### FACT F03-10 — Mean latency alone can hide harmful tail behaviour

Google SRE guidance explicitly warns that average latency can hide slow tails and recommends percentile-based views such as p50, p95, p99 or higher depending on the service. [S16]

**Implication:** System-response benchmarks should preserve latency distributions and report tails rather than relying on an arithmetic mean alone.

**Confidence:** HIGH as operational guidance; exact percentile choice remains context-dependent.

### FACT F03-11 — Web platforms provide high-resolution timing instrumentation

W3C specifications define high-resolution monotonic timing and browser APIs for navigation/user timing and performance entries. These mechanisms enable precise web-application instrumentation separate from manual wall-clock observation. [S17]

**Confidence:** HIGH.

### FACT F03-12 — Some web performance thresholds are evidence-based but platform-specific

Google's current Core Web Vitals guidance classifies LCP <= 2.5 s, INP <= 200 ms and CLS <= 0.1 as `good`, evaluated at the 75th percentile of page views (segmented by desktop/mobile where applicable). [S18]

**Implication:** External thresholds can be adopted in a **Web Platform Profile**, but they are not universal task-time thresholds for arbitrary software workflows.

**Confidence:** HIGH for the current Google web guidance.

### FACT F03-13 — Relevant SQuaRE measurement standards are currently in transition

ISO is developing replacements/revisions for quality-in-use measurement and product-quality measurement to align with the newer quality models. The JTC 1/SC 7 catalogue shows ISO/IEC CD 25000-22 and ISO/IEC DIS 25000-23 under development in 2026. [S05, S07]

**Confidence:** HIGH.

### FACT F03-14 — Benchmark raw data must be retained separately from derived summaries

ACM SIGSOFT explicitly identifies collecting only aggregated measurements instead of retaining raw results for offline analysis as a benchmarking antipattern. [S12]

**Implication:** SQBF run storage must keep per-run/per-sample timings, not only report-level averages.

**Confidence:** HIGH.

---

## 8. Derived conclusions

### INFERENCE I03-01 — Outcome must be evaluated before efficiency

A task completed incorrectly in 20 seconds is not more efficient than a correct completion in 60 seconds. Likewise, an evaluator that gives up immediately must not receive a favourable efficiency result.

**Derived from:** F03-01, F03-05, F03-06.

**Conclusion:** SQBF's ordering is:

```text
OUTCOME
  -> TIMING
    -> EFFICIENCY INTERPRETATION
```

Task-time aggregation must be stratified by outcome class.

**Confidence:** HIGH.

### INFERENCE I03-02 — SQBF needs one mandatory elapsed clock plus optional attributed timing

Attempting to infer fine-grained cognitive time from screen interaction is unreliable, especially with AI evaluators. However, a reproducible total task elapsed time is usually observable.

**Derived from:** F03-03, F03-05, F03-11 and measurement-validity principles.

**Conclusion:** `TOTAL_ELAPSED` is mandatory for timed scenarios. Finer timing partitions are recorded only when the instrumentation can identify their boundaries with declared confidence.

**Confidence:** HIGH.

### INFERENCE I03-03 — Temporal partitions and diagnostic phase labels must be two different structures

`HELP`, `RECOVERY` and `ORIENTATION` describe **why/what phase** the actor is in, while `APPLICATION_WAIT` and `ACTOR_CONTROLLED` describe **who/what controls elapsed time**. A help episode may itself include system waiting; recovery may include orientation and navigation.

**Conclusion:** SQBF must not force all timing labels into one additive taxonomy.

It adopts:

1. an **exclusive elapsed-time partition** for additive accounting; and
2. **overlapping diagnostic phase tags** for behavioural analysis.

**Confidence:** HIGH.

### INFERENCE I03-04 — AI task wall-clock time is an evaluator benchmark, not a human-time estimate

An AI computer-use run includes model deliberation/inference, screenshot/tool overhead and action execution characteristics that humans do not share. Different AI models/providers can have different latency even when interacting with the identical UI.

**Derived from:** F03-03, F03-09 and construct-validity requirements.

**Conclusion:** SQBF may use AI task time for **same-evaluator regression/comparison**, but must label it as `AI_EVALUATOR_TASK_TIME`. It must not claim this equals expected human task time.

Cross-model timing comparison requires R05 calibration/normalization rules and is not assumed valid by R03.

**Confidence:** HIGH.

### INFERENCE I03-05 — Product wait time should be isolated from evaluator/actor time where feasible

If the system takes 8 seconds to save, that is a different quality problem from an actor spending 8 seconds searching for the Save button.

**Conclusion:** Where observable, application-controlled waiting is a first-class partition and product-performance evidence source.

**Confidence:** HIGH.

### INFERENCE I03-06 — Physical/domain-process waiting must be separated from software time

Operational software can orchestrate tasks where the real-world process itself takes time: laboratory incubation, drying, external approval, equipment measurement, production cycles, etc. Counting that whole duration as UI inefficiency would measure the wrong construct.

**Conclusion:** Project profiles can tag `EXTERNAL_DOMAIN_WAIT`, preserving both:

- end-to-end workflow wall-clock time; and
- software/interaction time excluding unavoidable domain-process waiting.

**Confidence:** HIGH.

### INFERENCE I03-07 — There is no defensible universal LIMS/business-task time target in the generic core

Published product-measurement guidance intentionally leaves acceptable ranges to product/system/user needs, and usability task durations depend on task, user and context. [F03-04]

**Conclusion:** R03 records raw times and comparisons. R04 may only convert time to scores when an appropriate reference has been declared and validated.

**Confidence:** HIGH.

### INFERENCE I03-08 — The benchmark should support multiple reference types because they answer different questions

`Is BLE faster than last month?`, `Is BLE faster than the old process?`, and `Does BLE meet an operational requirement?` are not the same comparison.

**Conclusion:** Baseline/reference type is mandatory metadata for any derived timing comparison.

**Confidence:** HIGH.

### INFERENCE I03-09 — Task-time and system-latency statistics require different default summaries

Human task-time datasets are often small and positively skewed; service latency datasets can contain thousands/millions of observations where tails matter. One universal statistic would be inappropriate.

**Derived from:** F03-07, F03-09, F03-10.

**Conclusion:** R03 adopts separate reporting profiles for `TASK_TIME` and `SYSTEM_LATENCY`.

**Confidence:** HIGH.

### INFERENCE I03-10 — Valid slow runs are evidence, not outliers to delete

A slow run can be exactly the behaviour the benchmark is meant to discover. Arbitrary trimming makes a system appear faster and damages reproducibility.

**Derived from:** F03-09, F03-10, F03-14.

**Conclusion:** No timing observation is excluded solely because it is numerically extreme. Exclusion requires a documented invalid-run reason unrelated to the product behaviour being measured.

**Confidence:** HIGH.

### INFERENCE I03-11 — Cold and warm performance must be separate strata when both are plausible user states

Caches, connections, compilation, initialization and data loading can materially alter performance. Mixing cold and warm observations without recording state damages construct validity.

**Derived from:** benchmark context/workload and validity requirements [F03-03, F03-09].

**Conclusion:** Cache/start state is required environment metadata when it can influence performance.

**Confidence:** HIGH.

### INFERENCE I03-12 — Current web thresholds belong to a platform profile, not the generic scoring core

Core Web Vitals are designed for web-page/user-experience characteristics and have explicit platform methodology. They are valuable for browser-based products but irrelevant to some desktop/native/server workflows.

**Conclusion:** SQBF should later create a `WEB_APP` platform profile that can adopt current Web Vitals while the generic core remains technology-neutral.

**Confidence:** HIGH.

---

## 9. Adopted measurement model

### 9.1 Measurement planes

SQBF R03 adopts four separate planes:

```text
A. TASK TEMPORAL OUTCOME
   How long did this actor/evaluator take to reach this outcome?

B. TEMPORAL DIAGNOSTICS
   Where was the elapsed time spent / what episode caused it?

C. PRODUCT PERFORMANCE
   How fast/capable/resource-efficient was the software itself?

D. REFERENCE / COMPARISON
   Relative to what baseline/target is the value interpreted?
```

These planes can be linked but must not be merged into a single raw metric.

---

## 10. Task timing contract

### 10.1 Mandatory timing events

Every timed scenario MUST define these semantic events before execution:

#### `TASK_READY_AT`

The scenario instruction is fully available to the evaluator and the designated start-state UI is ready for interaction.

Rules:

- If reading the instruction is intended to be part of the test, the timer starts when the instruction becomes available.
- If instruction familiarization occurs before timing, this must be explicitly declared in scenario metadata.
- Hidden pre-reading is not allowed in a benchmark advertised as first-use/unaided.

#### `TASK_FIRST_ACTION_AT`

Timestamp of the first evaluator interaction with the application after `TASK_READY_AT`.

This is descriptive only; it is not necessarily productive.

#### `FIRST_PRODUCTIVE_ACTION_AT` (optional but recommended)

Timestamp of the first action that objectively advances toward a valid success path according to the scenario oracle/contract.

This supports an orientation/discoverability measure but must not be guessed merely because an action looked plausible.

#### `OBJECTIVE_SUCCESS_AT`

Timestamp when the predeclared success predicate is objectively satisfied.

Examples:

- persisted entity exists with required values;
- correct target information is displayed;
- workflow state reached;
- report generated with expected state;
- update committed and confirmation/state visible.

The evaluator saying `done` is **not** sufficient.

#### `EVALUATOR_SUCCESS_DECLARED_AT` (when applicable)

Timestamp when the evaluator explicitly claims success.

If this occurs without the success predicate, the outcome is `FALSE_SUCCESS`.

#### `TASK_TERMINATED_AT`

Timestamp when the run ends for any terminal outcome:

- success;
- failure;
- false success;
- abandonment;
- expected permission denial;
- system blocker;
- benchmark timeout;
- invalid-run termination.

### 10.2 Primary raw duration fields

```text
TOTAL_ELAPSED = TASK_TERMINATED_AT - TASK_READY_AT

SUCCESSFUL_COMPLETION_TIME = OBJECTIVE_SUCCESS_AT - TASK_READY_AT
  only when an objective success state was reached

TIME_TO_FIRST_ACTION = TASK_FIRST_ACTION_AT - TASK_READY_AT

TIME_TO_FIRST_PRODUCTIVE_ACTION = FIRST_PRODUCTIVE_ACTION_AT - TASK_READY_AT
  only when objectively classifiable

TIME_TO_FALSE_SUCCESS = EVALUATOR_SUCCESS_DECLARED_AT - TASK_READY_AT
  only for FALSE_SUCCESS

TIME_TO_FAILURE = TASK_TERMINATED_AT - TASK_READY_AT
  for terminal FAIL_KNOWN

TIME_TO_ABANDON = TASK_TERMINATED_AT - TASK_READY_AT
  for ABANDONED
```

### 10.3 Outcome-conditioned reporting rule

Do not aggregate these into one `average task time`:

```text
PASS_CORRECT times
PASS_WITH_RECOVERY times
FALSE_SUCCESS times
FAIL_KNOWN times
ABANDONED times
BLOCKED times
```

At minimum, successful completion time is reported separately from failure/abandonment time.

`PASS_WITH_RECOVERY` may be reported both:

- with all successful completions; and
- as its own stratum when recovery cost is relevant.

---

## 11. Exclusive elapsed-time partition

Fine-grained partitioning is optional unless a project/platform runner can instrument it reliably.

When used, every included moment of `TOTAL_ELAPSED` must belong to at most one exclusive class:

### `ACTOR_CONTROLLED`

Elapsed time primarily controlled by the current evaluator/actor: reading, deciding, navigating, typing, choosing, checking, interpreting.

For human tests, this includes human interaction/thinking that occurs during the timed task.

For AI tests, this can include model deliberation unless separately instrumented.

### `AI_EVALUATOR_COMPUTE`

AI-only optional partition when the harness can reliably identify evaluator inference/deliberation/tool-planning time separate from application waiting.

This is an evaluator property, not product performance.

### `APPLICATION_CONTROLLED_WAIT`

Time after an application action where the evaluator cannot reasonably progress because the software/system is processing/loading/responding.

Examples:

- route/data load;
- save processing;
- report generation;
- search/query execution;
- server-confirmed transition.

### `EXTERNAL_DOMAIN_WAIT`

Time controlled by a real-world/domain process outside ordinary application computation.

Examples:

- equipment measurement cycle;
- physical laboratory waiting step;
- external human approval;
- scheduled process that is inherently part of the domain workflow.

This may matter to end-to-end business duration while not representing UI/system response time.

### `BENCHMARK_HARNESS_OVERHEAD`

Time introduced by screenshot capture, automation transport, benchmark orchestration, recording infrastructure or other test machinery and independently measurable from product/evaluator behaviour.

### `PAUSED_EXCLUDED`

A documented pause excluded by protocol, such as an external interruption not caused by the product.

A run containing excluded pause time must retain both raw wall-clock and adjusted elapsed values plus exclusion reason.

### 11.1 Important rule

If the benchmark cannot classify a partition reliably, it records `UNKNOWN_ATTRIBUTION` rather than inventing a split.

---

## 12. Diagnostic phase tags

These labels are **not additive timing partitions**. They can overlap the exclusive partition above.

Recommended tags:

- `ORIENTATION`
- `DISCOVERY`
- `PRIMARY_WORK`
- `DATA_ENTRY`
- `INTERPRETATION`
- `VERIFICATION`
- `HELP_USAGE`
- `TRAINING_USAGE`
- `BACKTRACK`
- `ERROR_RECOVERY`
- `RETRY`
- `CONTEXT_SWITCH`
- `PERMISSION_RESOLUTION`

Example:

```text
12:04:10–12:04:25  ACTOR_CONTROLLED + HELP_USAGE
12:04:25–12:04:28  APPLICATION_CONTROLLED_WAIT + HELP_USAGE
12:04:28–12:04:40  ACTOR_CONTROLLED + ERROR_RECOVERY
```

Therefore:

```text
HELP_TIME
```

must not be added to `ACTOR_CONTROLLED + APPLICATION_CONTROLLED_WAIT` as if it were an independent partition. It is a tagged interval over those states.

---

## 13. AI evaluator timing contract

### 13.1 Required label

Every AI-run timing result must identify itself as:

```text
AI_EVALUATOR_TASK_TIME
```

with at least:

```text
evaluator_provider
evaluator_model
evaluator_version_or_snapshot_if_available
computer_use_mode
benchmark_runner_version
run_mode
```

### 13.2 Valid uses

AI task time is valid for:

- regression across application versions using the same evaluator configuration;
- comparing alternative UI designs using the same evaluator configuration;
- detecting large changes in discoverability/interaction cost;
- measuring the same benchmark suite longitudinally, provided R05 repeatability criteria are met.

### 13.3 Invalid claims

R03 forbids claims such as:

```text
"A human laboratory technician needs 92 seconds"
```

when the only observation is an Astra/Opus/Fable run.

AI wall-clock time can be influenced by:

- evaluator model compute latency;
- tool invocation overhead;
- screenshot processing;
- provider/runtime latency;
- model reasoning strategy;
- benchmark harness delays.

Those are not human interaction properties.

### 13.4 Cross-evaluator comparison

Until R05 defines a calibration method, R03 treats:

```text
Astra 120 s
Opus 85 s
```

as **not directly comparable evidence of product improvement**.

Both raw results may be stored, but they belong to separate evaluator strata.

---

## 14. Interaction efficiency observations carried from R02

Time is only one resource/cost signal. R03 keeps these R02 observations linked to the same timed run:

```text
total_interactions
unnecessary_interactions
navigation_transitions
maximum_navigation_depth
backtracks
dead_ends
repeated_actions
duplicate_data_entry_count
invalid_attempts
validation_errors
recovery_attempts
help_queries
external_support_required
```

R03 does not turn them into a compound efficiency score. R04 owns scoring/normalization.

### 14.1 Why raw action counts are not sufficient alone

Ten fast, obvious actions may be preferable to three highly confusing actions. Conversely, a short click path can hide expensive reading/interpretation.

Therefore:

```text
CLICK COUNT != EFFICIENCY
```

The metric is diagnostic evidence only unless a project-specific construct justifies stronger use.

---

## 15. Product performance measurement model

R03 separates product performance into three families consistent with the current performance-efficiency structure.

### 15.1 Time behaviour

Candidate generic measures:

- user-visible action latency;
- navigation/page transition latency;
- query/search latency;
- save/commit confirmation latency;
- report generation latency;
- startup/cold-start latency;
- warm/repeat operation latency;
- throughput rate where relevant.

Every latency measure must define:

```text
start_event
end_event
measured_layer
workload
conditions
```

Example:

```text
SAVE_CONFIRMATION_LATENCY
start: user activates Save
end: durable success state is confirmed and visible
```

This differs from pure server-request latency if client rendering or asynchronous confirmation continues afterward.

### 15.2 Resource utilization

Candidate measurements include, where instrumentable and relevant:

- CPU;
- memory;
- storage I/O;
- network I/O/bandwidth;
- persistent storage consumption;
- client CPU/memory for rich applications;
- energy/resource measures when a profile explicitly requires them.

These are mostly white-box/telemetry measures, not computer-use UX measures.

### 15.3 Capacity

Capacity describes the maximum supported parameter limits under specified quality requirements.

Candidate parameters:

- concurrent users;
- requests/transactions per unit time;
- dataset/database size;
- number of entities/items;
- report/query size;
- queue depth;
- connected devices;
- simultaneous jobs.

A capacity claim must define what quality condition still has to hold at that load.

Example:

```text
"supports 500 concurrent users"
```

is incomplete unless it specifies acceptable correctness, latency/error rate and test conditions.

---

## 16. Performance workload/context contract

Every comparable product-performance run must record the material context.

### 16.1 Software identity

```text
project
application_version
git_commit_or_build_id
deployment_mode
server_release/configuration
feature_flags
```

### 16.2 Client environment

```text
client_device_class
hardware_summary
os
browser_or_runtime
browser_version
viewport
device_pixel_ratio_if_relevant
input_mode
```

### 16.3 Network/environment

```text
network_type_or_profile
latency_emulation_if_any
bandwidth_limits_if_any
server_region/location
client_region/location
proxy/vpn state if material
```

### 16.4 Data state

```text
fixture_version
database_size_or_class
record/entity counts relevant to scenario
indexing/search state if relevant
seed/reference dataset version
```

### 16.5 Load/workload

```text
concurrent_users
arrival_rate_or_request_rate
operation_mix
test_duration
warmup_policy
background_load
think_time/load-model if applicable
```

### 16.6 Cache/start state

At minimum when relevant:

```text
COLD
WARM
MIXED_REALISTIC
```

Do not aggregate cold and warm results without preserving the strata.

### 16.7 Evaluator/test instrumentation

```text
runner_version
instrumentation_version
clock_source
sample_rate
measurement_precision
known_harness_overhead
```

---

## 17. System-latency statistical reporting

### 17.1 Raw samples first

All individual latency samples must be retainable.

### 17.2 Default summaries for sufficiently sampled latency distributions

Recommended descriptive set:

```text
n
p50
p75 (optional depending on profile)
p95
p99
min
max
error_count
timeout_count
```

Higher percentiles such as p99.9 may be appropriate for high-volume/critical services, but are meaningless without enough samples.

### 17.3 Mean

Arithmetic mean may be retained, but it must not be the only reported latency statistic for variable/tail-sensitive workloads.

### 17.4 Percentile sample-size caution

R03 does not require p99 from tiny sample sets. If a run has only tens of observations, high percentiles are unstable and should not be presented with false precision.

R04/implementation must define minimum sample requirements for each percentile before automated scoring.

---

## 18. Task-time statistical reporting

### 18.1 Preserve every run

For AI and human modes alike, retain all raw task times plus outcome.

### 18.2 AI repeated-run report

Until R05 establishes a stronger inferential model, recommended descriptive output is:

```text
all raw values
n
median
geometric mean (when all durations > 0)
min
max
```

Optional quartiles may be shown only with enough runs and must be labelled descriptive.

Do not infer a human population distribution from AI runs.

### 18.3 Human-study future report

For future human benchmarking, the evidence base supports using the geometric mean at least alongside the median for positively skewed small-sample task times. [S14]

R03 recommends storing:

```text
raw values
n
geometric mean
median
arithmetic mean
spread / interval estimates when methodologically justified
```

Different summaries answer different questions:

- **geometric mean / median:** typical center for skewed task times;
- **arithmetic mean:** expected aggregate time burden can be relevant for labor/cost planning;
- **distribution/spread:** consistency and long-tail user burden.

### 18.4 Log transformation

Log-domain analysis may be appropriate for statistical inference on positively skewed human task times, consistent with the usability literature. R04/human-study methodology must specify the exact inference method before use.

---

## 19. Failed, abandoned and censored timing

### 19.1 Do not mix failure with successful completion

Report separately:

```text
SUCCESSFUL_COMPLETION_TIME
TIME_TO_FAILURE
TIME_TO_ABANDON
TIME_TO_FALSE_SUCCESS
TIME_TO_SYSTEM_BLOCK
```

### 19.2 Benchmark timeout

A scenario can define a maximum runtime to protect test resources, but the timeout is not automatically a product-quality threshold.

If the benchmark stops at the timeout, the run is right-censored/terminated by protocol and must not be recorded as if the task naturally took exactly the timeout value.

### 19.3 Future advanced analysis

For sufficiently large datasets with many timeout/censored observations, survival/time-to-event methods may be considered in R04 or later statistical work. R03 does not make this mandatory for the MVP.

---

## 20. Invalid runs and outliers

### 20.1 No automatic numeric outlier deletion

A value is never excluded merely because it is slow/fast or far from the mean.

### 20.2 Valid exclusion reasons

Examples of potentially valid invalid-run reasons:

- benchmark harness crashed;
- screen-recording/automation infrastructure froze independently of application;
- unrelated OS update or machine sleep;
- evaluator connection lost before a meaningful task outcome;
- test fixture corrupt before task start;
- external interruption unrelated to product;
- task instructions were delivered incorrectly.

### 20.3 Invalid exclusions

Do not exclude a run because:

- the application was unexpectedly slow;
- the application timed out;
- a real error occurred;
- the actor became lost;
- many retries occurred;
- the task produced a bad product state.

Those are benchmark evidence.

### 20.4 Exclusion audit record

Every excluded run retains:

```text
run_id
raw_start/end timestamps
observed duration
exclusion_reason
excluded_by
supporting evidence
whether product behaviour may have contributed
```

---

## 21. Baseline and reference taxonomy

Every comparative timing result declares one of the following reference classes.

### `SELF_VERSION_BASELINE`

Same product/project, earlier accepted version/build, same scenario/profile/evaluator/environment as closely as possible.

Use for:

- regression detection;
- longitudinal optimization.

### `LEGACY_PROCESS_BASELINE`

Previous software/manual/paper/business process that the project is intended to replace.

Use for:

- workflow time savings;
- business-efficiency evidence.

Requirements:

- same outcome semantics;
- comparable actor skill;
- comparable data/task complexity;
- differences documented.

### `TARGET_REQUIREMENT`

Explicit business/user/contract/SLO requirement.

Examples:

```text
search result visible within X ms
monthly close workflow within Y minutes
```

The origin/rationale of the target must be recorded.

### `EXTERNAL_REFERENCE`

Published industry/reference benchmark.

Use only when:

- task semantics are materially comparable;
- user/context is comparable;
- measurement method is known;
- version/date/source are recorded.

An external number from a different task is not a valid target merely because it concerns similar software.

### `PLATFORM_THRESHOLD`

Technology/platform-specific external guidance.

Example:

- Core Web Vitals for web applications.

This can be authoritative for the chosen platform profile without becoming a generic software-task threshold.

### `NO_REFERENCE_RAW`

No defensible target/baseline yet.

This is a valid benchmark state.

The raw time is stored and becomes a candidate future baseline.

---

## 22. Comparative timing metrics

These are **derived measures**, not 0–100 quality scores.

When baseline and current values are comparable and positive:

### Absolute delta

```text
DELTA_TIME = CURRENT_TIME - BASELINE_TIME
```

Negative is faster.

### Relative change

```text
RELATIVE_TIME_CHANGE = (CURRENT - BASELINE) / BASELINE
```

Example: `-0.25` = 25% less time.

### Time saved

```text
TIME_SAVED = BASELINE - CURRENT
```

### Speedup ratio

```text
SPEEDUP = BASELINE / CURRENT
```

Example: `2.0x` means current is twice as fast under the declared measurement definition.

### Caution

No derived comparison is valid if the outcome, scenario, skill profile or environment changed materially without adjustment/documentation.

---

## 23. Legacy/manual workflow benchmarking

Because SQBF is intended to measure whether software actually improves work, project profiles may capture a legacy workflow before replacement.

Recommended record:

```text
legacy_process_id
legacy_process_version/date
role/skill profile
start condition
success condition
raw duration
active work duration if observable
waiting duration if observable
error/rework events
tools/materials used
assistance required
```

### 23.1 Important limitation

Legacy workflow time is project/domain evidence, not a generic core threshold.

For ELVA-BLE this can later answer questions such as:

```text
How much time does a trained laboratory technician need today?
How much time does the equivalent BLE workflow need?
```

R03 does not research LIMS-specific timings; that belongs to R09/profile work.

---

## 24. First-use vs experienced-use timing

R03 adopts R02/R08's future experience profiles as separate timing strata.

Do not average:

```text
FIRST_USE
TRAINED
EXPERIENCED
```

into one task-time number.

The evidence indicates that time can become more important to experienced users. [S15]

Therefore project profiles may later define stronger optimization targets for repeated high-frequency expert workflows than for rare first-use tasks, while first-use scenarios may prioritize discoverability/help/error avoidance.

Weighting belongs to R04/R08/profile design.

---

## 25. Learning curves and repeat-use timing

For `REPEAT_LEARN` scenarios from R02, store each iteration separately:

```text
run_1_time
run_2_time
run_3_time
...
```

Derived descriptive measures may include:

```text
absolute_improvement_run1_to_runN
relative_improvement_run1_to_runN
```

Do not silently replace Run 1 with the fastest later run.

First-use and learned performance answer different questions.

---

## 26. Help and recovery timing

### 26.1 Help

Store:

```text
help_used
help_episode_count
help_first_open_at
help_episode_intervals
successful_return_to_task
```

Derived:

```text
TIME_TO_HELP_DISCOVERY
```

may be useful when the scenario explicitly evaluates assistance.

### 26.2 Recovery

Store:

```text
error_detected_at
recovery_started_at
recovered_state_at
recovery_success
```

Derived:

```text
RECOVERY_ELAPSED
```

is a diagnostic measure.

### 26.3 No double counting

Help/recovery episode duration overlaps exclusive actor/application timing partitions and must not be added again to `TOTAL_ELAPSED`.

---

## 27. System-wait timing from black-box computer use

A black-box evaluator can often observe user-visible waiting, but attribution is imperfect.

Recommended evidence levels:

### `WAIT_OBSERVED_HIGH_CONFIDENCE`

Clear loading/progress state or disabled interaction until completion.

### `WAIT_OBSERVED_MEDIUM_CONFIDENCE`

UI remains unchanged after an action until new state appears, but the evaluator cannot prove the entire interval was application processing.

### `WAIT_UNRESOLVED`

Cannot reliably distinguish application wait from evaluator delay/decision.

Do not manufacture millisecond-level server latency from screenshot timing.

For precise product latency, use instrumentation/telemetry or platform APIs where available.

---

## 28. Web application performance extension candidate

R03 does not hard-code web metrics into the technology-neutral core, but records a candidate `WEB_APP` platform profile.

### 28.1 Instrumentation

Potential sources:

- W3C High Resolution Time;
- User Timing;
- Navigation Timing;
- Performance Timeline;
- Resource/Server/Event/Paint timing where applicable.

### 28.2 Core Web Vitals example

Current Google guidance uses:

```text
LCP good: <= 2.5 s
INP good: <= 200 ms
CLS good: <= 0.1
aggregation: 75th percentile
```

These can become `PLATFORM_THRESHOLD` references for web products.

### 28.3 Boundary

A web app can meet Core Web Vitals and still have a five-minute confusing business workflow.

Therefore:

```text
WEB PERFORMANCE != TASK EFFICIENCY
```

Both should be measured independently.

---

## 29. Product-performance vs reliability boundary

A slow request and a failed request are different observations.

R03 owns:

- latency distribution;
- timeout duration as observed timing;
- throughput;
- resource use;
- capacity.

R07 owns detailed:

- timeout/retry correctness;
- fault tolerance;
- recoverability;
- resilience under faults;
- partial-failure behaviour.

A performance run can emit reliability findings, but the constructs remain separate.

---

## 30. Product-performance vs UX boundary

R03 owns measured wait/latency.

R02 owns how the system communicates waiting:

- progress/status visibility;
- whether the user understands what is happening;
- whether cancellation/control exists;
- whether the next action is clear.

Example:

```text
Save takes 4.0 seconds -> R03 performance evidence
No progress/confirmation during those 4 seconds -> R02 interaction evidence
```

Do not score both as the same defect without acknowledging the shared cause.

---

## 31. Performance regression protocol

A valid before/after comparison should keep stable where material:

```text
scenario version
success predicate
profile/persona skill
run mode
evaluator model/config
fixture/data volume
hardware/client
browser/runtime
network profile
server/deployment
cache state
concurrency/load
instrumentation version
```

If a factor changes, record it and classify comparability:

```text
COMPARABLE
PARTIALLY_COMPARABLE
NOT_COMPARABLE
```

R04 may later decide whether partially comparable results can affect scoring.

---

## 32. Performance trend storage

For longitudinal use, the benchmark should store time-series-compatible records rather than overwrite the previous result.

Minimum keys:

```text
project_profile_version
scenario_version
software_build
run_timestamp
evaluator/configuration
environment_id
run_id
metric_id
raw_value
unit
outcome
reference_type
reference_id
```

This supports future visualizations such as:

```text
Probe erfassen
v1.4  225 s
v1.5  174 s
v1.6  141 s
```

without reparsing Markdown reports.

---

## 33. Candidate raw data schema

Illustrative only; exact JSON/YAML schema belongs to implementation/specification synthesis.

```yaml
run_timing:
  run_id: "..."
  scenario_id: "..."
  scenario_version: "..."
  outcome: PASS_CORRECT

  timestamps:
    task_ready_at: "..."
    first_action_at: "..."
    first_productive_action_at: "..."
    objective_success_at: "..."
    evaluator_success_declared_at: null
    task_terminated_at: "..."

  durations_ms:
    total_elapsed: 132000
    successful_completion: 132000
    time_to_first_action: 8000
    time_to_first_productive_action: 21000

  exclusive_partitions_ms:
    actor_controlled: 94000
    ai_evaluator_compute: null
    application_controlled_wait: 33000
    external_domain_wait: 0
    benchmark_harness_overhead: 5000
    unknown_attribution: 0

  diagnostic_episodes:
    - tag: ORIENTATION
      start: "..."
      end: "..."
    - tag: HELP_USAGE
      start: "..."
      end: "..."

  reference:
    type: SELF_VERSION_BASELINE
    id: "..."

  environment_id: "..."
```

Partition totals should only be required to reconcile when the instrumentation claims full partition coverage.

---

## 34. Candidate system-performance record

```yaml
performance_sample:
  metric_id: SAVE_CONFIRMATION_LATENCY
  sample_id: "..."
  software_build: "..."
  environment_id: "..."
  workload_id: "..."
  cache_state: WARM
  start_event: SAVE_ACTIVATED
  end_event: DURABLE_SUCCESS_VISIBLE
  duration_ms: 438
  result: SUCCESS
```

A benchmark report can aggregate this later, but the raw sample remains authoritative.

---

## 35. Comparison quality levels

R03 recommends grading **comparison validity**, not performance quality, before any timing delta is interpreted.

### `C1 — STRONG_COMPARABILITY`

Same scenario semantics, outcome, evaluator/profile, environment and measurement method; only intended software variable differs.

### `C2 — CONTROLLED_DIFFERENCE`

One or more declared factors differ but are understood and unlikely to dominate the measured result.

### `C3 — CONTEXTUAL_COMPARISON`

Useful business comparison, e.g. paper workflow vs software, but method/environment necessarily differ.

### `C4 — NON_COMPARABLE`

Materially different task/outcome/context or unknown measurement method.

C4 data may be shown as context but must not drive a regression claim.

Final use in scoring belongs to R04.

---

## 36. Threshold adoption rules

R03 permits a time/performance threshold only when its source is classified.

### Valid origins

1. `USER_NEED`
2. `BUSINESS_REQUIREMENT`
3. `CONTRACT_OR_SLA`
4. `SAFETY_OR_REGULATORY_REQUIREMENT`
5. `EMPIRICAL_INTERNAL_BASELINE_TARGET`
6. `VALID_EXTERNAL_REFERENCE`
7. `PLATFORM_STANDARD_OR_GUIDANCE`

### Required metadata

```text
threshold_value
unit
metric_definition
origin_type
source/reference
version/date
applicable_context
rationale
```

### Forbidden

A benchmark author must not convert a convenient round number into a supposed standard without evidence.

---

## 37. No-target Phase 1 policy

For new projects without baseline data, R03 recommends:

```text
REFERENCE = NO_REFERENCE_RAW
```

The framework still records:

- raw times;
- outcome;
- interaction diagnostics;
- environment;
- repeated runs;
- system latency distribution where available.

After sufficient stable data exists, an accepted build/run can become a `SELF_VERSION_BASELINE`.

This is preferable to inventing a target before any evidence exists.

---

## 38. Enterprise productivity derivations

Project profiles may later derive operational/business metrics from task-time evidence.

Examples:

### Estimated labor time saved

```text
TIME_SAVED_PER_TASK * TASK_FREQUENCY
```

### Annualized time saved

```text
TIME_SAVED_PER_TASK * ANNUAL_TASK_COUNT
```

### Self-service administrative savings

```text
LEGACY_SUPPORT_TIME - SELF_SERVICE_TASK_TIME
```

These are business-value metrics, not generic quality scores, and require domain frequency/cost assumptions.

---

## 39. Counter-evidence / alternative positions considered

### 39.1 `Use arithmetic mean for all task times`

Rejected as universal default because human task times are often positively skewed and small usability samples can be poorly represented by arithmetic mean alone. [S14]

Arithmetic mean remains useful for some expected aggregate resource/cost interpretations.

### 39.2 `Use median only`

Not adopted as sole default. The human-task-time literature found geometric mean can better estimate the population center for small skewed samples. [S14]

R03 therefore keeps both where useful.

### 39.3 `Use a universal 0.1 / 1 / 10 second interaction rule`

Rejected as a generic SQBF threshold. Historical UI-response heuristics can be useful design guidance but do not establish universal compliance for modern heterogeneous software/business workflows. R03 instead requires threshold provenance.

### 39.4 `Fewer clicks always means more efficient`

Rejected. Click/action count does not capture reading complexity, interpretation, error prevention or task correctness.

### 39.5 `Only measure successful task time`

Rejected as the only timing evidence. Successful time is the cleanest efficiency measure, but failure, abandonment and false success have important separate durations/outcomes. [S11, S20]

### 39.6 `Average latency is enough`

Rejected for variable/production-like system latency because tail behaviour can be hidden by averages. [S16]

### 39.7 `Core Web Vitals should be the generic performance score`

Rejected. They are valuable browser/web metrics but do not cover arbitrary business-task duration, backend capacity, native software or non-web contexts.

### 39.8 `AI wall-clock time can stand in for human time`

Rejected on construct-validity grounds. AI execution includes evaluator/runtime properties not present in humans.

---

## 40. Contradictions / disagreements

| Conflict ID | Source/position A | Source/position B | Type | Resolution | Impact |
|---|---|---|---|---|---|
| C03-01 | usability guidance often speaks of average task time | task-time research shows positive skew and small-sample issues | STATISTICAL | Store raw data; use appropriate summaries; no unexplained `average` | affects reporting |
| C03-02 | successful-task time is clean efficiency measure | whole user experience includes failures/abandonment | CONSTRUCT | report successful time and failure-time strata separately | avoids fast-failure bias |
| C03-03 | arithmetic mean captures expected burden | geometric mean better estimates typical center in small skewed task samples | ESTIMAND | retain both when they answer different questions; do not pretend one is universally correct | reporting metadata must state estimand |
| C03-04 | web platforms have explicit performance thresholds | ISO product measurement avoids universal ranges | SCOPE | platform threshold valid only inside its applicable platform/metric definition | no generic threshold contamination |
| C03-05 | total wall-clock AI run is easy to measure | evaluator compute/runtime contributes to that time | CONSTRUCT | label AI task time; same-evaluator comparisons only until R05 calibration | critical for AI-first benchmark |
| C03-06 | cold-start can look like an outlier | cold-start may be real user experience | EXPERIMENTAL | stratify cold/warm; never silently trim | environment metadata required |

---

## 41. Recommendations

### RECOMMENDATION R03-01 — Make outcome-conditioned task timing a core schema requirement

Every timed task must have explicit outcome + timestamps.

**Evidence basis:** F03-05, F03-06, I03-01.

### RECOMMENDATION R03-02 — Store raw timing records before any report aggregate

Markdown reports are views; structured raw runs remain the data source.

**Evidence basis:** F03-09, F03-14.

### RECOMMENDATION R03-03 — Adopt the dual temporal model

Use:

- exclusive elapsed-time partitions; and
- overlapping diagnostic phase tags.

**Evidence basis:** I03-02, I03-03.

### RECOMMENDATION R03-04 — Label AI timing as evaluator-specific

Do not advertise it as human task time.

**Evidence basis:** I03-04.

### RECOMMENDATION R03-05 — Keep user/task efficiency separate from product performance

A future report should be able to show both:

```text
Task completion: 145 s
Application wait within task: 12 s
Save p95: 620 ms
```

without collapsing them into the same raw metric.

**Evidence basis:** F03-01, I03-05.

### RECOMMENDATION R03-06 — Begin BLE with raw time + self-baseline, not invented target times

For workflows without defensible target data, first runs should establish versioned baselines. Legacy-process measurements can be added later.

**Evidence basis:** F03-04, I03-07, I03-08.

### RECOMMENDATION R03-07 — Create a future `WEB_APP` platform profile

It may adopt browser instrumentation and Core Web Vitals independently from generic task efficiency.

**Evidence basis:** F03-11, F03-12, I03-12.

### RECOMMENDATION R03-08 — Preserve tail performance

For system latency use distributions/percentiles appropriate to sample size and workload, not mean alone.

**Evidence basis:** F03-10.

### RECOMMENDATION R03-09 — Never auto-delete slow timing observations

Only documented invalid-run reasons can exclude a run.

**Evidence basis:** I03-10.

### RECOMMENDATION R03-10 — Record comparison validity

Before/after claims should carry a comparability class (C1–C4) so future reports can distinguish controlled regressions from contextual comparisons.

**Evidence basis:** F03-03, F03-09, I03-08.

---

## 42. Open questions

### OPEN-03-01 — Minimum AI run count for stable timing comparison

**Why unresolved:** Depends on evaluator variance measured empirically; R05 owns calibration/repeatability.

**Blocking:** NO for raw timing collection; YES before strong statistical AI regression gates.

**Unblock condition:** R05 repeated-run experiments.

### OPEN-03-02 — Exact percentile sample-size policy

**Why unresolved:** Different metric distributions and use cases require different minimum sample counts. R03 establishes the principle but not final automated thresholds.

**Blocking:** NO for raw collection.

**Unblock condition:** R04 statistical/scoring research + implementation validation.

### OPEN-03-03 — Final confidence interval method per run type

**Why unresolved:** AI repeated runs and human participant samples have different estimands and dependence assumptions.

**Blocking:** NO for MVP raw reports.

**Unblock condition:** R04/R05 and later human-methodology research.

### OPEN-03-04 — Whether AI evaluator compute can be instrumented reliably in Astra/Fable/Opus runners

**Why unresolved:** Depends on provider/harness telemetry available during implementation.

**Blocking:** NO.

**Fallback:** Store total AI task time, application-wait observations where defensible, and evaluator identity; do not make cross-model timing claims.

### OPEN-03-05 — Which system performance metrics become mandatory for every project

**Why unresolved:** A web LIMS, mobile app and backend service have different performance surfaces.

**Blocking:** NO.

**Unblock condition:** Platform-profile design during synthesis/implementation.

### OPEN-03-06 — BLE legacy-process baselines

**Why unresolved:** User has not yet measured current paper/legacy workflow durations.

**Blocking:** NO for Foundation; project-profile timing remains `NO_REFERENCE_RAW` initially.

**Unblock condition:** R09 / later real-world baseline capture.

### OPEN-03-07 — Current SQuaRE measurement revisions at Foundation freeze

**Why unresolved:** ISO/IEC CD 25000-22 and ISO/IEC DIS 25000-23 are under development in 2026.

**Blocking:** NO now.

**Unblock condition:** Re-check source status immediately before Benchmark Foundation 1.0 freeze.

---

## 43. Risks and limitations

### 43.1 AI computer-use timing is not human timing

This is the most important limitation for the initial AI-first benchmark.

### 43.2 Fine-grained attribution may exceed instrumentation quality

Black-box screenshots cannot always distinguish evaluator thinking from application delay. Unknown attribution is preferable to invented precision.

### 43.3 Baseline drift

Changing fixtures, data volume, network, browser, hardware or evaluator version can create false performance trends.

### 43.4 Optimization can harm other quality dimensions

Faster is not automatically better if speed comes from:

- removing validation;
- hiding status information;
- skipping confirmation;
- weakening security;
- reducing evidence/auditability;
- increasing errors.

Outcome/gates remain authoritative.

### 43.5 Small-run statistics

Three AI runs can show obvious regressions but cannot justify precise population percentile claims.

### 43.6 External benchmark misuse

Published performance numbers are often workload-specific. Similar product category does not guarantee comparability.

### 43.7 Draft standard churn

Current SQuaRE measurement revisions may change details before Foundation 1.0 freezes.

---

## 44. Confidence per major conclusion

| Conclusion | Confidence | Main reason |
|---|---|---|
| Outcome must precede timing interpretation | HIGH | standards/guidance + construct validity |
| Task time and product latency are separate constructs | HIGH | ISO quality model boundary |
| No universal business-task time threshold | HIGH | ISO product-measurement guidance + context dependence |
| Raw per-run timing must be retained | HIGH | ACM benchmark guidance |
| Human task times are often positively skewed | HIGH | peer-reviewed CHI evidence |
| Geometric mean is useful for small human task-time samples | HIGH | Sauro/Lewis simulations |
| Tail latency needs percentile reporting | HIGH | established SRE operational guidance |
| AI wall-clock time is not human task time | HIGH | construct-validity reasoning |
| Cold/warm state must be stratified when material | HIGH | benchmark context/validity principles |
| Core Web Vitals belong to a web platform profile | HIGH | metric scope + platform-specific threshold source |
| Expert workflows may weight time more strongly | MEDIUM-HIGH | empirical familiarity study; generalization limited |
| Exact AI timing statistics/run count | LOW / OPEN | requires R05 empirical calibration |

---

## 45. Implications for later modules

### R04 — Scoring / normalization / statistics

Must decide:

- how raw task time becomes 0–100 when a valid reference exists;
- how `NO_REFERENCE_RAW` behaves in scoring;
- whether geometric mean/median enters score calculation;
- confidence/comparability weighting;
- percentile sample requirements;
- non-compensation rules;
- how performance and task efficiency contribute without double counting.

### R05 — AI evaluator reproducibility

Must empirically determine:

- repeated-run variance;
- same-model stability;
- model/provider version impact;
- cross-model comparability;
- required run counts;
- whether evaluator compute can be isolated;
- evaluator calibration suite.

### R07 — Accessibility / reliability / resilience

Must own:

- timeout/retry behaviour;
- recoverability/fault tolerance;
- degraded mode;
- reliability under load/failure;
- accessibility-related timing concerns where applicable.

### R08 — Persona/scenario model

Must formalize:

- FIRST_USE / TRAINED / EXPERIENCED timing strata;
- scenario start/end predicates;
- domain waiting treatment;
- task frequency metadata;
- assisted/unaided modes.

### R09 — ELVA-BLE evidence inventory/profile

Must identify:

- critical high-frequency laboratory tasks;
- workflows where legacy baseline measurement is useful;
- physical/domain waiting periods;
- expected performance-sensitive screens/actions;
- current system instrumentation possibilities;
- business-relevant task frequencies.

### R10 / synthesis

Must freeze:

- raw timing schema;
- platform profiles;
- current standards versions;
- performance-report sections;
- future local dashboard data requirements.

---

## 46. Proposed generic report output

A future Markdown report should be able to show a task like this without implying unsupported precision:

```text
Scenario: PRODUCT_CREATE_01
Evaluator: Astra <version>
Experience profile: FIRST_USE
Outcome: PASS_CORRECT

AI evaluator task time:
  Run 1: 138.2 s
  Run 2: 125.9 s
  Run 3: 131.4 s

Median: 131.4 s
Geometric mean: 131.7 s
Reference: SELF_VERSION_BASELINE
Baseline median: 159.0 s
Relative change: -17.4%
Comparison validity: C1

Observed application wait:
  13.8 s (high-confidence intervals only)

Interaction diagnostics:
  Backtracks: 2
  Help used: no
  Invalid attempts: 1

Human task-time claim:
  NOT AVAILABLE — AI benchmark only
```

And system performance separately:

```text
SAVE_CONFIRMATION_LATENCY
n: 500
p50: 210 ms
p95: 480 ms
p99: 910 ms
errors: 0
cache state: WARM
workload: <versioned workload id>
```

---

## 47. Research acceptance criteria verification

- [x] Reproducible timing start/end contract defined.
- [x] Task-time outcome conditioning defined.
- [x] Additive time partitions separated from overlapping diagnostic tags.
- [x] AI evaluator overhead/timing identity explicitly separated from human-time claims.
- [x] Task efficiency and product performance separated.
- [x] Baseline/target taxonomy defined without arbitrary universal thresholds.
- [x] Statistical treatment of skewed task time and tail latency documented.
- [x] Failed/abandoned/false-success timing treated separately.
- [x] Outlier/invalid-run policy documented.
- [x] System-performance environment/workload metadata defined.
- [x] Cold/warm state handled.
- [x] Platform-specific web metrics kept outside generic core.
- [x] Current measurement-standard transition documented.
- [x] Counter-evidence/alternative approaches considered.
- [x] No final score formula made authoritative.
- [x] Open questions delegated to downstream research.

---

## 48. Research completion gate

```text
RESEARCH STATUS: COMPLETE
PRIMARY SOURCES COVERED: YES
CONTRADICTIONS RESOLVED OR DOCUMENTED: YES
FACTS / INFERENCES / RECOMMENDATIONS SEPARATED: YES
OPEN QUESTIONS DOCUMENTED: YES
CONFIDENCE: HIGH
READY FOR SYNTHESIS: YES
```

---

## 49. Executive research conclusion

R03 rejects the idea of a single undifferentiated `time` metric.

SQBF should measure time through a strict contract:

```text
Correct outcome first
        ↓
Reproducible task elapsed time
        ↓
Optional attributed/diagnostic timing
        ↓
Separate product-performance measurements
        ↓
Explicit baseline/reference
        ↓
Only then scoring/threshold interpretation
```

For the initial AI-first BLE benchmark, task time is immediately useful as a **versioned raw metric and same-evaluator regression measure**. It is not a substitute for human time-on-task.

Where no defensible target exists, SQBF should preserve `NO_REFERENCE_RAW` rather than inventing a score. The first stable runs become baselines; legacy process times can later provide business-efficiency comparisons.

Product performance must additionally preserve latency distributions, workload/environment, resource usage and capacity. Tail behaviour, cold/warm state and raw samples matter because averages can hide material user-facing regressions.

This gives the future benchmark platform a clean path from today's Markdown reports to longitudinal enterprise quality dashboards without corrupting the meaning of timing data.