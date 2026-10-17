# Software Quality Benchmark Framework (SQBF)

A versioned, AI-first framework for evaluating software quality in a reproducible way.

## Current phase

The project has **ongoing Foundation Research** and an **unmerged local MVP prototype**. The first bounded real CORE-SMOKE-01 run has passed with independent database evidence. LAB-01 uses a separate disposable working copy; authoritative quality scoring remains a separate methodology milestone.

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

## Framework structure and reusable project profiles

- `sqbf/`: product-neutral runner, providers, action-policy, reporting and scaffold.
- `projects/_template/`: **blank versioned project template**; no application URLs, valid user accounts, seed datasets or run artifacts.
- `projects/ble-elva/`: project-specific profile, STS 0–45 scenario and external fixture contract.
- `runs/` (ignored by Git): local generated screenshots, JSON evidence and reports.

To create a new independent project in a clean directory, from the repository root:

    python -m sqbf.cli new-project --slug example-app --name "Example application"

This creates `projects/example-app/` only if it does not exist. Running the same command in separate fresh directories with equal inputs yields identical configuration files. It intentionally cannot pass preflight until you replace its configuration placeholders and set up an isolated fixture. See `docs/project-profiles.md`.

All tests are **local-only** (Codex/PowerShell + Python unittest + Playwright); GitHub Actions is not used.

## BLE/ELVA executable MVP (implementation in review)

A small Playwright and screenshot-vision runner now exists under sqbf/ and
projects/ble-elva/ on the proposed implementation branch. See
projects/ble-elva/README.md for Windows setup, local isolated fixture
requirements, sample CLI commands and important security limitations.

CORE-SMOKE-01 run `04bd06b3-f868-4390-b7d6-3df67e9cb85f` passed technical, independent no-write Oracle and reviewer checks. LAB-01 v0.3 adds bounded product creation in a separate working copy with a SELECT-only persistence Oracle. See [local operations](projects/ble-elva/operations.md). These process proofs do not replace Foundation methodology or establish an authoritative software-quality score. The regular NSN014 v0.4 suite is technically ready (model-free readiness passed) but has not been run; see the [completion report](docs/nsn014-v04-completion-report.md). PR #10 remains Draft; no automatic merge.
