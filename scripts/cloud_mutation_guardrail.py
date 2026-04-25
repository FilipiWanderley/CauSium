#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PatternRule:
    key: str
    regex: re.Pattern[str]


@dataclass(frozen=True)
class AllowlistRule:
    path_regex: re.Pattern[str]
    pattern_key: str
    reason: str


PATTERN_RULES: tuple[PatternRule, ...] = (
    PatternRule("begin_create_or_update", re.compile(r"begin_create_or_update", re.IGNORECASE)),
    PatternRule("create_or_update", re.compile(r"create_or_update", re.IGNORECASE)),
    PatternRule("run_instances", re.compile(r"run_instances", re.IGNORECASE)),
    PatternRule("stop_instances", re.compile(r"stop_instances", re.IGNORECASE)),
    PatternRule("delete_resource", re.compile(r"delete_resource", re.IGNORECASE)),
    PatternRule("delete_", re.compile(r"\bdelete_", re.IGNORECASE)),
    PatternRule("patch", re.compile(r"\.patch\(", re.IGNORECASE)),
    PatternRule("resize", re.compile(r"\bresize\b", re.IGNORECASE)),
    PatternRule("scale", re.compile(r"\bscale\b", re.IGNORECASE)),
    PatternRule("setIamPolicy", re.compile(r"setIamPolicy", re.IGNORECASE)),
)

TEXT_EXTENSIONS = {
    ".py",
    ".txt",
    ".md",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".sh",
}


def _read_allowlist(allowlist_path: Path) -> list[AllowlistRule]:
    if not allowlist_path.exists():
        return []
    rules: list[AllowlistRule] = []
    for line in allowlist_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        parts = raw.split("::", 2)
        if len(parts) != 3:
            raise ValueError(
                "Linha invalida na allowlist. Use: <path_regex>::<pattern_key>::<reason>\n"
                f"Linha: {raw}"
            )
        path_expr, pattern_key, reason = parts
        keys = {rule.key for rule in PATTERN_RULES}
        if pattern_key not in keys:
            raise ValueError(f"pattern_key desconhecido na allowlist: {pattern_key}")
        rules.append(
            AllowlistRule(
                path_regex=re.compile(path_expr),
                pattern_key=pattern_key,
                reason=reason.strip(),
            )
        )
    return rules


def _is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS


def _is_allowed(rel_path: str, pattern_key: str, allowlist: list[AllowlistRule]) -> str | None:
    for rule in allowlist:
        if rule.pattern_key != pattern_key:
            continue
        if rule.path_regex.search(rel_path):
            return rule.reason
    return None


def _scan(target: Path, allowlist: list[AllowlistRule]) -> tuple[list[str], list[str]]:
    violations: list[str] = []
    suppressed: list[str] = []
    for path in sorted(target.rglob("*")):
        if not path.is_file() or not _is_text_file(path):
            continue
        rel_path = str(path.as_posix())
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(content.splitlines(), start=1):
            for rule in PATTERN_RULES:
                if not rule.regex.search(line):
                    continue
                reason = _is_allowed(rel_path, rule.key, allowlist)
                snippet = line.strip()
                if reason:
                    suppressed.append(
                        f"{rel_path}:{line_number} [{rule.key}] SUPRIMIDO ({reason})"
                    )
                    continue
                violations.append(
                    f"{rel_path}:{line_number} [{rule.key}] {snippet[:180]}"
                )
    return violations, suppressed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Guardrail para bloquear assinaturas de mutacao cloud em backend/app."
    )
    parser.add_argument(
        "--target",
        default="backend/app",
        help="Diretorio alvo para scan (padrao: backend/app).",
    )
    parser.add_argument(
        "--allowlist",
        default=".security/cloud_mutation_guardrail_allowlist.txt",
        help="Arquivo de allowlist (padrao: .security/cloud_mutation_guardrail_allowlist.txt).",
    )
    args = parser.parse_args()

    target = Path(args.target)
    if not target.exists():
        print(f"[guardrail] Target nao encontrado: {target}")
        return 2

    allowlist = _read_allowlist(Path(args.allowlist))
    violations, suppressed = _scan(target, allowlist)

    print(f"[guardrail] Escaneado: {target}")
    print(f"[guardrail] Regras: {', '.join(rule.key for rule in PATTERN_RULES)}")
    print(f"[guardrail] Itens suprimidos por allowlist: {len(suppressed)}")
    for line in suppressed[:50]:
        print(f"  - {line}")
    if len(suppressed) > 50:
        print(f"  ... {len(suppressed) - 50} itens suprimidos adicionais")

    if violations:
        print(f"[guardrail] FALHA: encontradas {len(violations)} ocorrencias suspeitas.")
        for line in violations:
            print(f"  - {line}")
        print(
            "\n[guardrail] Para excecao, documente em .security/cloud_mutation_guardrail_allowlist.txt "
            "no formato: <path_regex>::<pattern_key>::<reason>"
        )
        return 1

    print("[guardrail] OK: nenhuma ocorrencia suspeita nao-allowlisted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
