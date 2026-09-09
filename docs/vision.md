# Vision

## Purpose

Build a reusable software-quality benchmark framework that turns ad-hoc AI review into a versioned, evidence-based quality standard.

The framework is intended to support multiple software products over time without coupling the generic benchmark methodology to any one domain.

## Near-term goal

The first usable version does **not** need a web dashboard. It needs a stable blueprint that allows an AI evaluator to execute defined benchmark scenarios and produce a reproducible Markdown report with scores, measurements, gates and findings.

## Long-term goal

Evolve the framework into an internal enterprise software-testing tool with a local web interface for:

- project profiles,
- benchmark definitions,
- scenario configuration,
- evaluator configuration,
- score and gate visualization,
- time and efficiency trends,
- security and engineering-quality views,
- regression comparisons,
- findings and evidence,
- benchmark history,
- threshold and weighting configuration.

## Architecture principle

The framework consists of a generic core plus project-specific profiles.

```text
Generic Benchmark Core
├── quality model
├── metrics
├── scoring
├── gates
├── statistics
├── evaluator contracts
├── scenario/persona schemas
└── report/evidence schemas

Project Profiles
├── project-specific personas
├── domain workflows
├── domain correctness rules
├── critical gates
├── permissions/scopes
└── benchmark suites
```

A project profile may specialize the generic core, but must not silently redefine generic concepts.

## Evaluation modes

The research must distinguish at least:

- black-box UI evaluation,
- assisted UI evaluation,
- black-box security evaluation,
- white-box security evaluation,
- white-box engineering-quality evaluation.

Source code, databases, hidden routes and internal APIs are forbidden during blind UI benchmark runs.

## Scoring philosophy

The framework will expose 0–100 scores, but a single average must never conceal a critical failure. Raw metrics, normalized measures, dimension scores and hard gates are separate layers.

## Time measurement

Task time is a first-class metric from the first benchmark run. Initial runs may establish baselines before project-specific target times exist. User interaction time and system waiting time should be separable where technically possible.

## AI-first, human-readable

Initial benchmark execution is AI-first. Human studies can be added later as a separate evidence stream. Reports must remain readable and auditable by humans.

## Reproducibility

A benchmark result must eventually be traceable to at least:

- benchmark-core version,
- project-profile version,
- persona version,
- scenario version,
- fixture/test-data version,
- application/build version,
- evaluator model/version/configuration,
- run mode,
- environment/device/viewport,
- timestamp and run number.
