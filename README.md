# Software Quality Benchmark Framework (SQBF)

A versioned, AI-first framework for evaluating software quality in a reproducible way.

## Current phase

The project is currently in **Foundation Research**. The immediate goal is to define the benchmark methodology before implementing a runner or dashboard.

Initial MVP target:

1. define a generic quality model,
2. define reproducible metrics, scoring and hard gates,
3. define evaluator and scenario contracts,
4. define project-specific profiles separately from the generic core,
5. execute AI-driven benchmark runs,
6. generate structured evidence and a human-readable Markdown report.

A local web application for visualization, trend analysis, benchmark configuration and enterprise use is a later product phase and is not part of the first MVP.

## Design principles

- Generic benchmark logic and project-specific rules are strictly separated.
- Raw measurements, normalized measures, scores and hard gates are different concepts.
- Critical failures must not be hidden by averages.
- Time and efficiency are measured from the first benchmark runs, even before target times exist.
- AI evaluators are versioned inputs to the benchmark and must not be treated as perfectly deterministic.
- Black-box UI testing must not use source code, database access, internal APIs, developer tools or hidden routes.
- Human-readable reports are required; structured run data will be retained so a later web UI can consume it without parsing Markdown.
- Research conclusions, assumptions and recommendations must remain traceable to their sources.

## Foundation research plan

- **R00** Research methodology and evidence rules
- **R01** Generic software quality model
- **R02** Usability and human-computer interaction
- **R03** Time, efficiency and performance measurement
- **R04** Scoring, normalization and statistics
- **R05** AI evaluator reproducibility and calibration
- **R06** Security assurance
- **R07** Accessibility, reliability and resilience
- **R08** Persona, skill and scenario model
- **R09** First project evidence inventory
- **R10** Foundation 1.0 synthesis
- **R11** Engineering quality and secure development standard

See `research/README.md` for the research contract and sequencing.

## Status

No benchmark score is considered authoritative until Foundation 1.0 has defined the measurement, scoring, gate and reproducibility contracts.
