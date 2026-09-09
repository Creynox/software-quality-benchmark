# Foundation Research

The benchmark methodology is developed in separate research modules to reduce premature conclusions and make contradictions visible before synthesis.

> **Governing research methodology:** `research/R00-research-methodology/R00-research-methodology.md`
>
> R00 is authoritative for how R01–R11 classify evidence, record sources, separate facts/inferences/recommendations, handle contradictions, assign confidence, respect source licensing/AI-use restrictions, and close a research module.

## Research sequence

| ID | Topic | Primary purpose |
|---|---|---|
| R00 | Research methodology | Define evidence hierarchy, source handling, confidence and completion rules |
| R01 | Generic software quality | Define the high-level quality taxonomy |
| R02 | Usability & interaction | Define effectiveness, discoverability, learnability, feedback, help and recovery concepts |
| R03 | Time, efficiency & performance | Define task-time and system-performance measurement |
| R04 | Scoring, normalization & statistics | Define how raw observations may become scores without hiding uncertainty |
| R05 | AI evaluator reproducibility | Define evaluator identity, repeated runs, calibration and leakage controls |
| R06 | Security assurance | Define black-box and white-box security benchmark layers |
| R07 | Accessibility, reliability & resilience | Define accessibility, failure-state and recovery evaluation |
| R08 | Persona, skill & scenario model | Define reusable persona and scenario schemas |
| R09 | First project evidence inventory | Inventory the first real software product without contaminating the generic core |
| R10 | Foundation synthesis | Reconcile R00–R09 into Foundation 1.0 |
| R11 | Engineering quality | Define maintainability, testing, CI/CD, dependency and secure-development quality |

## Required structure for every research module

Use `research/templates/research-module-template.md` as the starting point.

Each research document must contain:

1. Research ID and version
2. Date
3. Question / objective
4. Scope
5. Explicit out-of-scope topics
6. Primary sources
7. Secondary sources
8. Confirmed facts
9. Derived conclusions
10. Recommendations
11. Open questions
12. Contradictions / disagreements between sources
13. Rejected alternatives
14. Risks and limitations
15. Confidence per major conclusion
16. Implications for later research modules
17. Research completion gate

## Evidence model

The exact evidence contract is defined in R00. In short:

- match evidence to the **type of claim** instead of using one universal source ranking;
- distinguish normative authority from empirical evidence strength;
- verify source status/version/currentness;
- never make a normative claim from an informative/blog/community source;
- never treat AI model memory as evidence;
- record copyright/licensing/AI-use restrictions as part of source eligibility.

## Separation rules

Every document must clearly separate:

- **FACT** — directly supported by evidence,
- **INFERENCE** — reasoned conclusion from facts,
- **RECOMMENDATION** — proposed design choice for this framework,
- **OPEN** — unresolved question,
- **PROJECT-SPECIFIC** — belongs to a project profile, not the generic core.

## No premature scoring

No global weights, 0–100 formula, pass threshold or overall score becomes authoritative before R04 and R10 are complete.

Raw metrics may be defined earlier, but their scoring interpretation remains provisional.

## Research completion gate

Each module ends with:

```text
RESEARCH STATUS: COMPLETE | PARTIAL | BLOCKED
PRIMARY SOURCES COVERED: YES | NO
CONTRADICTIONS RESOLVED OR DOCUMENTED: YES | NO
FACTS / INFERENCES / RECOMMENDATIONS SEPARATED: YES | NO
OPEN QUESTIONS DOCUMENTED: YES | NO
CONFIDENCE: HIGH | MEDIUM | LOW
READY FOR SYNTHESIS: YES | NO
```

A module marked `PARTIAL` or `BLOCKED` may inform later work, but must not silently become an authoritative Foundation 1.0 rule.

## Research discipline

- Prefer depth over speed.
- Do not force agreement between sources.
- Record uncertainty instead of inventing a rule.
- Keep generic methodology independent from the first product profile.
- Do not implement the benchmark runner while core measurement contracts are still unstable.
