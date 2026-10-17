# Generic SQBF project profiles and isolated application configurations

## Two independent layers

1. Generic runtime: sqbf/ (screenshot-only UI Executor, guarded actions,
   deterministic measurements, configurable LLM providers, reports).
   Do NOT add application names, workflow paths, data models, roles,
   customer data, or quality policy exceptions to the generic runtime.
2. Project profiles: projects/<project-id>/, each with its own scenario and
   fixture manifest. Only profiles may refer to business rules, test
   locations, domain terminology or application-specific permissions.

The common generic source template is projects/_template/ and is versioned.
It is deliberately **unconfigured**: no valid application URL or login,
no running fixture, no result baseline or benchmark screenshots.

## Create a blank reproducible profile (from source checkout)

    python -m sqbf.cli new-project --slug sample-app --name "Sample application"

This creates:
- projects/sample-app/project.json
- projects/sample-app/README.md
- projects/sample-app/scenarios/first-task.json
- projects/sample-app/fixtures/first-task.json

The command refuses an existing target and rejects slashes, traversal
and ambiguous project slugs. Given the same name, slug and template commit,
the resulting file bytes are reproducible without timestamps or secret values.
Source control pins the template and each project profile version.
The framework core and other projects are left unchanged.

BEFORE executing a new project, explicitly configure the scenario URL,
host allowlist, persona, task, expected visible end state and separate
fixture contract. The placeholder URL is invalid by design so an
unconfigured template cannot accidentally connect to a real service.
The project generator itself never modifies a target application's DB.

## Separate fixture lifecycle

"Reproducible" requires more than a versioned JSON document. The
project's responsible implementer must independently establish:
- isolated application instance and database/tenant/test data scope;
- deterministic seed state and safe, idempotent or snapshot-based reset;
- the scenario's required roles and seeded prerequisites;
- immutable software revision and fixture version per test run;
- independent authorized Oracle/expected-outcome verification;
- provenance and locally stored evidence, without secrets in Git.

The fixture JSON is an explicit *contract*, not a seed script.
Never interpret presence of a fixture JSON as confirmation a DB is
initialized or that a valid reset is safe. The executor is deliberately
isolated from environment/fixture setup and from the Oracle.

## First product profile: ELVA/BLE

See projects/ble-elva/project.json and
projects/ble-elva/fixtures/enzberg-sts-0-45-base-v1.json.

Only BLE's profile contains Enzberg, Laborleitung, STS 0–45 and the
two normative references. Its actual local web application, dedicated
fixture and authorized read-only persistence check remain pending under
GitHub Issue #11; the runner remains in PR #10 (Draft). This split
retains domain-specific benchmark work without contaminating the
reusable SQBF template.

## Testing and governance

No GitHub Actions. Run all checks locally with Codex/PowerShell:

    python -m unittest discover -s tests -v
    python -m sqbf.cli preflight --scenario projects/ble-elva/scenarios/sts-0-45-product.json

Additionally validate Playwright Chromium locally before a real UI run.
Preserve test command, versions, exit code and results in the PR/issue.
A visual PASS is never a verified functional PASS without the separate
Oracle. Do not merge or mark Done solely because code was pushed.
