# R01 — Generic Software Quality Model

- **Research ID:** R01
- **Version:** 1.0.0
- **Date:** 2026-09-09
- **Issue:** #3
- **Repository:** `Creynox/software-quality-benchmark`
- **Governing methodology:** `research/R00-research-methodology/R00-research-methodology.md`
- **Research type:** Standards-led structured evidence review with model-boundary analysis
- **Status:** COMPLETE

## 1. Question / objective

Define the project-independent quality taxonomy that the Software Quality Benchmark Framework (SQBF) should use as its generic foundation.

R01 answers the following questions:

1. Which software/ICT quality dimensions should the generic benchmark distinguish?
2. Which concerns belong to **product quality**, which belong to **quality in use**, and which belong to **engineering/process assurance**?
3. Which characteristics are related but must remain separately observable to avoid hidden trade-offs?
4. Which quality concerns are plausible score dimensions, which are plausible non-compensable gate dimensions, and which decisions must be deferred to later modules?
5. How should security, safety, reliability, accessibility, performance, maintainability and functional correctness be positioned without double-counting?
6. Which concerns belong in the generic core and which belong in project-, domain- or technology-specific extensions?
7. Which later research module owns detailed operationalization of each concern?

The goal is a **taxonomy and boundary contract**, not a final scoring system.

---

## 2. Scope

R01 covers:

- the current SQuaRE product-quality and quality-in-use model structure;
- the separation of product properties from outcomes in a context of use;
- the separation of product quality from software-development process capability;
- the role of project/domain extensions such as data quality and AI-system quality;
- overlap and double-counting risks;
- a proposed generic benchmark architecture;
- assignment of detailed measurement questions to R02–R11;
- candidate score/gate classification without numeric weights or thresholds.

---

## 3. Explicitly out of scope

R01 does **not** define:

- metric formulas;
- 0–100 normalization;
- weights;
- pass/fail thresholds;
- task-time formulas;
- AI-evaluator repeatability rules;
- detailed OWASP/security controls;
- WCAG conformance criteria;
- detailed reliability/resilience scenarios;
- code-quality metrics;
- CI/CD maturity measures;
- project-specific personas or workflows;
- BLE-specific business rules;
- the benchmark runner implementation;
- the future local benchmark web application.

Those belong to later modules.

---

## 4. Method

R01 follows R00's claim-type-first evidence model.

### 4.1 Review strategy

The research first identified the current official ISO/IEC SQuaRE model standards and their status, then checked the surrounding SQuaRE series for measurement and extension boundaries. Process-quality standards were reviewed only to determine whether engineering-process quality should be merged into the same taxonomy. Secondary sources were then used to:

- confirm publicly visible characteristic names where the full normative standard text is not freely reproduced;
- identify domain-specific quality-model gaps;
- search for evidence that ISO/IEC 25010 alone should not be treated as an exhaustive ontology for every software context;
- identify construct-overlap risks between product quality and quality in use.

R01 is not a formal systematic literature review. It is a standards-led structured evidence review under R00.

### 4.2 Representative search log

Research date: 2026-09-09.

Representative queries included:

- `ISO/IEC 25010:2023 software quality model official ISO product quality characteristics`
- `ISO/IEC 25019:2023 quality in use model official ISO`
- `ISO/IEC 25002:2024 quality model overview and usage`
- `ISO 25000 SQuaRE series divisions`
- `ISO/IEC 25020 quality measurement framework`
- `ISO/IEC 25012 data quality model`
- `ISO/IEC 25059 AI quality model`
- `ISO/IEC 12207 software lifecycle processes`
- `ISO/IEC 33020 process capability`
- `ISO IEC 25019 beneficialness freedom from risk acceptability`
- `systematic review software quality models ISO 25010 alternatives`
- `software quality assessment model systematic mapping study`

### 4.3 Counter-evidence search

The review explicitly searched for cases where:

- ISO/IEC 25010 was insufficient for a specialized context;
- alternative quality models exposed dimensions outside the SQuaRE product model;
- quality-in-use evaluations collapsed into usability only;
- process or ecosystem quality was incorrectly treated as product quality.

The result is reflected in Sections 8, 9 and 15.

---

## 5. Source register

### 5.1 Primary / authoritative sources

| ID | Source | Class | Status | Role in R01 |
|---|---|---|---|---|
| S01 | ISO/IEC 25010:2023, *SQuaRE — Product quality model* — https://www.iso.org/standard/78176.html | NORMATIVE_STANDARD | CURRENT / PUBLISHED | Defines the current product-quality model and confirms nine characteristics |
| S02 | ISO/IEC 25019:2023, *SQuaRE — Quality-in-use model* — https://www.iso.org/standard/78177.html | NORMATIVE_STANDARD | CURRENT / PUBLISHED | Defines the current quality-in-use model with three characteristics and explicit context-of-use dependency |
| S03 | ISO/IEC 25002:2024, *SQuaRE — Quality model overview and usage* — https://www.iso.org/standard/78175.html | NORMATIVE_STANDARD | CURRENT / PUBLISHED | Establishes quality-model structure/semantics and relation to measurement, requirements and evaluation |
| S04 | ISO/IEC JTC 1/SC 7, *ISO/IEC 25000 SQuaRE series* — https://committee.iso.org/sites/jtc1sc7/home/projects/flagship-standards/iso-25000-square-series.html | OFFICIAL_GUIDANCE | CURRENT | Confirms SQuaRE divisions: models, measurement, requirements, evaluation and extensions |
| S05 | ISO/IEC 25020:2019, *SQuaRE — Quality measurement framework* — https://www.iso.org/standard/72117.html | NORMATIVE_STANDARD | CURRENT / CONFIRMED | Separates quality models from measurement; covers product quality, quality in use, data quality and IT service quality measurement |
| S06 | ISO/IEC 25012:2008, *SQuaRE — Data quality model* — https://www.iso.org/standard/35736.html | NORMATIVE_STANDARD | CURRENT / CONFIRMED | Demonstrates separate data-quality model and extension need for data-centric projects |
| S07 | ISO/IEC 25059:2023, *SQuaRE — Quality model for AI systems* — https://www.iso.org/standard/80655.html | NORMATIVE_STANDARD | PUBLISHED; REVISION IN PROGRESS | Demonstrates application-specific extension of SQuaRE for AI systems |
| S08 | ISO/IEC/IEEE 12207:2026, *Software life cycle processes* — https://www.iso.org/standard/90219.html | NORMATIVE_STANDARD | CURRENT / PUBLISHED | Establishes software life-cycle processes and organizational/project process improvement scope |
| S09 | ISO/IEC 33020:2019, *Process measurement framework for assessment of process capability* — https://www.iso.org/standard/78526.html | NORMATIVE_STANDARD | CURRENT / CONFIRMED | Defines process capability as a process quality characteristic and supports capability assessment |
| S10 | ISO/IEC DIS 25023, *Measurement of product quality* — https://www.iso.org/obp/ui?_escaped_fragment_=iso%3Astd%3Aiso-iec%3A25023%3Adis%3Aed-1%3Av1%3Aen | NORMATIVE_STANDARD | DRAFT / NOT FINAL | Publicly exposes current 25010-aligned characteristic headings and revision notes; used only as draft corroboration, not final measurement authority |
| S11 | ISO/IEC CD 25000-22, *Measurement of quality-in-use* — https://www.iso.org/standard/92688.html | NORMATIVE_STANDARD | COMMITTEE DRAFT / NOT FINAL | Confirms that measurement guidance is being revised to align with ISO/IEC 25019; not authoritative for final metrics |

### 5.2 Secondary / interpretive sources

| ID | Source | Class | Role in R01 |
|---|---|---|---|
| S12 | Sonar, *ISO/IEC 25010 Explained: 9 Software Quality Characteristics* — https://www.sonarsource.com/resources/library/iso-iec-25010-explained/ | SPECIALIST_GUIDANCE | Publicly lists the nine 2023 product-quality characteristic names; used only to corroborate naming |
| S13 | arc42 Quality Model, *ISO/IEC 25019 — Quality-in-use model* — https://quality.arc42.org/standards/iso-25019 | SPECIALIST_GUIDANCE | Publicly summarizes the three quality-in-use characteristics/subcharacteristics; used as naming aid, not normative authority |
| S14 | Hastings & Reinhold (2026), *From Standards to Practice: A Position on Challenges in Operationalizing Software Quality-in-Use* — https://www.scitepress.org/PublishedPapers/2026/149259/ | PEER_REVIEWED_PRIMARY / POSITION | Warns that quality-in-use is often incorrectly reduced to usability-only evaluation |
| S15 | Adewumi et al. (2016), *A systematic literature review of open source software quality assessment models* — https://doi.org/10.1186/s40064-016-3612-4 | PEER_REVIEWED_SYNTHESIS | Shows specialized contexts can require quality concerns outside generic ISO product/quality-in-use characteristics, e.g. community/process properties |
| S16 | Yan et al., *Software quality assessment model: a systematic mapping study* — https://research.monash.edu/en/publications/software-quality-assessment-model-a-systematic-mapping-study/ | PEER_REVIEWED_SYNTHESIS | Distinguishes definition, assessment and prediction quality models; supports separation of taxonomy from metric implementation |
| S17 | Plevnik & Jereb (2026/2027), *Evaluating logistics software quality: A systematic review and research agenda for ISO/IEC 25010...* — https://www.sciencedirect.com/science/article/pii/S0920548926000619 | PEER_REVIEWED_SYNTHESIS | Domain review illustrating uneven applicability/emphasis of quality characteristics and need for domain profiles |

### 5.3 Source-status note

R01 does not reproduce copyrighted ISO standard text. Official ISO pages are used for standard identity, scope, status and publicly available summaries. Public secondary sources are used only to corroborate characteristic names/structure where necessary. Detailed operational definitions remain subject to licensed source access and later research.

---

## 6. Confirmed facts

### FACT F01-01 — The current SQuaRE product-quality model is ISO/IEC 25010:2023 and has nine characteristics

ISO/IEC 25010:2023 is the current published product-quality model. ISO states that it applies to ICT products and software products and contains nine characteristics subdivided into subcharacteristics. The model is intended as a reference for specifying, measuring and evaluating product quality. [S01]

Publicly corroborated characteristic names are:

1. Functional suitability
2. Performance efficiency
3. Compatibility
4. Interaction capability
5. Reliability
6. Security
7. Maintainability
8. Flexibility
9. Safety

The current ISO draft for product-quality measurement exposes the same nine section headings and states that the 2023 edition added safety, replaced the former usability characteristic with interaction capability, and replaced portability with flexibility. [S10, corroborated by S12]

**Confidence:** HIGH.

### FACT F01-02 — Quality in use is now a separate current model: ISO/IEC 25019:2023

ISO/IEC 25019:2023 defines quality in use separately from ISO/IEC 25010. ISO states that the model has three characteristics and that context of use is a prerequisite; when the intended context changes, the context must be re-specified. [S02]

Publicly documented characteristic names are:

1. Beneficialness
2. Freedom from risk
3. Acceptability

Secondary sources consistently summarize the current substructure as:

- Beneficialness → usability, accessibility, suitability;
- Freedom from risk → economic, environmental/societal, health, human-life risk concerns;
- Acceptability → experience, trustworthiness, compliance.

[S13, S14; naming also corroborated by recent research discussing ISO/IEC 25019]

**Confidence:** HIGH for top-level structure; MEDIUM-HIGH for detailed subcharacteristic naming because R01 relies on public summaries rather than licensed normative text.

### FACT F01-03 — Product quality and quality in use are different constructs

ISO/IEC 25010 addresses properties/capabilities of ICT/software products. ISO/IEC 25019 addresses stakeholder-relevant outcomes when a product/system is used in a specified context. ISO/IEC 25002 explicitly describes quality models as structures linked to requirements, measurement and evaluation. [S01, S02, S03]

**Confidence:** HIGH.

### FACT F01-04 — Quality models and measurement models are distinct

The SQuaRE family separates quality models (2501n) from quality measurement (2502n), requirements (2503n) and evaluation (2504n). ISO/IEC 25020 provides a measurement framework and explicitly discusses measure selection, construction, reliability/validity and measurement application across product quality, quality in use, data quality and IT service quality. [S04, S05]

**Implication:** A taxonomy is not yet a scoring model.

**Confidence:** HIGH.

### FACT F01-05 — SQuaRE explicitly supports extensions for specialized application domains

The official SQuaRE series description includes an extension division (25050–25099) for application-domain standards or complementary quality material. ISO/IEC 25059 is an application-specific SQuaRE extension for AI systems. [S04, S07]

**Confidence:** HIGH.

### FACT F01-06 — Data quality has a separate SQuaRE model

ISO/IEC 25012 defines a general data-quality model for structured data and is used for data-quality requirements, measurement and evaluation. [S06]

**Implication:** Data quality should not be silently collapsed into functional correctness or reliability.

**Confidence:** HIGH.

### FACT F01-07 — Software life-cycle/process capability is modeled separately from product quality

ISO/IEC/IEEE 12207:2026 establishes lifecycle processes for software systems/products/services and includes processes for defining, controlling and improving lifecycle processes. ISO/IEC 33020 provides a process-capability measurement framework and explicitly treats process capability as a process quality characteristic. [S08, S09]

**Implication:** `Engineering Quality` is not simply another ISO/IEC 25010 product characteristic.

**Confidence:** HIGH.

### FACT F01-08 — Specialized quality models can require concerns not represented as generic product characteristics

The open-source-software quality-model systematic review found domain/ecosystem concerns such as community sustainability and process maturity that are not represented by the generic product/quality-in-use characteristics. Specialized AI quality standards likewise extend SQuaRE rather than treating the generic model as sufficient without augmentation. [S07, S15]

**Confidence:** HIGH that extensions can be needed; LOW for any claim that a specific extension applies universally.

### FACT F01-09 — Quality in use is broader than usability

ISO/IEC 25019 contains three top-level characteristics, while usability is only part of beneficialness. Recent methodological literature specifically warns that evaluating quality in use only through usability measures misses acceptability, risk and broader stakeholder outcomes. [S02, S13, S14]

**Confidence:** HIGH.

### FACT F01-10 — The current measurement standards are in transition

ISO/IEC 25020:2019 remains current as the generic measurement framework. ISO/IEC 25022:2016 is being replaced by a new quality-in-use measurement work item aligned with ISO/IEC 25019, and a revised product-quality measurement standard is available as a draft. [S05, S10, S11]

**Implication:** R03/R04 must version measurement-source assumptions and must not treat draft formulas as final standards.

**Confidence:** HIGH.

---

## 7. Derived conclusions

### INFERENCE I01-01 — SQBF needs multiple quality planes, not one flat list

If product quality, quality in use and engineering-process quality are placed into one flat weighted list, the framework will mix:

- properties of the product;
- stakeholder outcomes in context;
- capability of the organization/process that created and operates the product.

These are related but not equivalent constructs. [F01-03, F01-07]

**Conclusion:** SQBF should model at least three distinct planes:

1. **Product Quality**
2. **Quality in Use**
3. **Engineering / Process Assurance**

and a fourth extension plane for project/domain-specific concerns.

**Confidence:** HIGH.

### INFERENCE I01-02 — ISO/IEC 25010 should be the generic product-quality backbone, not the entire benchmark ontology

ISO/IEC 25010 provides the strongest current standardized generic product-quality taxonomy, but the SQuaRE family itself contains separate quality-in-use, data-quality and application-specific extension models. Process capability also has its own standards. [F01-01, F01-02, F01-05, F01-06, F01-07]

**Conclusion:** Adopt 25010's nine top-level characteristics as the **generic product-quality backbone**, while explicitly allowing separate planes/extensions.

**Confidence:** HIGH.

### INFERENCE I01-03 — A quality characteristic should not automatically equal a top-level score

The presence of a characteristic in a quality model means it is a relevant category for requirements/evaluation, not that it must receive an independent equally weighted 0–100 score. Measurement validity, overlap, criticality and project applicability must be established later. [F01-04]

**Conclusion:** R01 only marks `SCORE_CANDIDATE`, `GATE_CANDIDATE`, or `CONTEXT_OUTCOME`; R04/R10 decide actual score structure.

**Confidence:** HIGH.

### INFERENCE I01-04 — Gates should be orthogonal to scores

A serious security, safety or functional-correctness failure can make a release unacceptable even if unrelated dimensions score highly. This is a logical consequence of risk-sensitive evaluation and cannot be represented safely by a compensating average.

**Conclusion:** SQBF must support non-compensable gates independently from numeric scores. The exact gate catalogue and thresholds are deferred to R04/R06/R07/R10 and project profiles.

**Confidence:** HIGH as framework architecture; specific default gates remain OPEN.

### INFERENCE I01-05 — Context is part of the identity of a quality-in-use result

Because ISO/IEC 25019 makes context of use a prerequisite, a quality-in-use score without persona, goals, device/environment, permissions and scenario context is not reproducible enough to compare across releases. [F01-02]

**Conclusion:** Project benchmark runs must bind quality-in-use results to a context profile. R08 will define the schema.

**Confidence:** HIGH.

### INFERENCE I01-06 — Domain profiles must extend, not mutate, the generic core

SQuaRE explicitly supports application-specific extensions, and research shows specialized contexts often emphasize or add concerns. [F01-05, F01-08]

**Conclusion:** `profiles/elva-ble`, `profiles/para-dos`, future AI/mobile/ERP profiles should be able to add domain rules, gates and weighting without changing the meaning of generic core characteristics.

**Confidence:** HIGH.

---

## 8. Alternative-model / counter-evidence findings

### 8.1 Older/general alternative models are not adopted as the primary taxonomy

McCall, Boehm, Dromey and FURPS remain historically important and are still used in comparative research. However, the current SQuaRE family provides a maintained international reference model and now explicitly separates product quality, quality in use and extensions.

**RECOMMENDATION:** Do not build a new hybrid top-level taxonomy by unioning every historical quality model. Use SQuaRE as the backbone and retain non-SQuaRE concerns as explicit extension candidates.

### 8.2 Domain-specific research demonstrates non-universal applicability

The OSS review [S15] shows community/ecosystem properties that matter to OSS but are not general product-quality characteristics. Logistics research [S17] shows uneven use/emphasis of ISO/IEC 25010 characteristics across a specialized domain.

**RECOMMENDATION:** The generic core must support `APPLICABLE`, `NOT_APPLICABLE`, `REQUIRED`, and profile-specific weighting/gate configuration rather than requiring identical importance everywhere.

### 8.3 Quality-in-use operationalization is a known weak point

The recent position paper [S14] identifies a recurring problem: empirical evaluations often reduce quality in use to interface usability. This would be especially problematic for a future SQBF dashboard, because a single `UX` score could appear to represent trust, risk and real-world outcomes when it does not.

**RECOMMENDATION:** Keep `Interaction / Usability` and broader `Quality in Use` visibly separate in the report model.

### 8.4 Quality assessment models are not the same as quality definition models

The mapping-study literature [S16] distinguishes quality definition models from assessment/prediction models.

**RECOMMENDATION:** R01 defines the quality model only. R03/R04 define assessment mechanics later.

---

## 9. Adopted provisional SQBF quality architecture

The following architecture is a **RECOMMENDATION** for Foundation 1.0 synthesis. It becomes authoritative only after R10.

```text
SQBF QUALITY MODEL
│
├── Plane A — PRODUCT QUALITY
│   ├── Functional Suitability
│   ├── Performance Efficiency
│   ├── Compatibility
│   ├── Interaction Capability
│   ├── Reliability
│   ├── Security
│   ├── Maintainability
│   ├── Flexibility
│   └── Safety
│
├── Plane B — QUALITY IN USE
│   ├── Beneficialness
│   ├── Freedom from Risk
│   └── Acceptability
│
├── Plane C — ENGINEERING / PROCESS ASSURANCE
│   ├── lifecycle/process capability
│   ├── test/verification assurance
│   ├── CI/CD and release assurance
│   ├── dependency/supply-chain assurance
│   ├── observability/operational assurance
│   └── documentation/change-control assurance
│
└── Plane D — PROJECT / DOMAIN EXTENSIONS
    ├── Data Quality
    ├── AI Quality
    ├── Service Quality
    ├── domain/regulatory rules
    ├── project-specific safety/compliance gates
    └── project-specific personas/workflows
```

### 9.1 Plane A — Product Quality

**Purpose:** Evaluate properties/capabilities of the software/ICT product itself.

**Backbone:** ISO/IEC 25010:2023.

**Rule:** The nine characteristics are the generic top-level coverage checklist. A project profile may mark dimensions as different importance or not applicable only with justification, but may not redefine the core meaning.

### 9.2 Plane B — Quality in Use

**Purpose:** Evaluate whether stakeholders achieve beneficial, acceptable and sufficiently low-risk outcomes in a specified context of use.

**Backbone:** ISO/IEC 25019:2023.

**Rule:** Every quality-in-use result is context-bound; no context-free global user score.

### 9.3 Plane C — Engineering / Process Assurance

**Purpose:** Evaluate whether the engineering system that produces/releases/operates software is capable, controlled and evidence-producing.

**Backbone candidates:** ISO/IEC/IEEE 12207, ISO/IEC 330xx, secure-development sources (later R06/R11), testing standards and repository/CI evidence.

**Rule:** This plane must not be used as a proxy for actual product quality. A mature process can still produce a defective product; a good product snapshot does not prove a mature process.

### 9.4 Plane D — Project / Domain Extensions

**Purpose:** Add concerns that are real but not universally applicable.

Examples:

- LIMS/WPK domain correctness and auditability;
- medical or industrial safety requirements;
- AI-specific characteristics;
- structured data quality;
- service-level quality;
- mobile-platform constraints;
- organization-specific governance.

**Rule:** Extensions cannot silently overwrite generic core definitions.

---

## 10. Product-quality dimension map

The descriptions below are framework paraphrases, not reproductions of ISO standard text.

| Dimension | What SQBF should ask at a high level | Initial classification | Detailed owner |
|---|---|---|---|
| Functional Suitability | Does the product provide the required functions, correctly and appropriately for intended tasks? | SCORE_CANDIDATE + GATE_CANDIDATE for critical correctness/completeness | R10 + project profile; functional test evidence |
| Performance Efficiency | Does the product meet time/resource/capacity expectations under defined conditions? | SCORE_CANDIDATE + threshold/gate capable | R03 |
| Compatibility | Can it coexist and interoperate as required with other products/systems? | SCORE_CANDIDATE + project gate capable | R10/project profile |
| Interaction Capability | Can users recognize, learn, operate and get assistance from the product while being protected from interaction errors and exclusion? | SCORE_CANDIDATE | R02/R07 |
| Reliability | Does it remain available/correct enough, tolerate faults and recover as required? | SCORE_CANDIDATE + GATE_CANDIDATE | R07 |
| Security | Does it preserve required security properties against threats and misuse? | SCORE_CANDIDATE only if construct-valid + strong GATE_CANDIDATE | R06 |
| Maintainability | Can the product be analyzed, modified, tested and reused/modularized with acceptable effort/risk? | SCORE_CANDIDATE | R11 |
| Flexibility | Can it adapt, scale, install/replace/fit changed environments as required? | SCORE_CANDIDATE | R11/project profile |
| Safety | Does the product avoid or control unacceptable harm arising from operation, failure or integration? | Primarily GATE_CANDIDATE; score may exist only where meaningful | R07 + domain profile |

**Important:** `GATE_CANDIDATE` means the framework must support a hard gate for this construct. It does not mean every project has the same gate threshold.

---

## 11. Quality-in-use dimension map

| Dimension | What SQBF should ask at a high level | Initial classification | Detailed owner |
|---|---|---|---|
| Beneficialness | In this context, does use of the system actually help stakeholders achieve useful goals with acceptable usability/accessibility/suitability? | CONTEXT_OUTCOME + SCORE_CANDIDATE | R02/R03/R07/R08 |
| Freedom from Risk | In this context, does use of the system avoid/mitigate unacceptable economic, societal/environmental, health or life consequences? | CONTEXT_OUTCOME + strong GATE_CANDIDATE | R06/R07 + project profile |
| Acceptability | In this context, is adoption/use acceptable in terms of stakeholder experience, justified trust and applicable compliance expectations? | CONTEXT_OUTCOME + SCORE/GATE depending subconstruct | R02/R06/R08 + project profile |

### 11.1 Why this is not just `UX`

A user can complete an interface task quickly and still experience poor quality in use if:

- the result is not useful for the actual job;
- the user cannot justifiably trust it;
- use creates unacceptable business/safety risk;
- required compliance is not satisfied;
- the product excludes relevant users or contexts.

Therefore SQBF should report **Interaction/Usability** and **Quality in Use** separately.

---

## 12. Double-counting and construct-overlap matrix

R01 identifies the following overlap risks that later measurement modules MUST handle explicitly.

### 12.1 Performance Efficiency vs user Efficiency

- Product performance: response time, resource usage, capacity and system behavior.
- User/task efficiency: resources/time a user expends to achieve a goal.

A fast server can support a slow workflow; a well-designed workflow can still be slowed by poor system performance.

**Rule:** R03 must keep `SYSTEM_PERFORMANCE` and `USER_TASK_EFFICIENCY` as distinct raw-metric families.

### 12.2 Interaction Capability vs Quality-in-Use Usability

Interaction capability concerns product properties that enable effective interaction. Quality-in-use usability concerns outcome in a defined context.

**Rule:** Do not score the same task-success/time/help observation twice under both layers. A measure must have one primary construct or an explicitly defined derived relationship.

### 12.3 Interaction inclusivity/user assistance vs Accessibility outcome

The product can expose inclusive/helpful interaction capabilities, while accessibility quality in use asks whether relevant people can actually achieve goals in context.

**Rule:** R07 must distinguish enabling product properties from observed accessibility outcomes.

### 12.4 Functional Suitability vs Quality-in-Use Suitability

Functional suitability asks whether required functionality is present/correct/appropriate. Quality-in-use suitability concerns whether behaviors/outcomes satisfy relevant quality needs when used.

**Rule:** A functional test result must not automatically count as a quality-in-use outcome.

### 12.5 Reliability vs Safety

Reliability concerns continued/dependable operation and recovery. Safety concerns unacceptable harm.

A system can be highly reliable while reliably doing something unsafe, and a safety-designed system can fail while still moving to a safe state.

**Rule:** Keep separate dimensions and allow safety gates independent of reliability scores.

### 12.6 Product Safety vs Freedom from Risk

Product safety represents safety-related properties of the product; freedom from risk is a contextual outcome for stakeholders and can include economic, environmental/societal and health/life consequences.

**Rule:** Product safety evidence can contribute to a risk evaluation but cannot replace contextual risk outcome analysis.

### 12.7 Security vs Trustworthiness

Technical security properties and stakeholder trust are not equivalent.

A user can trust an insecure system; a secure system can be distrusted because it is opaque or confusing.

**Rule:** R06 must keep security assurance separate from perceived/justified trust outcome.

### 12.8 Maintainability vs Engineering Process Capability

Maintainability is a product property. Process capability concerns how consistently the organization/project executes engineering processes.

**Rule:** R11 must not infer one from the other.

### 12.9 Functional Correctness vs Data Quality

A function can implement its specification correctly while operating on incomplete/inaccurate/invalid data; conversely, high-quality data does not prove correct logic.

**Rule:** Data quality remains an extension plane when materially relevant.

---

## 13. Provisional gate architecture

R01 does not define final gates, but it defines the **architecture required to support them**.

### 13.1 Non-compensable gate principle

A gate result is evaluated separately from numeric scores.

Provisional report semantics:

```text
Dimension scores: available
Overall index: available only if policy allows
Critical gates: PASS / FAIL / NOT_EVALUATED
Release eligibility: ELIGIBLE / NOT_ELIGIBLE / UNDETERMINED
```

### 13.2 Generic gate candidates

The framework should be able to attach gates to at least:

- critical functional correctness/completeness;
- security/access control/data protection;
- safety/harm prevention;
- reliability/recoverability for critical workflows;
- scope/tenant isolation where multi-tenant or scoped data exist;
- data integrity / false-success conditions;
- accessibility when legally/contractually/product-critically required;
- compliance/domain obligations;
- quality-in-use freedom-from-risk outcomes.

These are **candidates**, not universal mandatory gates.

### 13.3 Why not universalize gates in R01

A couples mobile app, an internal ERP module and an industrial LIMS do not have identical safety, audit or availability criticality. R10/project profiles must assign gate policy based on risk/context rather than pretending every project has identical failure consequences.

---

## 14. Generic-core vs project-profile boundary

### 14.1 Generic core owns

- names and semantics of generic quality planes;
- common metric/event vocabulary;
- score/gate mechanics;
- evaluator metadata;
- evidence model;
- versioning model;
- generic scenario/persona schema;
- generic report structure;
- generic product-quality and quality-in-use taxonomy;
- reusable security/accessibility/reliability benchmark contracts.

### 14.2 Project profile owns

- project personas;
- role/permission models;
- workflows;
- domain terms;
- domain correctness rules;
- criticality classification;
- domain-specific gates;
- applicable quality-dimension selection;
- project baselines/targets;
- test fixtures;
- project-specific security boundaries;
- regulatory/contractual requirements;
- product-specific acceptable time/availability/error thresholds.

### 14.3 Technology/domain extension owns

Examples:

- AI extension;
- data-quality extension;
- mobile interaction/platform extension;
- cloud/service-quality extension;
- regulated medical/industrial extension;
- open-source/community extension.

**Boundary rule:** A project-specific concern may become a generic extension only after evidence shows it is reusable beyond one project. It must not enter the generic core merely because ELVA-BLE needs it.

---

## 15. Applicability and profiling model

R01 recommends that every generic characteristic can be assigned a project-profile applicability state:

```text
REQUIRED
APPLICABLE
NOT_APPLICABLE
DEFERRED
UNKNOWN
```

Definitions:

- `REQUIRED` — project profile treats the dimension as mandatory for benchmark completion.
- `APPLICABLE` — dimension is relevant and measured where scenarios/evidence exist.
- `NOT_APPLICABLE` — justified exclusion for the project/release context.
- `DEFERRED` — intentionally postponed to a later benchmark maturity level.
- `UNKNOWN` — applicability not yet decided; should reduce benchmark completeness confidence.

**RECOMMENDATION:** `NOT_APPLICABLE` must require rationale. Otherwise projects could artificially improve benchmark scores by removing difficult dimensions.

---

## 16. Proposed relationship to later research modules

| Research | Primary responsibility after R01 |
|---|---|
| R02 — Usability & Interaction | Interaction capability, usability outcomes, discoverability, learnability, help, feedback, error prevention/recovery, satisfaction-related constructs |
| R03 — Time, Efficiency & Performance | Product performance vs user/task efficiency, system wait time, task time, resource/capacity measures |
| R04 — Scoring / Normalization / Statistics | Metric-to-score transformation, weighting, aggregation, uncertainty, baseline/target logic, gate/score interaction |
| R05 — AI Evaluator Reproducibility | Reliability of AI-produced observations/scores, repeat runs, evaluator identity/calibration, leakage control |
| R06 — Security Assurance | Security dimension, black/white-box controls, security hard gates, technical trust evidence |
| R07 — Accessibility / Reliability / Resilience | accessibility outcomes/enablers, reliability, recovery, resilience, safety interaction and relevant gates |
| R08 — Persona / Skill / Scenario Model | context-of-use identity, personas, skills, permissions, device/environment, scenario contracts |
| R09 — ELVA-BLE Evidence Inventory | project profile evidence only; no generic-core mutation |
| R10 — Foundation Synthesis | final taxonomy, score/gate architecture, conflict resolution across R01–R09 |
| R11 — Engineering Quality | maintainability operationalization, lifecycle/process assurance, testing/CI/CD/dependency/observability/documentation quality |

---

## 17. Recommended report hierarchy

R01 recommends that later benchmark Markdown/JSON reports avoid one undifferentiated quality number at the top.

Provisional hierarchy:

```text
Software Quality Benchmark
│
├── Product Quality
│   ├── Functional Suitability
│   ├── Performance Efficiency
│   ├── Compatibility
│   ├── Interaction Capability
│   ├── Reliability
│   ├── Security
│   ├── Maintainability
│   ├── Flexibility
│   └── Safety
│
├── Quality in Use
│   ├── Beneficialness
│   ├── Freedom from Risk
│   └── Acceptability
│
├── Engineering Assurance
│   └── ... R11
│
├── Project Extensions
│   └── ... project profile
│
└── Gates
    ├── Critical pass/fail results
    └── Release eligibility
```

A later UI may visualize this as separate dashboards/radars/trends, but the information architecture should already exist in the Markdown/structured result model.

---

## 18. Rejected alternatives

### REJECTED A01 — One `UX Score` as the primary software-quality score

Reason: UX does not cover functional correctness, reliability, security, maintainability, compatibility, safety or process assurance. Quality in use itself is broader than usability. [S01, S02, S14]

### REJECTED A02 — One flat weighted list containing product, user and process quality

Reason: mixes distinct constructs and makes interpretation/causal diagnosis weak. Product outcome and process capability are not equivalent. [S01, S02, S08, S09]

### REJECTED A03 — ISO/IEC 25010 alone as the complete enterprise testing framework

Reason: SQuaRE itself has separate quality-in-use, data-quality and application-specific models; lifecycle/process capability is outside the product model. [S02, S04, S06, S07, S08, S09]

### REJECTED A04 — Invent a custom top-level taxonomy now

Reason: unnecessary loss of interoperability with a maintained international model before evidence shows a concrete gap. Specialized concerns can be extensions.

### REJECTED A05 — Treat all dimensions as equally weighted

Reason: no evidence supports universal equal importance across application domains, and critical risks cannot be safely represented by pure averaging. Weighting belongs to R04/R10/project profiles.

### REJECTED A06 — Treat security/safety only as numeric sub-scores

Reason: high unrelated scores could compensate for unacceptable critical failure. Gate support is required.

### REJECTED A07 — Treat every technical issue as a hard gate

Reason: would make the benchmark unusable and destroy severity/risk discrimination. Gate policy must be risk- and profile-driven.

---

## 19. Risks and limitations

### LIMITATION L01 — Full ISO text was not ingested

R00's copyright/AI-use rule prevents indiscriminate ingestion/reproduction of licensed ISO content. R01 therefore relies on official abstracts/status pages plus public corroboration for detailed naming.

**Impact:** Top-level architecture confidence is high; detailed subcharacteristic semantics should be rechecked against licensed standards if the framework later claims formal ISO conformance.

### LIMITATION L02 — ISO/IEC 25019 operationalization is comparatively new

The 2023 quality-in-use model is newer than much of the empirical usability literature, and current measurement guidance is still being revised.

**Impact:** R02/R03/R04 should not assume mature empirical benchmarks exist for every new quality-in-use construct.

### LIMITATION L03 — The taxonomy does not prove measurement validity

A characteristic can be conceptually useful while still lacking a reliable/automatable metric.

**Impact:** Score inclusion requires later construct-validity work.

### LIMITATION L04 — AI-first testing changes observable evidence

Some product qualities (e.g. maintainability) require repository/engineering evidence rather than desktop UI observation. Some quality-in-use outcomes may be poorly approximated by AI agents.

**Impact:** R05 and R11 must define evaluator/evidence boundaries.

### LIMITATION L05 — Safety and compliance are domain-dependent

Generic taxonomy can reserve the constructs but cannot define universal acceptable risk/compliance without project context.

### LIMITATION L06 — Process assurance model is intentionally incomplete in R01

R01 establishes only the boundary. Detailed process/engineering quality belongs to R11.

---

## 20. Open questions

### OPEN O01 — Should `Engineering Assurance` receive a single 0–100 score?

Deferred to R11/R04/R10. A capability profile may be more interpretable than a single score.

### OPEN O02 — Should product safety always be a mandatory benchmark dimension?

The generic model should always expose the dimension, but whether evidence is mandatory may vary by profile. Deferred to R07/R10.

### OPEN O03 — How should quality-in-use Acceptability be measured by AI evaluators?

Trust, experience and acceptance may require human evidence or carefully constrained proxy measures. Deferred to R02/R05/R08.

### OPEN O04 — Should data quality be a default extension for all data-centric business software?

Likely useful for LIMS/ERP/CAS systems but not universal. Deferred to R09/R10.

### OPEN O05 — How should legal/compliance concerns interact with `Acceptability → Compliance` and project-specific compliance gates?

R01 does not interpret legal obligations. Project profiles must source applicable obligations directly.

### OPEN O06 — What minimum evidence is required before a project can mark a generic characteristic `NOT_APPLICABLE`?

Deferred to R04/R10 governance.

### OPEN O07 — How should future ISO/IEC 25059 revision changes affect the generic extension architecture?

Track source status. Do not pin the generic core to a draft AI extension.

---

## 21. Recommendations for Foundation synthesis

### RECOMMENDATION R01-01
Adopt ISO/IEC 25010:2023's nine product-quality characteristics as the generic **Product Quality** backbone.

### RECOMMENDATION R01-02
Adopt ISO/IEC 25019:2023's three-characteristic **Quality in Use** model as a separate context-bound plane rather than folding it into Interaction/UX.

### RECOMMENDATION R01-03
Create a separate **Engineering / Process Assurance** plane; do not represent engineering maturity as a product-quality characteristic.

### RECOMMENDATION R01-04
Support **Project / Domain Extensions** for data quality, AI quality, service quality and domain/regulatory requirements.

### RECOMMENDATION R01-05
Support both numeric scoring and independent hard gates. Do not let scores compensate for failed critical gates.

### RECOMMENDATION R01-06
Do not assign numeric weights until R04 and R10.

### RECOMMENDATION R01-07
Require every scored/gated measure to identify its **primary construct** to prevent double-counting across product quality and quality in use.

### RECOMMENDATION R01-08
Bind every quality-in-use result to a versioned context-of-use/persona/scenario identity defined by R08.

### RECOMMENDATION R01-09
Treat draft ISO measurement standards as `DRAFT` evidence and re-check status before Foundation 1.0 release.

### RECOMMENDATION R01-10
Keep the benchmark's Markdown MVP and future local web UI aligned to this multi-plane hierarchy from the start so that later visualization does not require reinterpreting historical runs.

---

## 22. Implications for repository architecture

R01 does not implement schemas yet, but it implies a future structure similar to:

```text
core/
├── quality-model/
│   ├── product-quality.yaml
│   ├── quality-in-use.yaml
│   └── engineering-assurance.yaml
├── gates/
├── metrics/
└── schemas/

profiles/
├── elva-ble/
└── para-dos/

extensions/
├── data-quality/
├── ai-quality/
└── service-quality/
```

This is an architectural implication only. No code/schema becomes authoritative until R10 and later implementation planning.

---

## 23. Traceability matrix

| Conclusion | Evidence |
|---|---|
| Product-quality backbone has nine characteristics | S01, S10, S12 |
| Quality in use is separate and context-bound | S02, S03 |
| Quality in use has three top-level characteristics | S02, corroborated by S13/S14 |
| Taxonomy and measurement must be separated | S03, S04, S05, S16 |
| Data quality is a separate model | S06 |
| Application-specific extensions are legitimate | S04, S07 |
| Engineering process quality is separate from product quality | S08, S09 |
| Specialized domains may need extra concerns | S07, S15, S17 |
| Quality in use must not be reduced to usability | S02, S13, S14 |
| Hard gates must remain non-compensable | Framework inference from risk/criticality separation; final operationalization deferred |
| Project profiles must not mutate generic semantics | S04/S07 extension structure + R00 generic/project separation contract |

---

## 24. Research completion assessment

### Coverage

Required source families were covered:

- current ISO/IEC 25010 product-quality model: YES;
- current ISO/IEC 25019 quality-in-use model: YES;
- ISO/IEC 25002 quality-model framework: YES;
- SQuaRE family structure: YES;
- quality measurement boundary: YES;
- data-quality extension boundary: YES;
- AI/application-specific extension boundary: YES;
- engineering/process-quality boundary: YES;
- alternative/domain model counter-evidence: YES.

### Material contradictions

No direct contradiction was found in the current normative model structure. The main tensions are **scope differences**, not factual contradictions:

- product quality vs quality in use;
- product properties vs process capability;
- generic model vs domain extensions;
- usability vs broader quality in use.

These are documented rather than collapsed.

### Confidence

- Product-quality top-level taxonomy: **HIGH**.
- Product vs quality-in-use separation: **HIGH**.
- Process-quality separation: **HIGH**.
- Need for extension plane: **HIGH**.
- Exact detailed quality-in-use subcharacteristic semantics without licensed text: **MEDIUM-HIGH**.
- Gate architecture as a framework design choice: **HIGH**, but specific mandatory gates: **OPEN**.
- Future scoring architecture: **NOT DECIDED**.

---

## 25. Final gate

```text
RESEARCH STATUS: COMPLETE
PRIMARY SOURCES COVERED: YES
CONTRADICTIONS RESOLVED OR DOCUMENTED: YES
FACTS / INFERENCES / RECOMMENDATIONS SEPARATED: YES
OPEN QUESTIONS DOCUMENTED: YES
CONFIDENCE: HIGH
READY FOR SYNTHESIS: YES
```

R01 is ready to inform R02–R11 and R10 synthesis. It does **not** authorize numeric weights, a global 0–100 formula, universal gate thresholds or project-specific benchmark rules.
