"""Local evidence and human-readable report; no screenshots committed to Git."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Evidence:
    def __init__(self, path: Path):
        self.path = path
        self.path.mkdir(parents=True, exist_ok=False)
        self.events: list[dict] = []
        self.images: list[dict] = []

    def event(self, kind: str, **values) -> None:
        self.events.append({"time": now_iso(), "kind": kind, **values})
        self.flush()

    def snapshot(self, png: bytes, label: str) -> None:
        name = f"{len(self.images):03d}-{label}.png"
        (self.path / name).write_bytes(png)
        self.images.append({"name": name, "label": label, "sha256": hashlib.sha256(png).hexdigest()})
        self.flush()

    def flush(self) -> None:
        (self.path / "events.json").write_text(
            json.dumps(self.events, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (self.path / "evidence.json").write_text(
            json.dumps(self.images, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def finish(self, manifest: dict, review: dict | None, status: str) -> None:
        payload = {**manifest, "verdict": status, "review": review or {}}
        (self.path / "run.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        findings = review.get("findings", []) if review else []
        lines = [
            "# Software Quality Blackbox Benchmark – Run Report", "",
            f"- Run ID: {manifest['run_id']}",
            f"- Szenario: {manifest['scenario_id']}",
            f"- Persona: {manifest['persona']}",
            f"- Executor: {manifest['executor_model']}",
            f"- Analyst: {manifest.get('analyst_model') or 'nicht ausgeführt'}",
            f"- Fixture: {manifest['fixture_id']}",
            f"- Software-Version: {manifest['software_version']}",
            f"- Status: **{status}**",
            f"- Technischer Runner: **{manifest.get('technical_status', 'nicht bewertet')}**",
            f"- Fachliches Ergebnis: **{manifest.get('functional_status', 'nicht bewertet')}**",
            f"- Executor-Endstatus: {manifest['executor_status']}",
            f"- Modellwartezeit: {manifest.get('model_wait_seconds', 0):.1f} Sekunden",
            f"- Aktive Runnerzeit (ohne Modellwartezeit): {manifest.get('active_seconds_excluding_model_wait', manifest['wall_seconds']):.1f} Sekunden",
            "- Fachlicher PASS: **nicht bestätigt** (kein unabhängiger Persistenz-Oracle im MVP)",
            f"- UI-Aktionen: {manifest['actions']} / {manifest['budget_actions']}",
            f"- Dauer (Wallclock, inklusive KI-Wartezeit): {manifest['wall_seconds']:.1f} Sekunden",
            "", "## Nachweise",
        ]
        lines.extend(f"- {im['name']} (SHA-256: {im['sha256']})" for im in self.images)
        lines.extend(["", "## Bewertung", "", str((review or {}).get("reason", "Keine fachliche Bewertung.")), "", "## Findings"])
        if findings:
            lines.extend(f"- {str(finding)}" for finding in findings)
        else:
            lines.append("- Keine dokumentiert oder nicht bewertet.")
        lines.extend([
            "", "## Einschränkungen", "",
            "- Screenshots verbleiben lokal; sensible Inhalte vor Weitergabe prüfen.",
            "- VISUAL_PASS_PENDING_ORACLE bedeutet, dass der Analyst den sichtbaren Endzustand unterstützt; ohne getrennten fachlichen Oracle-Nachweis ist dies kein fachlicher PASS und beweist keine Datenbank-Persistenz.",
            "- Ein erfolgreiches Agenten-Endsignal allein wird nicht als PASS gewertet.",
        ])
        (self.path / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
