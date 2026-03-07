from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .types import GenerationRecord, JudgmentRecord, RunManifest


class RunStorage:
    def __init__(self, root: Path, run_name: str):
        self.root = root
        self.run_name = run_name
        self.run_dir = root / "runs" / run_name
        self.outputs_dir = self.run_dir / "outputs"
        self.judgments_dir = self.run_dir / "judgments"
        self.analysis_dir = self.run_dir / "analysis"

    def ensure_dirs(self) -> None:
        for path in [self.outputs_dir, self.judgments_dir, self.analysis_dir]:
            path.mkdir(parents=True, exist_ok=True)

    def manifest_path(self) -> Path:
        return self.run_dir / "manifest.json"

    def write_manifest(self, manifest: RunManifest) -> None:
        self.ensure_dirs()
        self._write_json(self.manifest_path(), asdict(manifest))

    def load_manifest(self) -> Optional[RunManifest]:
        path = self.manifest_path()
        if not path.exists():
            return None
        data = self._read_json(path)
        return RunManifest(**data)

    def output_path(self, benchmark_version: str, prompt_id: str, candidate_model_id: str) -> Path:
        return self.outputs_dir / benchmark_version / prompt_id / f"{_safe_name(candidate_model_id)}.json"

    def judgment_path(
        self,
        benchmark_version: str,
        prompt_id: str,
        candidate_model_id: str,
        judge_model_id: str,
    ) -> Path:
        return (
            self.judgments_dir
            / benchmark_version
            / prompt_id
            / _safe_name(candidate_model_id)
            / f"{_safe_name(judge_model_id)}.json"
        )

    def has_output(self, benchmark_version: str, prompt_id: str, candidate_model_id: str) -> bool:
        return self.output_path(benchmark_version, prompt_id, candidate_model_id).exists()

    def has_judgment(
        self,
        benchmark_version: str,
        prompt_id: str,
        candidate_model_id: str,
        judge_model_id: str,
    ) -> bool:
        return self.judgment_path(benchmark_version, prompt_id, candidate_model_id, judge_model_id).exists()

    def write_output(self, record: GenerationRecord) -> None:
        path = self.output_path(record.benchmark_version, record.prompt_id, record.candidate_model_id)
        self._write_json(path, asdict(record))

    def write_judgment(self, record: JudgmentRecord) -> None:
        path = self.judgment_path(
            record.benchmark_version,
            record.prompt_id,
            record.candidate_model_id,
            record.judge_model_id,
        )
        self._write_json(path, asdict(record))

    def load_outputs(self) -> List[GenerationRecord]:
        records: List[GenerationRecord] = []
        for path in sorted(self.outputs_dir.rglob("*.json")):
            if path.name == "manifest.json":
                continue
            data = self._read_json(path)
            records.append(GenerationRecord(**data))
        return records

    def load_judgments(self) -> List[JudgmentRecord]:
        records: List[JudgmentRecord] = []
        for path in sorted(self.judgments_dir.rglob("*.json")):
            data = self._read_json(path)
            records.append(JudgmentRecord(**data))
        return records

    def write_analysis_json(self, filename: str, payload: Dict[str, object]) -> Path:
        path = self.analysis_dir / filename
        self._write_json(path, payload)
        return path

    def write_analysis_text(self, filename: str, text: str) -> Path:
        path = self.analysis_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def write_analysis_bytes(self, filename: str, content: bytes) -> Path:
        path = self.analysis_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def _write_json(self, path: Path, payload: Dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")

    def _read_json(self, path: Path) -> Dict[str, object]:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)


def _safe_name(value: str) -> str:
    return value.replace("/", "__").replace(":", "_")
