# R00 — Research Methodology & Evidence Contract

- **Research ID:** R00
- **Version:** 1.0.0
- **Date:** 2026-09-09
- **Issue:** #1
- **Repository:** `Creynox/software-quality-benchmark`
- **Research type:** Standards-led structured evidence review
- **Status:** COMPLETE

## 1. Question / objective

Define the research methodology that all later Software Quality Benchmark Foundation modules must follow so that conclusions are auditable, reproducible enough for engineering use, clearly separated by evidence type, and resistant to premature or unsupported scoring decisions.

R00 answers:

1. What counts as evidence for different kinds of claims?
2. How are normative requirements distinguished from guidance, empirical findings, inferences and project-specific facts?
3. How are sources discovered, screened, versioned and cited?
4. How are contradictions handled without silently forcing agreement?
5. How is confidence assigned to major conclusions?
6. How are copyrighted or AI-restricted sources handled?
7. When is a research module COMPLETE, PARTIAL or BLOCKED?
8. How are research conclusions versioned and changed without invalidating downstream modules silently?
9. How is the generic benchmark core kept separate from project profiles such as ELVA-BLE?

## 2. Scope

R00 defines the **research process** for R01–R11 and later benchmark research modules.

It covers:

- evidence classification;
- source selection and search discipline;
- normative vs informative material;
- source status and versioning;
- claim traceability;
- research protocol requirements;
- quality appraisal appropriate to source type;
- contradiction handling;
- confidence levels;
- generic-vs-project evidence separation;
- copyright / licensing / AI-use checks;
- change control;
- module completion gates.

## 3. Explicitly out of scope

R00 does **not** make authoritative decisions about:

- the final software-quality taxonomy;
- UX dimensions or weights;
- any 0–100 scoring formula;
- global pass thresholds;
- time normalization;
- security control catalogues;
- BLE personas or workflows;
- benchmark runner implementation;
- dashboard / local web application implementation;
- human-subject study design beyond identifying future methodology needs.

Those belong to later modules.

## 4. Method used for R00 itself

R00 is **not claimed to be a formal systematic literature review**. The evidence base mixes standards-development guidance, Internet standards practice, software-engineering research methodology and benchmark-methodology guidance. A formal SLR would not fit all of those source classes equally well.

Instead, R00 uses a **standards-led structured evidence review** and deliberately borrows the auditability disciplines of software-engineering systematic reviews:

- predefined research questions;
- explicit scope and exclusions;
- source-class coverage;
- documented search terms;
- source screening;
- evidence extraction;
- chain of evidence from sources to conclusions;
- explicit treatment of limitations and contradictions;
- separate facts, inferences and recommendations;
- documented deviations and open questions.

This choice is consistent with software-engineering review guidance that emphasizes planning, conducting and reporting reviews through a pre-defined protocol, and with the ACM SIGSOFT Empirical Standards' requirement for systematic, replicable search descriptions, clear selection criteria, explicit extraction/synthesis methods and a clear chain of evidence.

### 4.1 Search log used for R00

Searches were performed on 2026-09-09 using web search plus direct access to official and scholarly sources. Representative queries included:

- `ISO IEC Directives Part 2 normative references informative references`
- `W3C normative informative sections specification manual`
- `RFC 2119 RFC 8174 requirement words`
- `Guidelines for performing Systematic Literature Reviews in Software Engineering Kitchenham Charters`
- `ACM SIGSOFT Empirical Standards systematic review benchmarking open science`
- `QAISER systematic literature reviews software engineering`
- `ISO copyright standards artificial intelligence`

Search was intentionally source-led rather than exhaustive keyword-only discovery: official publisher material was sought first for normative/status questions, then software-engineering methodology sources for empirical-review discipline.

## 5. Primary and secondary sources

### 5.1 Primary / authoritative sources used

| ID | Source | Role in R00 |
|---|---|---|
| S01 | W3C, **Normative References** — https://www.w3.org/2013/09/normative-references | Stability, change-control, dependency and licensing considerations for normative references |
| S02 | W3C, **Manual of Style** — https://www.w3.org/guide/manual-of-style/ | Explicit separation of normative/informative material; versioned references; careful requirement language |
| S03 | W3C, **Normative References to W3C Standards** — https://www.w3.org/2013/02/stdref | Document status and dated-vs-latest URI handling |
| S04 | RFC 2119 / BCP 14 — https://www.rfc-editor.org/info/rfc2119/ | Meaning and careful use of MUST / SHOULD / MAY requirement language |
| S05 | RFC 8174 / BCP 14 — https://www.rfc-editor.org/info/rfc8174/ | Requirement-keyword semantics apply to uppercase keywords when used in BCP 14 sense |
| S06 | ACM SIGSOFT **Empirical Standards for Software Engineering** — https://www2.sigsoft.org/EmpiricalStandards/ | Official software-engineering evidence standards; systematic reviews, benchmarking, replication/open-science expectations |
| S07 | ACM SIGSOFT **Standards** — https://www2.sigsoft.org/EmpiricalStandards/docs/standards | Essential benchmark and systematic-review attributes; replication detail; construct validity |
| S08 | ACM SIGSOFT **Supplements** — https://www2.sigsoft.org/EmpiricalStandards/docs/supplements | Open science, registered reports, sampling and inter-rater expectations |
| S09 | EBSE / Kitchenham & Charters, **Guidelines for performing Systematic Literature Reviews in Software Engineering**, 2007 — https://ebse.webspace.durham.ac.uk/ebse-bibliography/guidelines-for-performing-systematic-literature-reviews-in-software-engineering/ | Planning / conducting / reporting model and auditable protocol discipline |
| S10 | ISO, **Directives and Policies** — https://www.iso.org/directives-and-policies.html | Official status that ISO/IEC Directives govern standards development; normative-reference resources |
| S11 | ISO Helpdesk, **Add normative and bibliographic references** — https://helpdesk-docs.iso.org/article/621-add-modify-delete-references-in-the-normative-references-bibliography-clauses | Official distinction between normative and bibliographic references; dated/undated reference handling |
| S12 | ISO, **Copyright** — https://www.iso.org/copyright.html | Copyright and AI-use restrictions for ISO content |

### 5.2 Secondary / scholarly quality-control source

| ID | Source | Role in R00 |
|---|---|---|
| S13 | Usman, Ali & Wohlin (2023), **A Quality Assessment Instrument for Systematic Literature Reviews in Software Engineering (QAISER)**, DOI 10.37190/e-Inf230105 — https://www.e-informatyka.pl/index.php/einformatica/volumes/volume-2023/issue-1/article-5/ | Supports protocol-before-review, documented search/selection/extraction/quality/synthesis and explicit handling of deviations |

### 5.3 Source-selection note

No source above is treated as universally superior for every claim. Source suitability depends on **claim type**. This is a central conclusion of R00.

A current normative standard is authoritative for what that standard requires, but it is not automatically the strongest empirical evidence that a design choice improves usability. Conversely, a peer-reviewed experiment can support an empirical effect but cannot create a normative requirement that the relevant standards body never made.

## 6. Confirmed facts from the evidence

### FACT F00-01 — Normative and informative material must be distinguished

Standards bodies explicitly distinguish normative material (requirements/conformance-relevant content) from informative material (explanation, examples, guidance). W3C requires informative sections to be identified, and ISO standards maintain normative-reference and bibliography/informative distinctions. [S01, S02, S03, S10, S11]

**Implication:** The benchmark research must never convert an informative note, blog explanation or secondary summary into a claimed standard requirement.

### FACT F00-02 — Reference status and stability matter

W3C's normative-reference guidance explicitly considers stability, expected change, change-control policy, dependency nature and specificity of the referenced material. W3C also distinguishes dated immutable version URIs from latest-version URIs. [S01, S03]

**Implication:** Every material source in this project needs status/version metadata; a citation to an undifferentiated "latest" page is insufficient for historically reproducible benchmark decisions.

### FACT F00-03 — Requirement keywords have defined semantics only when deliberately used

RFC 2119 defines MUST, SHOULD and MAY semantics for specification requirements, and RFC 8174 clarifies the special meanings apply when the keywords appear in uppercase in the BCP 14 sense. RFC 2119 also warns against using imperatives merely to impose a preferred implementation method when not required. [S04, S05]

**Implication:** Requirement language in Foundation specifications must be intentional. Research notes should not casually use uppercase MUST/SHOULD/MAY unless they are deliberately establishing an adopted framework rule.

### FACT F00-04 — Software-engineering systematic reviews require an auditable protocol and chain of evidence

Kitchenham & Charters frame systematic review as a rigorous, auditable process organized around planning, conducting and reporting. ACM SIGSOFT requires systematic reviews to describe search terms/process, selection criteria, extracted data and synthesis, and to maintain a clear chain of evidence from extracted data to research answers. QAISER likewise treats a written protocol, search/selection/extraction/quality/synthesis planning and documentation of deviations as central quality properties. [S06, S07, S09, S13]

**Implication:** Later research modules must be protocol-led rather than free-form AI essays.

### FACT F00-05 — Benchmarks themselves require construct validity, replicable setup and stability checks

ACM SIGSOFT's benchmarking standard requires the benchmarked quality, metrics, measurement method and workload/usage profile to be defined; the setup must be described sufficiently for replication; reliability/stability should be assessed through sufficient repetitions/duration; and construct validity must be discussed. [S06, S07]

**Implication:** R04/R05 cannot treat a single opaque AI score as a reliable benchmark result.

### FACT F00-06 — Open/reproducible artifacts are valuable, but disclosure can be limited by legal/ethical constraints

ACM SIGSOFT encourages protocols, datasets, analysis scripts and supplementary artifacts to be made available, while explicitly recognizing legitimate reasons why artifacts cannot be released. [S08]

**Implication:** The project should maximize reproducibility but must not publish restricted project data, confidential evidence or copyrighted standards text merely for openness.

### FACT F00-07 — ISO content has explicit copyright and AI-use restrictions

ISO's current copyright page states ISO publications and ISO Online content are copyright protected and restrict use for machine-learning / artificial-intelligence purposes except where permitted. [S12]

**Implication:** This project must not ingest or redistribute full ISO standards text through AI workflows unless the relevant license/permission explicitly allows it. Bibliographic references and independently maintained research metadata must be handled separately from protected source text.

## 7. Derived conclusions

### INFERENCE I00-01 — A single linear "source hierarchy" is unsafe

A single list such as `standard > paper > blog` conflates two different questions:

1. **Normative authority** — who has authority to define a requirement?
2. **Empirical evidence strength** — what evidence supports a claim about measured effects or behavior?

A standard can be decisive for a conformance claim while offering no empirical proof of usability benefit. A rigorous study can demonstrate an effect while having no authority to create a conformance obligation.

**Conclusion:** R00 adopts a **claim-type-first evidence model**, not one universal ranking.

**Confidence:** HIGH — directly consistent with normative/informative distinctions plus empirical-method guidance. [S01–S07]

### INFERENCE I00-02 — Project implementation evidence and project intent are different evidence classes

Executable behavior, tests and runtime evidence can show what a product currently does. Architecture decisions, domain contracts and requirements can show what it is intended or required to do. Neither automatically invalidates the other when they disagree; disagreement is itself evidence of drift or a defect.

**Conclusion:** R09 and all future project profiles must keep `IMPLEMENTED_BEHAVIOR` separate from `DESIGN_CONTRACT` and `WORK_MANAGEMENT_INTENT`.

**Confidence:** HIGH — engineering reasoning aligned with the chain-of-evidence requirement; project-specific formalization is a framework design choice.

### INFERENCE I00-03 — Research completeness must be based on coverage and unresolved risk, not number of sources

Ten weak or duplicative sources do not make a conclusion stronger than a smaller set of direct, current, authoritative sources. Conversely, one source is insufficient when the research question spans multiple source classes or contains material empirical disagreement.

**Conclusion:** Modules close when required source families are covered, claims are traceable, material contradictions are resolved/documented, and no known evidence gap can plausibly reverse a major conclusion.

**Confidence:** HIGH — supported by systematic-review and benchmark-method guidance. [S06–S09, S13]

### INFERENCE I00-04 — AI model memory is not evidence

An AI evaluator may use prior knowledge to formulate search hypotheses, but an unsourced model assertion cannot be entered as `FACT` in the benchmark foundation.

**Conclusion:** Every material FACT requires an external or repository evidence reference. Unsourced model knowledge is a search lead only.

**Confidence:** HIGH — framework rule necessary to preserve the chain of evidence required by the selected methodology. [S07, S09]

## 8. Adopted research evidence model

### 8.1 Claim categories

Every material statement in a research module must be recognizable as one of the following:

- **FACT** — directly supported by cited evidence.
- **INFERENCE** — reasoned conclusion derived from one or more FACTs; rationale and source IDs required.
- **RECOMMENDATION** — proposed framework/project design choice; must not be presented as an external requirement unless a source actually requires it.
- **OPEN** — unresolved question, evidence gap or conflict.
- **PROJECT-SPECIFIC** — evidence or rule that belongs to a project profile rather than the generic benchmark core.

Optional additional metadata may describe the **nature** of a claim:

- `NORMATIVE`
- `EMPIRICAL`
- `DESCRIPTIVE`
- `IMPLEMENTATION`
- `DESIGN`

The category and nature are independent. For example, `FACT + EMPIRICAL` differs from `FACT + NORMATIVE`.

### 8.2 Source classes

Sources are classified by role, not forced into one universal quality ranking:

- `REGULATORY_OFFICIAL` — official law/regulator source, only when legal/regulatory research is explicitly in scope;
- `NORMATIVE_STANDARD` — current published standard/specification with conformance authority in its defined scope;
- `OFFICIAL_GUIDANCE` — guidance from the same standards body, regulator, platform owner or authoritative organization;
- `PEER_REVIEWED_SYNTHESIS` — systematic review, meta-analysis or equivalent;
- `PEER_REVIEWED_PRIMARY` — empirical primary study;
- `TECHNICAL_REPORT` — methodologically documented institutional/academic report;
- `SPECIALIST_GUIDANCE` — established specialist source with disclosed method;
- `PROJECT_DESIGN_CONTRACT` — ADR, domain contract, requirement or policy for a specific software project;
- `PROJECT_IMPLEMENTATION_EVIDENCE` — current code, tests, runtime/browser evidence, build or deployed behavior;
- `PROJECT_WORK_MANAGEMENT` — issue, PR, roadmap or planning evidence;
- `VENDOR_OR_COMMUNITY` — vendor documentation, blog, forum or community source.

### 8.3 Claim-type matching rules

#### Normative / conformance claim

A claim that something is **required** by a standard must be supported by the normative source itself or an official source that unambiguously identifies the requirement. Secondary articles can explain but cannot establish the obligation.

#### Empirical-effect claim

A claim that a practice improves time, usability, reliability or another measured outcome should be supported by empirical evidence appropriate to the question. Standards/guidance may motivate the practice but do not automatically prove its effect size.

#### Product-behavior claim

A claim about what a project currently does should rely on current implementation/runtime/test evidence tied to a commit/build/environment where practical.

#### Project-intent claim

A claim about what a project is intended or required to do should cite current project contracts, ADRs, requirements or equivalent decision records.

#### Legal/regulatory claim

Legal obligations are outside the normal assumption set. If later research makes legal/regulatory claims, use official legal/regulatory sources and flag the need for appropriate legal interpretation. Do not infer a legal obligation merely because an ISO/industry standard exists.

## 9. Source registry requirements

Every included material source must record, where available:

```yaml
source_id:
title:
publisher_or_author:
source_class:
publication_or_version_date:
edition_or_revision:
status: CURRENT | DRAFT | SUPERSEDED | UNKNOWN
stable_identifier: DOI | standard_id | RFC | versioned_URL | commit_SHA | other
url:
accessed_at:
applicability: DIRECT | ANALOGOUS | CONTEXTUAL
normative_scope:
license_or_copyright_notes:
ai_use: ALLOWED | RESTRICTED | UNKNOWN
used_for_claims:
notes:
```

Not every field applies to every source, but omission of material status/version information must be explained.

## 10. Search protocol for future modules

Before substantive searching, each module must define:

1. research question(s);
2. scope and out-of-scope topics;
3. expected source families;
4. initial search terms / repositories / standards bodies;
5. inclusion and exclusion rules;
6. data to be extracted;
7. synthesis method;
8. expected completion gate.

### 10.1 Required search sequence

Use the following sequence unless the module documents why another order is better:

1. **Authoritative-source discovery** — identify relevant standards bodies, regulators, official specifications and primary project contracts.
2. **Current-status verification** — confirm edition/revision/status, supersession and errata where available.
3. **Method / empirical discovery** — search peer-reviewed and methodologically transparent software-engineering / reference-discipline evidence as needed.
4. **Secondary explanation** — use specialist or vendor guidance only to clarify, discover vocabulary or identify primary sources.
5. **Backward/forward search** — for scholarly questions, inspect key references/citations when they could materially change coverage.
6. **Contradiction search** — deliberately search for evidence that could falsify or limit major conclusions.

### 10.2 Search-log minimum

Each module records:

- date(s) searched;
- source/database/site;
- material queries;
- included sources;
- material exclusions and reasons when exclusion could affect conclusions;
- known access limitations.

A complete dump of every irrelevant search result is not required.

### 10.3 Stopping rule

Research may stop when all of the following are true:

- the predeclared primary source families have been covered or their absence documented;
- no known current primary source has been ignored merely because it conflicts with the emerging conclusion;
- additional searching is no longer producing material new claim categories or changing major conclusions;
- contradictions are resolved or explicitly carried as OPEN;
- remaining uncertainty is documented and reflected in confidence.

This is a **coverage/saturation rule**, not a required source count.

## 11. Inclusion / exclusion rules

### Include

A source may be included when it is relevant to a research question and at least one of these is true:

- it is the primary normative/official source;
- it provides direct empirical evidence;
- it is a recognized methodological reference;
- it documents project behavior or project contract evidence;
- it materially challenges an emerging conclusion;
- it is needed to understand source status, licensing or revision history.

### Exclude or downgrade

A source should be excluded from authoritative support, or clearly downgraded, when:

- it merely repeats another source without adding evidence;
- its publisher/status/version cannot be established;
- it is obsolete and no historical comparison is needed;
- it is marketing content offered as evidence of effectiveness;
- it makes unsourced normative claims;
- it is inaccessible in a way that prevents verification of the claimed content;
- its use would violate copyright/licensing/AI-use restrictions.

An excluded source may still be recorded if the exclusion itself is material.

## 12. Quality appraisal is source-type specific

There is no single numerical "source quality score" in R00.

### 12.1 Normative / official sources

Check:

- issuing authority;
- document status;
- edition/revision date;
- normative vs informative section;
- scope/applicability;
- dated vs living reference;
- supersession/errata;
- licensing/AI-use constraints.

### 12.2 Empirical studies / reviews

Check as appropriate:

- research design fit to the question;
- sample/task/system selection;
- measurement validity;
- reproducibility / protocol disclosure;
- analysis appropriateness;
- uncertainty/variation reporting;
- bias and validity threats;
- peer-review/publication status;
- replication or supporting evidence.

### 12.3 Project repository evidence

Check:

- repository and ref/commit/build;
- current vs historical state;
- runtime/test evidence vs documentation-only claim;
- whether tests prove behavior or merely implementation detail;
- environment/fixture used;
- whether an ADR/domain contract defines intent that differs from implementation;
- whether issue/PR status represents planning rather than shipped behavior.

### 12.4 Vendor/community guidance

Check:

- whether the source is describing its own product;
- possible commercial bias;
- version/date;
- whether it links to primary evidence;
- whether the claim is advice rather than demonstrated fact.

## 13. Chain-of-evidence / claim ledger

Every **major conclusion** must be traceable through a claim ledger, either explicitly as a table or implicitly through clearly cited subsections.

Recommended fields:

```yaml
claim_id:
claim_category: FACT | INFERENCE | RECOMMENDATION | OPEN | PROJECT-SPECIFIC
claim_nature: NORMATIVE | EMPIRICAL | DESCRIPTIVE | IMPLEMENTATION | DESIGN
statement:
supporting_source_ids:
source_scope:
directness: DIRECT | INDIRECT
conflicting_source_ids:
confidence: HIGH | MEDIUM | LOW | N/A
reasoning_or_rationale:
downstream_implications:
```

### Binding rules

- `FACT` requires at least one verifiable supporting source.
- `INFERENCE` requires cited supporting FACTs and explicit reasoning.
- `RECOMMENDATION` must identify itself as a framework choice and must not inherit normative force from adjacent citations.
- `OPEN` must not be silently converted into a recommendation during synthesis.
- `PROJECT-SPECIFIC` must not be promoted into Generic Core merely because the first project needs it.
- AI model memory alone is never a supporting source.

## 14. Contradiction protocol

When two sources appear to disagree, do **not** immediately choose one.

Apply this sequence:

1. **Restate both claims precisely.** Avoid comparing paraphrases that use different scopes.
2. **Check scope.** Different populations, software types, assurance levels or contexts may remove the conflict.
3. **Check terminology.** The same word may carry different defined meanings.
4. **Check version/status.** Determine whether one source supersedes or updates another.
5. **Check normative status.** Informative guidance does not override normative text within the same governing specification.
6. **Check evidence type.** A normative requirement and an empirical finding can coexist even when they answer different questions.
7. **Check methodological quality/directness** for empirical disagreements.
8. **Record residual disagreement.** If both remain applicable and incompatible, mark an OPEN conflict and defer the design choice to synthesis/decision record.

### Required contradiction record

```yaml
conflict_id:
source_a:
source_b:
conflict_type: SCOPE | TERMINOLOGY | VERSION | NORMATIVE | EMPIRICAL | PROJECT_DRIFT | OTHER
resolution: RESOLVED | PARTIAL | OPEN
reason:
impact_on_conclusions:
```

### Special project-drift case

If a project contract says one thing but executable behavior shows another, do not declare either source invalid by default. Record:

- intended rule;
- observed implementation;
- evidence for both;
- whether the difference is a defect, stale documentation or an unresolved design change.

## 15. Confidence model

R00 deliberately uses an **ordinal** confidence model rather than pseudo-precise percentages.

Confidence is assigned per **major conclusion**, not once for the entire document.

Evaluate:

1. **Directness** — does the evidence answer the actual claim or only an analogy?
2. **Source/claim fit** — is the source type appropriate for the type of claim?
3. **Currentness/stability** — is the source current, stable and versioned?
4. **Consistency** — do other applicable sources materially disagree?
5. **Coverage** — have the necessary source families been checked?
6. **Method quality / reproducibility** — for empirical claims, is the design and analysis credible enough for the conclusion?
7. **Traceability** — can another reviewer reproduce the path from source to conclusion?

### HIGH

Use when evidence is direct, current and appropriate to the claim; material source families are covered; no unresolved contradiction plausibly overturns the conclusion; and the chain of evidence is reproducible.

### MEDIUM

Use when the conclusion is reasonably supported but has one or more material limitations such as indirectness, limited empirical coverage, uncertain generalizability, provisional source status, or non-critical disagreement.

### LOW

Use when evidence is sparse, substantially indirect, old/draft/unstable, methodologically weak for the claim, or materially conflicting.

### N/A

Use for an unresolved OPEN question rather than forcing a confidence label onto a non-conclusion.

### Confidence guardrails

- A normative claim cannot be HIGH if no normative/official source directly supports it.
- A general empirical claim cannot be HIGH based only on a vendor/blog/community source.
- A project behavior claim cannot be HIGH if no current build/runtime/code/test evidence is available and only planning documentation exists.
- A conclusion with an unresolved material contradiction cannot be HIGH.

## 16. Normative language inside this repository

### 16.1 Research documents

Research modules are primarily evidence/synthesis documents. They should prefer ordinary language plus the explicit tags `FACT`, `INFERENCE`, `RECOMMENDATION`, `OPEN`, `PROJECT-SPECIFIC`.

They should **not** use uppercase BCP 14 MUST/SHOULD/MAY merely for emphasis.

### 16.2 Adopted Foundation specifications

If Foundation 1.0 later adopts normative internal rules, it may use BCP 14 semantics deliberately and include the BCP 14 interpretation statement. [S04, S05]

When requirements are derived from an external standard, preserve the source's own normative meaning and citation. Do not rewrite informative external guidance as a Foundation MUST unless the Foundation independently and explicitly chooses that rule.

## 17. Copyright, licensing and AI-use contract

### 17.1 General rule

Evidence traceability does not grant a right to copy source text.

The repository should store:

- bibliographic metadata;
- stable identifiers/URLs;
- independently written analysis;
- short quotations only when permitted and genuinely necessary;
- source status/licensing notes.

It should not mirror full copyrighted standards or proprietary reports without explicit permission.

### 17.2 AI-restricted sources

If a source publisher prohibits or restricts AI use, the AI researcher must not ingest the protected full text merely because a human user has access to it. ISO currently publishes such restrictions for ISO content. [S12]

For an AI-restricted source:

- mark `ai_use: RESTRICTED`;
- do not upload/paste the protected full text into the benchmark AI workflow;
- do not redistribute it in this repository;
- use only source metadata / permitted public material where legally and contractually allowed;
- if a project requires detailed conformance mapping, use a rights-cleared process (for example human review or licensed tooling) and record that constraint explicitly.

R00 does **not** make a legal determination about every source license; it requires the restriction to be checked and respected.

### 17.3 Public vs confidential project evidence

Open-science ideals do not override confidentiality. Project profiles may reference private repositories/evidence while the Generic Core remains public. Sensitive evidence should be stored in an appropriate private location and linked by stable internal identifier rather than copied into a public benchmark repository.

## 18. Generic Core vs project-specific separation

R00 establishes a hard conceptual boundary:

### Generic Core may contain

- general measurement definitions;
- generic quality dimensions;
- generic scoring/gating machinery;
- generic persona/skill schema;
- generic evidence and run schemas;
- generic security/accessibility/performance methodology;
- generic AI evaluator contract.

### Project Profile may contain

- domain roles;
- project permissions;
- actual workflows;
- project-specific critical paths;
- domain correctness rules;
- project-specific security boundaries;
- baseline/target times;
- fixtures/test users;
- project-specific weights or gates where allowed by Foundation rules.

### Separation rules

1. A rule discovered only because ELVA-BLE needs it starts as `PROJECT-SPECIFIC`.
2. It may move into Generic Core only after an explicit generalization decision supported by evidence that it applies beyond the project.
3. Generic Core must not import private project data.
4. Project Profile may specialize Generic Core but may not silently redefine a generic metric while keeping the same identifier.
5. Profile-specific scoring/gating overrides must be explicit and versioned.

## 19. Research-module completion states

### COMPLETE

All required source families are covered or their absence is documented; major claims are traceable; material contradictions are resolved or OPEN; facts/inferences/recommendations are separated; open questions are explicit; no known evidence gap is likely to reverse a major conclusion without being visible.

A COMPLETE module may still have OPEN questions if they are non-blocking and clearly carried forward.

### PARTIAL

Useful evidence exists, but one or more material source families, contradictions, access constraints or validation steps remain. Conclusions may inform later research but must be treated as provisional.

### BLOCKED

A material dependency prevents a reliable conclusion—for example inaccessible authoritative evidence, unresolved licensing restrictions, a necessary project decision, or a conflict that cannot be evaluated with available evidence.

A BLOCKED module must identify the exact unblock condition.

## 20. Required completion gate

Every research module must end with exactly these top-level fields:

```text
RESEARCH STATUS: COMPLETE | PARTIAL | BLOCKED
PRIMARY SOURCES COVERED: YES | NO
CONTRADICTIONS RESOLVED OR DOCUMENTED: YES | NO
FACTS / INFERENCES / RECOMMENDATIONS SEPARATED: YES | NO
OPEN QUESTIONS DOCUMENTED: YES | NO
CONFIDENCE: HIGH | MEDIUM | LOW
READY FOR SYNTHESIS: YES | NO
```

### Gate interpretation

`READY FOR SYNTHESIS: YES` requires:

- `RESEARCH STATUS: COMPLETE`;
- primary sources covered;
- contradictions resolved/documented;
- claim categories separated;
- open questions documented.

Overall `CONFIDENCE` summarizes the module only for navigation. It does **not** replace per-conclusion confidence.

## 21. Change control and research versioning

Research conclusions will evolve. Changes must be visible.

### 21.1 Version semantics

Use semantic-style versions for research documents:

- **PATCH** — editorial/source-link correction with no material conclusion change;
- **MINOR** — new evidence or clarification that adds/refines conclusions without invalidating dependent contracts;
- **MAJOR** — reversal or material change to a conclusion/contract that can invalidate downstream assumptions.

### 21.2 Substantive change rules

For any MINOR or MAJOR change:

- state why the research was reopened;
- identify new/changed sources;
- list changed conclusions;
- list affected downstream modules/profiles;
- re-evaluate confidence and open contradictions;
- update the changelog/PR description.

### 21.3 Source updates

A source being updated does not automatically change this project.

Instead:

1. detect/record the new source version;
2. compare relevant claims;
3. assess downstream impact;
4. update research only if conclusions materially change or reproducibility requires the new citation.

This prevents silent semantic drift from "latest version" references.

## 22. Research review expectations

Before a module is considered COMPLETE, perform a structured self-review or independent review covering:

- each acceptance criterion;
- claim/source traceability;
- missing primary source classes;
- counterevidence search;
- normative-vs-informative mistakes;
- current/superseded source status;
- unsupported AI-memory claims;
- project-specific contamination;
- copyright/AI-use constraints;
- open contradictions;
- whether confidence is overstated.

For high-impact Foundation decisions (especially scoring, security gates and AI evaluator reliability), an independent second-model or human review is recommended before Foundation 1.0 adoption.

## 23. Rejected alternatives

### REJECTED A — One universal source-ranking ladder

Reason: It confuses normative authority with empirical strength. Source fitness depends on claim type.

### REJECTED B — Treat every research module as a formal SLR

Reason: Several modules rely heavily on standards, specifications, project evidence and security frameworks rather than only academic literature. Formal SLR requirements would create process theater without improving all source classes equally.

### REJECTED C — Free-form AI research with citations added afterward

Reason: It breaks the required chain of evidence and encourages model-memory claims to become facts.

### REJECTED D — Numeric confidence percentages

Reason: R00 has no validated calibration method for probabilities of correctness. HIGH/MEDIUM/LOW is more honest until a future calibration method exists.

### REJECTED E — Automatically resolve source conflicts by taking the newest source

Reason: Newer does not necessarily mean same scope, same authority or supersession. Version/status must be evaluated.

### REJECTED F — Copy full standards into the research repository for convenience

Reason: Copyright/licensing/AI-use restrictions may prohibit this and open-science goals do not override those restrictions. [S12]

### REJECTED G — Let first-project needs define the Generic Core automatically

Reason: It would make a nominally reusable framework actually encode ELVA-BLE/LIMS assumptions.

## 24. Risks and limitations

### L00-01 — Source-access asymmetry

Some standards are not freely accessible and some explicitly restrict AI use. This can constrain future primary-source analysis. R00 mitigates the risk through source-access metadata and a BLOCKED/PARTIAL state rather than pretending inaccessible text was verified.

### L00-02 — Methodology sources come from multiple traditions

Standards development, empirical software engineering and product engineering have different evidence norms. R00 intentionally does not force a single academic hierarchy over normative standards or project evidence.

### L00-03 — Confidence remains judgment-based

HIGH/MEDIUM/LOW is still a structured expert judgment. It is not statistically calibrated. R04/R05 may later define additional quantitative reliability measures for benchmark runs, but that does not retroactively turn research confidence into probability.

### L00-04 — Search cannot prove absolute exhaustiveness

The completion rule is designed around documented coverage and saturation, not a false claim that every possible source was found.

### L00-05 — Public repository

This repository may be public while future project profiles can involve private architecture/security evidence. R09 must not copy confidential BLE evidence into a public location without an explicit visibility decision.

## 25. Open questions

### OPEN-00-01 — Long-term archival location

GitHub provides version control but is not by itself an archival research repository. Before a public stable 1.0 release, decide whether tagged Foundation releases and source registers should also be archived in a preservation service (for example a DOI-backed archive).

**Blocking now:** NO.

### OPEN-00-02 — Independent research review policy

Decide before Foundation 1.0 which modules require mandatory independent model/human review versus structured self-review. R04, R05 and R06 are strong candidates for mandatory independent review because scoring, AI reproducibility and security errors could affect the whole benchmark.

**Blocking R01:** NO.

### OPEN-00-03 — Public/private project-profile storage

Before R09, decide whether ELVA-BLE project evidence lives in this repository, a private companion repository, or only as references to the private BLE repository.

**Blocking R01:** NO.
**Blocking R09:** YES before sensitive evidence is written.

## 26. Recommendations adopted for later modules

### RECOMMENDATION R00-01 — Use a structured evidence protocol for every research module

Each module should be independently reviewable and should not depend on hidden chat context.

### RECOMMENDATION R00-02 — Separate source authority from evidence strength

Do not globally rank standards, academic studies and project evidence on one axis. Match evidence to claim type.

### RECOMMENDATION R00-03 — Maintain source metadata and claim traceability from the start

Do not postpone provenance until the final report.

### RECOMMENDATION R00-04 — Preserve uncertainty instead of manufacturing rules

If evidence cannot support a conclusion, mark OPEN/PARTIAL/BLOCKED.

### RECOMMENDATION R00-05 — Keep raw evidence and final benchmark requirements conceptually separate

A research finding does not become a benchmark MUST until it is explicitly adopted by Foundation synthesis/decision control.

### RECOMMENDATION R00-06 — Treat copyright / AI-use permission as part of evidence eligibility

A source that cannot legally/contractually be ingested into an AI workflow is not silently used anyway.

### RECOMMENDATION R00-07 — Require counterevidence search for high-impact conclusions

For scoring formulas, security gates, AI evaluator reliability and major quality-model decisions, researchers should deliberately seek evidence that could falsify or limit the preferred conclusion.

## 27. Implications for later research modules

### R01 — Generic software quality

Must map each quality characteristic to current authoritative definitions and distinguish normative taxonomy from our own later project taxonomy.

### R02 — Usability & interaction

Must separate standard definitions from empirical findings about usability methods and from our benchmark design recommendations.

### R03 — Time / efficiency / performance

Must treat raw time measures separately from any scoring threshold until evidence/baselines justify normalization.

### R04 — Scoring / normalization / statistics

Must use explicit construct-validity reasoning, preserve raw metrics, report uncertainty and avoid compensating critical failures through averages unless the gate model explicitly permits it.

### R05 — AI evaluator reproducibility

Must define evaluator identity/version, repeated runs, leakage controls and model variance based on evidence rather than treating one agent run as truth.

### R06 — Security assurance

Must distinguish authoritative control frameworks, verification guidance and empirical/project security evidence; copyright/AI restrictions are especially relevant.

### R07 — Accessibility / reliability / resilience

Must verify specification status/version and not convert advisory techniques into mandatory conformance criteria without normative support.

### R08 — Persona / scenario model

Generic schemas must be distinguished from ELVA-BLE role definitions.

### R09 — Project evidence inventory

Must keep implementation evidence, design contracts and work-management intent separate; must resolve the private/public evidence strategy before writing sensitive material.

### R10 — Synthesis

May adopt research recommendations as Foundation requirements only explicitly, with traceability to the source modules and a decision/change record.

### R11 — Engineering quality

Must separate process maturity guidance from product-level code/test evidence and avoid treating one framework as universally mandatory.

## 28. Acceptance-criteria verification for Issue #1

- [x] Research question and scope are explicit.
- [x] Evidence model is defined and justified.
- [x] Normative requirements cannot be inferred from blogs or recommendations.
- [x] Confidence model is defined.
- [x] Contradiction protocol is defined.
- [x] Research completion gate is defined.
- [x] Versioning/change rules are defined.
- [x] Generic-vs-project-specific separation rule is defined.
- [x] No scoring formula is made authoritative in R00.
- [x] Copyright / AI-use restrictions are part of source eligibility.
- [x] AI memory is explicitly excluded as evidence.

## 29. Research completion gate

```text
RESEARCH STATUS: COMPLETE
PRIMARY SOURCES COVERED: YES
CONTRADICTIONS RESOLVED OR DOCUMENTED: YES
FACTS / INFERENCES / RECOMMENDATIONS SEPARATED: YES
OPEN QUESTIONS DOCUMENTED: YES
CONFIDENCE: HIGH
READY FOR SYNTHESIS: YES
```

## 30. R00 conclusion

The Foundation Research should not be conducted as a sequence of persuasive AI essays. It should operate as a versioned evidence system.

The central methodological decision is that **claim type determines what evidence is authoritative**. Normative authority, empirical strength, project intent and implemented behavior are separate evidence dimensions. Every later module must preserve that separation, keep a visible chain of evidence, record uncertainty and contradictions, respect source-version/licensing constraints, and refuse to manufacture certainty when evidence is incomplete.

R00 is therefore ready to govern R01–R11.