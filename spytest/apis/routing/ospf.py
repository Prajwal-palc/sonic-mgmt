"""
OSPF configuration and verification helpers for SpyTest test suites.

These utilities provide lightweight wrappers around SpyTest's CLI helpers so
testcases can push topology-aware configuration snippets and validate sonic-cli
outputs without re-implementing common parsing logic.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from spytest import st
from utilities.common import make_list

__all__ = [
    "apply_cli_sequence",
    "collect_cli_output",
    "check_cli_expectations",
    "is_cli_expectation_met",
    "format_expectation_failure",
]


def _normalize_command_sequence(commands: Iterable[str] | str | None) -> List[str]:
    """Return a sanitized list of CLI commands, dropping null or empty entries."""
    normalized: List[str] = []
    for entry in make_list(commands):
        if entry is None:
            continue
        line = str(entry).strip()
        if line:
            normalized.append(line)
    return normalized


def apply_cli_sequence(
    dut: str,
    commands: Iterable[str] | str | None,
    cli_type: str = "klish",
    skip_error_check: bool = False,
) -> Tuple[bool, Dict[str, str]]:
    """
    Execute each command in ``commands`` on the given ``dut``.

    Returns ``True`` when all commands run without raising an exception. When any
    command fails, the function logs the error and returns ``False`` so tests can
    react accordingly.
    """
    sequence = _normalize_command_sequence(commands)
    if not sequence:
        st.log(f"[OSPF] No commands to apply on {dut}")
        return True, {}

    def _normalize_response(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, (list, tuple)):
            return "\n".join(str(item) for item in value)
        return str(value)

    def _has_cli_error(text: str) -> bool:
        lowered = text.lower()
        return any(
            token in lowered
            for token in (
                "% error",
                "invalid input",
                "unknown command",
                "unrecognized command",
                "not found",
                "unsupported",
                "incomplete command",
            )
        )

    st.log(f"[OSPF] Applying CLI sequence on {dut} via {cli_type}: {sequence}")
    try:
        for command in sequence:
            config_kwargs = {
                "type": cli_type,
                "skip_error_check": skip_error_check,
            }
            if cli_type == "vtysh":
                config_kwargs["conf"] = True

            response = st.config(
                dut,
                command,
                **config_kwargs,
            )
            text = _normalize_response(response)
            if text and _has_cli_error(text):
                st.error(
                    f"[OSPF] CLI rejected '{command}' on {dut}: {text.strip()}"
                )
                return False, {
                    "command": command,
                    "output": text,
                    "dut": dut,
                }
    except Exception as exc:  # pylint: disable=broad-except
        st.error(f"[OSPF] Failed to run '{command}' on {dut}: {exc}")
        return False, {
            "command": command,
            "output": str(exc),
            "dut": dut,
            "exception": "1",
        }
    return True, {}


def collect_cli_output(
    dut: str,
    command: str,
    cli_type: str = "klish",
    skip_error_check: bool = True,
    sudo: bool = False,
) -> str:
    """
    Run ``command`` on ``dut`` and return raw output as a single string.

    The helper normalizes list/tuple responses from ``st.show`` and always
    returns a string, easing downstream substring checks.
    """
    output = st.show(
        dut,
        command,
        type=cli_type,
        skip_tmpl=True,
        skip_error_check=skip_error_check,
        sudo=sudo,
    )
    if isinstance(output, (list, tuple)):
        return "\n".join(str(line) for line in output)
    if output is None:
        return ""
    return str(output)


def check_cli_expectations(
    dut: str,
    command: str,
    expectation: Mapping[str, Sequence[str]] | None = None,
    cli_type: str = "klish",
    skip_error_check: bool = True,
    sudo: bool = False,
) -> Tuple[bool, Mapping[str, object]]:
    """
    Validate CLI output against expectation rules.

    Expectation keys:
        - ``all``: every string must be present
        - ``any``: at least one string must be present
        - ``none``: no string may be present

    Returns ``(ok, details)`` where ``details`` includes the captured output and
    any missing/unexpected strings to help build failure messages.
    """
    expectation = expectation or {}
    text = collect_cli_output(
        dut,
        command,
        cli_type=cli_type,
        skip_error_check=skip_error_check,
        sudo=sudo,
    )

    all_terms = [str(term) for term in make_list(expectation.get("all")) if term is not None]
    any_terms = [str(term) for term in make_list(expectation.get("any")) if term is not None]
    none_terms = [str(term) for term in make_list(expectation.get("none")) if term is not None]

    missing_all = [term for term in all_terms if term not in text]

    any_found = True
    missing_any: List[str] = []
    if any_terms:
        any_found = any(term in text for term in any_terms)
        if not any_found:
            missing_any = any_terms.copy()

    unexpected = [term for term in none_terms if term in text]

    ok = not missing_all and any_found and not unexpected
    details = {
        "command": command,
        "output": text,
        "missing_all": missing_all,
        "missing_any": missing_any,
        "unexpected": unexpected,
    }
    return ok, details


def is_cli_expectation_met(
    dut: str,
    command: str,
    expectation: Mapping[str, Sequence[str]] | None = None,
    cli_type: str = "klish",
    skip_error_check: bool = True,
    sudo: bool = False,
) -> bool:
    """Boolean shortcut over :func:`check_cli_expectations` for poll loops."""
    return check_cli_expectations(
        dut,
        command,
        expectation=expectation,
        cli_type=cli_type,
        skip_error_check=skip_error_check,
        sudo=sudo,
    )[0]


def format_expectation_failure(details: Mapping[str, object]) -> str:
    """
    Build a short human-readable message from ``check_cli_expectations`` output.
    """
    segments: List[str] = []

    missing_all = details.get("missing_all") or []
    if missing_all:
        segments.append(f"missing strings: {missing_all}")

    missing_any = details.get("missing_any") or []
    if missing_any:
        segments.append(f"none of the optional matches found: {missing_any}")

    unexpected = details.get("unexpected") or []
    if unexpected:
        segments.append(f"unexpected strings present: {unexpected}")

    if not segments:
        return "expectations satisfied"
    return "; ".join(str(segment) for segment in segments)
