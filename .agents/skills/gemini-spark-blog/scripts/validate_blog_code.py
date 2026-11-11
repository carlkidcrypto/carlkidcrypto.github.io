#!/usr/bin/env python3
"""Validate and test example code blocks in blog posts.

Checks:
1. Python syntax & compilation: Parses with ast.parse and compile(mode='exec').
2. ezsnmp API compliance:
   - Detects and rejects legacy easysnmp imports.
   - Detects non-existent exceptions (e.g. EasySNMPError -> GenericError, EasySNMPTimeoutError -> TimeoutError).
   - Detects legacy methods on Session (.bulkwalk -> .bulk_walk, .get_bulk -> .bulk_get).
   - Detects legacy attributes on Result (.oid_index -> .index, .snmp_type -> .type).
3. Bash / Shell syntax: Validates with `bash -n`.
4. YAML syntax: Validates with yaml.safe_load.
5. Runtime Test Harness:
   - Executes runnable Python snippets in an isolated scope with a simulated mock ezsnmp session.
   - Verifies runtime execution without NameError, AttributeError, TypeError, KeyError, or unhandled exceptions.
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


def find_repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".git").exists() or (p / "source" / "blog").exists():
            return p
        p = p.parent
    cwd = Path.cwd().resolve()
    if (cwd / ".git").exists() or (cwd / "source" / "blog").exists():
        return cwd
    return Path(__file__).resolve().parents[4]


REPO_ROOT = find_repo_root()
BLOG_DIR = REPO_ROOT / "source" / "blog"
EXAMPLE_SCRIPTS_DIR = REPO_ROOT / "example_scripts"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/carlkidcrypto/carlkidcrypto.github.io/main/example_scripts"


@dataclass
class CodeBlock:
    post_path: Path
    line_number: int
    language: str
    code: str
    raw_code: str


@dataclass
class ValidationIssue:
    post_path: Path
    line_number: int
    severity: str  # "ERROR" or "WARNING"
    message: str
    code_snippet: str = ""


# ---------------------------------------------------------------------------
# Code Extraction
# ---------------------------------------------------------------------------


def extract_code_blocks(post_path: Path) -> List[CodeBlock]:
    """Extract code blocks from RST or Markdown files with accurate line numbers."""
    content = post_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    blocks: List[CodeBlock] = []

    if post_path.suffix.lower() == ".md":
        in_fence = False
        fence_lang = ""
        fence_lineno = 0
        fence_lines: List[str] = []
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("```"):
                if not in_fence:
                    in_fence = True
                    fence_lineno = idx + 1
                    fence_lang = stripped.lstrip("`").strip().lower()
                    fence_lines = []
                else:
                    in_fence = False
                    raw_code = "\n".join(fence_lines)
                    code = textwrap.dedent(raw_code).strip()
                    if code and fence_lang:
                        blocks.append(
                            CodeBlock(
                                post_path=post_path,
                                line_number=fence_lineno,
                                language=fence_lang,
                                code=code,
                                raw_code=raw_code,
                            )
                        )
            elif in_fence:
                fence_lines.append(line)
        return blocks

    pattern = re.compile(r"^([ \t]*)\.\.\s+code-block::\s*(\w+)")
    i = 0
    while i < len(lines):
        match = pattern.match(lines[i])
        if match:
            indent_str = match.group(1)
            language = match.group(2).lower()
            header_lineno = i + 1

            # Advance past blank lines
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1

            if i >= len(lines):
                break

            # The block must be indented more than the directive
            raw_block_lines: List[str] = []
            while i < len(lines):
                line = lines[i]
                if not line.strip():
                    raw_block_lines.append("")
                    i += 1
                    continue
                # Check indentation
                curr_indent = len(line) - len(line.lstrip(" "))
                base_indent = len(indent_str)
                if curr_indent > base_indent:
                    raw_block_lines.append(line)
                    i += 1
                else:
                    break

            # Strip directive options (e.g. :linenos:, :caption:, etc.)
            block_lines: List[str] = []
            in_options = True
            for b_line in raw_block_lines:
                s_line = b_line.strip()
                if in_options:
                    if not s_line:
                        in_options = False
                        continue
                    if re.match(r"^:[a-zA-Z0-9_-]+:.*$", s_line):
                        continue
                    in_options = False
                block_lines.append(b_line)

            raw_code = "\n".join(block_lines)
            code = textwrap.dedent(raw_code).strip()
            if code:
                blocks.append(
                    CodeBlock(
                        post_path=post_path,
                        line_number=header_lineno,
                        language=language,
                        code=code,
                        raw_code=raw_code,
                    )
                )
            continue
        i += 1

    return blocks


# ---------------------------------------------------------------------------
# Static & Syntax Validations
# ---------------------------------------------------------------------------

LEGACY_EXCEPTION_MAP = {
    "EasySNMPError": "GenericError",
    "EasySNMPTimeoutError": "TimeoutError",
    "EasySNMPConnectionError": "ConnectionError",
    "EasySNMPNoSuchInstanceError": "NoSuchInstanceError",
    "EasySNMPNoSuchNameError": "NoSuchNameError",
    "EasySNMPNoSuchObjectError": "NoSuchObjectError",
    "EasySNMPUndeterminedTypeError": "UndeterminedTypeError",
    "EasySNMPUnknownObjectIDError": "UnknownObjectIDError",
    "EasySNMPPacketError": "PacketError",
    "EasySNMPParseError": "ParseError",
}


def validate_python_syntax_and_api(block: CodeBlock) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []

    # 1. AST Parse
    try:
        tree = ast.parse(
            block.code, filename=f"{block.post_path.name}:{block.line_number}"
        )
    except SyntaxError as e:
        issues.append(
            ValidationIssue(
                post_path=block.post_path,
                line_number=block.line_number + (e.lineno or 1) - 1,
                severity="ERROR",
                message=f"Python SyntaxError: {e.msg} (line {e.lineno})",
                code_snippet=e.text.strip() if e.text else "",
            )
        )
        return issues

    # 2. Compilation check
    try:
        flags = ast.PyCF_ALLOW_TOP_LEVEL_AWAIT if sys.version_info >= (3, 8) else 0
        compile(
            block.code,
            filename=f"{block.post_path.name}:{block.line_number}",
            mode="exec",
            flags=flags,
        )
    except Exception as e:
        issues.append(
            ValidationIssue(
                post_path=block.post_path,
                line_number=block.line_number,
                severity="ERROR",
                message=f"Compilation failed: {e}",
            )
        )
        return issues

    # 3. Static AST analysis for ezsnmp API consistency
    for node in ast.walk(tree):
        # Check imports: reject legacy easysnmp
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "easysnmp":
                    issues.append(
                        ValidationIssue(
                            post_path=block.post_path,
                            line_number=block.line_number + node.lineno - 1,
                            severity="ERROR",
                            message="Legacy 'import easysnmp' detected. Use 'import ezsnmp' instead.",
                        )
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.module == "easysnmp":
                issues.append(
                    ValidationIssue(
                        post_path=block.post_path,
                        line_number=block.line_number + node.lineno - 1,
                        severity="ERROR",
                        message="Legacy 'from easysnmp import ...' detected. Use 'from ezsnmp import ...' instead.",
                    )
                )
            elif node.module in ("ezsnmp.exceptions", "ezsnmp"):
                for alias in node.names:
                    if alias.name in LEGACY_EXCEPTION_MAP:
                        target = LEGACY_EXCEPTION_MAP[alias.name]
                        issues.append(
                            ValidationIssue(
                                post_path=block.post_path,
                                line_number=block.line_number + node.lineno - 1,
                                severity="ERROR",
                                message=(
                                    f"Outdated exception 'from {node.module} import {alias.name}'. "
                                    f"In ezsnmp, use '{target}'."
                                ),
                            )
                        )
        elif isinstance(node, ast.Name):
            if node.id in LEGACY_EXCEPTION_MAP:
                target = LEGACY_EXCEPTION_MAP[node.id]
                issues.append(
                    ValidationIssue(
                        post_path=block.post_path,
                        line_number=block.line_number + node.lineno - 1,
                        severity="ERROR",
                        message=f"Legacy exception '{node.id}' detected. In ezsnmp, use '{target}'.",
                    )
                )

        # Check method calls on Session: bulkwalk -> bulk_walk, get_bulk -> bulk_get
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == "bulkwalk":
                    issues.append(
                        ValidationIssue(
                            post_path=block.post_path,
                            line_number=block.line_number + node.lineno - 1,
                            severity="ERROR",
                            message="Non-existent method 'session.bulkwalk()'. Use 'session.bulk_walk()'.",
                        )
                    )
                elif node.func.attr == "get_bulk":
                    issues.append(
                        ValidationIssue(
                            post_path=block.post_path,
                            line_number=block.line_number + node.lineno - 1,
                            severity="ERROR",
                            message="Non-existent method 'session.get_bulk()'. Use 'session.bulk_get()'.",
                        )
                    )

        # Check attribute access on Result objects: .oid_index -> .index, .snmp_type -> .type
        elif isinstance(node, ast.Attribute):
            if node.attr == "oid_index":
                issues.append(
                    ValidationIssue(
                        post_path=block.post_path,
                        line_number=block.line_number + node.lineno - 1,
                        severity="ERROR",
                        message="Legacy attribute '.oid_index' accessed. In ezsnmp Result objects, use '.index'.",
                    )
                )
            elif node.attr == "snmp_type":
                issues.append(
                    ValidationIssue(
                        post_path=block.post_path,
                        line_number=block.line_number + node.lineno - 1,
                        severity="ERROR",
                        message="Legacy attribute '.snmp_type' accessed. In ezsnmp Result objects, use '.type'.",
                    )
                )

    return issues


def validate_bash_syntax(block: CodeBlock) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    # Avoid validating markdown-style commentary or interactive prompt blocks
    lines = [
        line for line in block.code.splitlines() if not line.strip().startswith("#")
    ]
    sanitized = "\n".join(lines).strip()
    if not sanitized:
        return issues

    try:
        proc = subprocess.run(
            ["bash", "-n"],
            input=sanitized,
            text=True,
            capture_output=True,
            timeout=5,
        )
        if proc.returncode != 0:
            issues.append(
                ValidationIssue(
                    post_path=block.post_path,
                    line_number=block.line_number,
                    severity="ERROR",
                    message=f"Bash syntax error: {proc.stderr.strip()}",
                )
            )
    except Exception as e:
        issues.append(
            ValidationIssue(
                post_path=block.post_path,
                line_number=block.line_number,
                severity="WARNING",
                message=f"Could not execute bash -n: {e}",
            )
        )
    return issues


def validate_yaml_syntax(block: CodeBlock) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    try:
        import yaml

        yaml.safe_load(block.code)
    except Exception as e:
        issues.append(
            ValidationIssue(
                post_path=block.post_path,
                line_number=block.line_number,
                severity="ERROR",
                message=f"YAML parse error: {e}",
            )
        )
    return issues


# ---------------------------------------------------------------------------
# Mock ezsnmp Test Environment & Runtime Harness
# ---------------------------------------------------------------------------


class MockResult:
    """Simulated ezsnmp Result object for behavioral testing."""

    def __init__(self, oid: str, index: str, value: Any, type_: str = "OCTETSTR"):
        self.oid = str(oid)
        self.index = str(index)
        self.value = str(value)
        self.type = str(type_)
        self.converted_value = value

    @property
    def oid_index(self) -> str:
        # In ezsnmp, .index is canonical. If .oid_index is called, flag it.
        raise AttributeError(
            "ezsnmp Result object has no attribute 'oid_index'. Use 'index'."
        )

    @property
    def snmp_type(self) -> str:
        raise AttributeError(
            "ezsnmp Result object has no attribute 'snmp_type'. Use 'type'."
        )

    def __repr__(self) -> str:
        return f"Result(oid='{self.oid}', index='{self.index}', value='{self.value}', type='{self.type}')"


class MockSession:
    """Simulated ezsnmp Session that answers standard MIB queries."""

    def __init__(
        self,
        hostname: str = "localhost",
        community: str = "public",
        version: int = 2,
        **kwargs: Any,
    ):
        self.hostname = hostname
        self.community = community
        self.version = version
        self.kwargs = kwargs

    def __enter__(self) -> "MockSession":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    def close(self) -> None:
        pass

    def get(self, oids: Any) -> Tuple[MockResult, ...]:
        if isinstance(oids, (list, tuple)):
            return tuple(self._get_single(str(oid)) for oid in oids)
        return (self._get_single(str(oids)),)

    def _get_single(self, oid: str) -> MockResult:
        if "sysDescr" in oid or oid.endswith(".1.3.6.1.2.1.1.1.0"):
            return MockResult(
                "sysDescr",
                "0",
                "Cisco IOS Software, C3750E Software (C3750E-UNIVERSALK9-M)",
                "OCTETSTR",
            )
        if "sysName" in oid:
            return MockResult("sysName", "0", "core-sw01", "OCTETSTR")
        if "sysUpTime" in oid:
            return MockResult("sysUpTime", "0", "12345678", "TICKS")
        if "sysLocation" in oid:
            return MockResult("sysLocation", "0", "Data Center 1 - Rack 4", "OCTETSTR")
        if "pethMainPsePower" in oid:
            return MockResult("pethMainPsePower", "1", "740", "GAUGE")
        if "pethMainPseConsumptionPower" in oid:
            return MockResult("pethMainPseConsumptionPower", "1", "320", "GAUGE")
        return MockResult(oid, "0", "mock-value", "OCTETSTR")

    def get_next(self, oids: Any) -> Tuple[MockResult, ...]:
        return self.get(oids)

    def walk(self, oids: Any) -> Tuple[MockResult, ...]:
        return self.bulk_walk(oids)

    def bulk_walk(self, oids: Any, max_repetitions: int = 25) -> Tuple[MockResult, ...]:
        oid_name = str(oids)
        if "ifDescr" in oid_name:
            return (
                MockResult("ifDescr", "1", "GigabitEthernet0/1", "OCTETSTR"),
                MockResult("ifDescr", "2", "GigabitEthernet0/2", "OCTETSTR"),
                MockResult("ifDescr", "3", "TenGigabitEthernet0/1", "OCTETSTR"),
            )
        if "ifHCInOctets" in oid_name:
            return (
                MockResult("ifHCInOctets", "1", "1048576000", "COUNTER64"),
                MockResult("ifHCInOctets", "2", "2097152000", "COUNTER64"),
                MockResult("ifHCInOctets", "3", "5242880000", "COUNTER64"),
            )
        if "ifHCOutOctets" in oid_name:
            return (
                MockResult("ifHCOutOctets", "1", "948576000", "COUNTER64"),
                MockResult("ifHCOutOctets", "2", "1897152000", "COUNTER64"),
                MockResult("ifHCOutOctets", "3", "4242880000", "COUNTER64"),
            )
        if "bgpPeerState" in oid_name:
            return (
                MockResult("bgpPeerState", "192.0.2.1.0", "6", "INTEGER"),
                MockResult("bgpPeerState", "192.0.2.2.0", "6", "INTEGER"),
            )
        if "bgpPeerRemoteAs" in oid_name:
            return (
                MockResult("bgpPeerRemoteAs", "192.0.2.1.0", "64512", "INTEGER"),
                MockResult("bgpPeerRemoteAs", "192.0.2.2.0", "64513", "INTEGER"),
            )
        if "bgpPeerFsmEstablishedTime" in oid_name:
            return (
                MockResult("bgpPeerFsmEstablishedTime", "192.0.2.1.0", "3600", "GAUGE"),
                MockResult("bgpPeerFsmEstablishedTime", "192.0.2.2.0", "7200", "GAUGE"),
            )
        if "cbgpPeer2AcceptedPrefixes" in oid_name:
            return (
                MockResult(
                    "cbgpPeer2AcceptedPrefixes", "1.4.192.0.2.1.1.1", "150000", "GAUGE"
                ),
                MockResult(
                    "cbgpPeer2AcceptedPrefixes", "1.4.192.0.2.2.1.1", "850000", "GAUGE"
                ),
            )
        if "dot1qPvid" in oid_name:
            return (
                MockResult("dot1qPvid", "1", "10", "INTEGER"),
                MockResult("dot1qPvid", "2", "20", "INTEGER"),
            )
        if "pethPsePortDetectionStatus" in oid_name:
            return (
                MockResult("pethPsePortDetectionStatus", "1.1", "3", "INTEGER"),
                MockResult("pethPsePortDetectionStatus", "1.2", "1", "INTEGER"),
            )
        if "pethPsePortPowerPriority" in oid_name:
            return (
                MockResult("pethPsePortPowerPriority", "1.1", "1", "INTEGER"),
                MockResult("pethPsePortPowerPriority", "1.2", "3", "INTEGER"),
            )
        if "cpeExtPsePortPwrAllocated" in oid_name:
            return (
                MockResult("cpeExtPsePortPwrAllocated", "1.1", "15400", "GAUGE"),
                MockResult("cpeExtPsePortPwrAllocated", "1.2", "0", "GAUGE"),
            )
        if "cpeExtPsePortPwrConsumed" in oid_name:
            return (
                MockResult("cpeExtPsePortPwrConsumed", "1.1", "12100", "GAUGE"),
                MockResult("cpeExtPsePortPwrConsumed", "1.2", "0", "GAUGE"),
            )
        if "entPhysicalClass" in oid_name:
            return (
                MockResult("entPhysicalClass", "1", "3", "INTEGER"),
                MockResult("entPhysicalClass", "2", "9", "INTEGER"),
            )
        if "entPhysicalModelName" in oid_name:
            return (
                MockResult("entPhysicalModelName", "1", "WS-C3750E-48PD", "OCTETSTR"),
            )
        if "entPhysicalSerialNum" in oid_name:
            return (MockResult("entPhysicalSerialNum", "1", "FOC1234ABCD", "OCTETSTR"),)
        return (
            MockResult(oid_name, "1", "100", "INTEGER"),
            MockResult(oid_name, "2", "200", "INTEGER"),
        )

    def bulk_get(
        self, oids: Any, non_repeaters: int = 0, max_repetitions: int = 10
    ) -> Tuple[MockResult, ...]:
        return self.bulk_walk(oids, max_repetitions=max_repetitions)

    def set(self, *args: Any, **kwargs: Any) -> Tuple[MockResult, ...]:
        return (MockResult("sysLocation.0", "0", "updated", "OCTETSTR"),)


class DummyPool:
    def __init__(self, *args: Any, **kwargs: Any):
        pass

    def __enter__(self) -> "DummyPool":
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def map(
        self, func: Callable, iterable: Any, *args: Any, **kwargs: Any
    ) -> List[Any]:
        return [func(x) for x in iterable]

    def starmap(
        self, func: Callable, iterable: Any, *args: Any, **kwargs: Any
    ) -> List[Any]:
        return [func(*x) for x in iterable]

    def close(self) -> None:
        pass

    def join(self) -> None:
        pass


def execute_test_harness(
    block: CodeBlock, sandbox_globals: Dict[str, Any]
) -> List[ValidationIssue]:
    """Execute runnable Python code blocks in a sandbox with mock ezsnmp."""
    issues: List[ValidationIssue] = []

    # Check if snippet contains runnable logic (functions or top-level execution)
    # Skip snippets that are purely shell/interactive output or isolated 1-2 line snippets
    if len(block.code.splitlines()) < 4:
        return issues

    # Pre-populate Session and Result
    import asyncio

    sandbox_globals.setdefault("asyncio", asyncio)
    sandbox_globals.setdefault("Session", MockSession)
    sandbox_globals.setdefault("Result", MockResult)
    sandbox_globals.setdefault("DEVICE_INVENTORY", ["192.168.1.1", "192.168.1.2"])

    class DummyDataFrame:
        def write_parquet(self, *a: Any, **k: Any) -> None:
            pass

    sandbox_globals.setdefault("telemetry_df", DummyDataFrame())

    # Install ezsnmp mock into sys.modules during execution
    import types

    mock_ezsnmp = types.ModuleType("ezsnmp")
    mock_exceptions = types.ModuleType("ezsnmp.exceptions")

    class GenericError(Exception):
        pass

    class TimeoutError(GenericError):
        pass

    class ConnectionError(GenericError):
        pass

    class NoSuchInstanceError(GenericError):
        pass

    class NoSuchNameError(GenericError):
        pass

    class NoSuchObjectError(GenericError):
        pass

    class PacketError(GenericError):
        pass

    class ParseError(GenericError):
        pass

    class UndeterminedTypeError(GenericError):
        pass

    class UnknownObjectIDError(GenericError):
        pass

    mock_exceptions.GenericError = GenericError
    mock_exceptions.TimeoutError = TimeoutError
    mock_exceptions.ConnectionError = ConnectionError
    mock_exceptions.NoSuchInstanceError = NoSuchInstanceError
    mock_exceptions.NoSuchNameError = NoSuchNameError
    mock_exceptions.NoSuchObjectError = NoSuchObjectError
    mock_exceptions.PacketError = PacketError
    mock_exceptions.ParseError = ParseError
    mock_exceptions.UndeterminedTypeError = UndeterminedTypeError
    mock_exceptions.UnknownObjectIDError = UnknownObjectIDError

    mock_ezsnmp.Session = MockSession
    mock_ezsnmp.Result = MockResult
    mock_ezsnmp.exceptions = mock_exceptions
    mock_ezsnmp.GenericError = GenericError
    mock_ezsnmp.TimeoutError = TimeoutError
    mock_ezsnmp.ConnectionError = ConnectionError
    mock_ezsnmp.NoSuchInstanceError = NoSuchInstanceError
    mock_ezsnmp.NoSuchObjectError = NoSuchObjectError
    mock_ezsnmp.PacketError = PacketError
    mock_ezsnmp.ParseError = ParseError
    mock_ezsnmp.UndeterminedTypeError = UndeterminedTypeError
    mock_ezsnmp.UnknownObjectIDError = UnknownObjectIDError

    # Patch sys.modules
    old_ezsnmp = sys.modules.get("ezsnmp")
    old_exceptions = sys.modules.get("ezsnmp.exceptions")
    sys.modules["ezsnmp"] = mock_ezsnmp
    sys.modules["ezsnmp.exceptions"] = mock_exceptions

    # Mock purpleair_api
    mock_purpleair_module = types.ModuleType("purpleair_api")
    mock_paa_mod = types.ModuleType("purpleair_api.PurpleAirAPI")
    mock_pread_mod = types.ModuleType("purpleair_api.PurpleAirReadAPI")
    mock_pwrite_mod = types.ModuleType("purpleair_api.PurpleAirWriteAPI")
    mock_plocal_mod = types.ModuleType("purpleair_api.PurpleAirLocalAPI")

    class MockPurpleAirBase:
        def __init__(self, *a: Any, **k: Any): pass
        def request_sensor_data(self, *a: Any, **k: Any) -> Dict[str, Any]:
            return {"sensor": {"name": "Mock Station", "pm2.5_atm": 12.5, "pm2.5_cf_1": 12.0, "temperature": 72.0, "humidity": 45.0, "pressure": 1013.25}}
        def request_multiple_sensors_data(self, *a: Any, **k: Any) -> Dict[str, Any]:
            return {"fields": ["name", "latitude", "longitude", "pm2.5_atm", "temperature"], "data": [["Mock Sensor 1", 46.7, -117.1, 10.2, 70.0]]}
        def request_group_data(self, *a: Any, **k: Any) -> Dict[str, Any]:
            return {"group_id": 1234, "name": "Mock Group"}
        def request_members_data(self, *a: Any, **k: Any) -> Dict[str, Any]:
            return {"fields": ["sensor_index", "name", "pm2.5_atm"], "data": [[282168, "Mock Station", 12.5]]}
        def post_create_group_data(self, *a: Any, **k: Any) -> Dict[str, Any]:
            return {"group_id": 1234, "name": "Mock Group"}
        def post_create_member(self, *a: Any, **k: Any) -> Dict[str, Any]:
            return {"member_id": 5678, "sensor_index": 282168}
        def request_local_sensor_data(self, *a: Any, **k: Any) -> Dict[str, Any]:
            return {"SensorId": "MockLocal", "pm2_5_atm": 12.5, "current_temp_f": 72.0, "current_humidity": 45.0, "pressure": 1013.25}

    mock_paa_mod.PurpleAirAPI = MockPurpleAirBase
    mock_pread_mod.PurpleAirReadAPI = MockPurpleAirBase
    mock_pwrite_mod.PurpleAirWriteAPI = MockPurpleAirBase
    mock_plocal_mod.PurpleAirLocalAPI = MockPurpleAirBase
    mock_purpleair_module.PurpleAirAPI = MockPurpleAirBase
    mock_purpleair_module.PurpleAirReadAPI = MockPurpleAirBase
    mock_purpleair_module.PurpleAirWriteAPI = MockPurpleAirBase
    mock_purpleair_module.PurpleAirLocalAPI = MockPurpleAirBase

    old_purpleair = sys.modules.get("purpleair_api")
    old_purpleair_api = sys.modules.get("purpleair_api.PurpleAirAPI")
    old_purpleair_read = sys.modules.get("purpleair_api.PurpleAirReadAPI")
    old_purpleair_write = sys.modules.get("purpleair_api.PurpleAirWriteAPI")
    old_purpleair_local = sys.modules.get("purpleair_api.PurpleAirLocalAPI")
    sys.modules["purpleair_api"] = mock_purpleair_module
    sys.modules["purpleair_api.PurpleAirAPI"] = mock_paa_mod
    sys.modules["purpleair_api.PurpleAirReadAPI"] = mock_pread_mod
    sys.modules["purpleair_api.PurpleAirWriteAPI"] = mock_pwrite_mod
    sys.modules["purpleair_api.PurpleAirLocalAPI"] = mock_plocal_mod

    # Default environment variables for mock tests
    os.environ.setdefault("PURPLEAIR_READ_KEY", "mock-read-key-12345")
    os.environ.setdefault("PURPLEAIR_WRITE_KEY", "mock-write-key-12345")

    # Mock time.sleep, multiprocessing.Pool, and ProcessPoolExecutor to avoid blocking or pickling issues
    import time
    import multiprocessing
    import concurrent.futures

    old_sleep = time.sleep
    old_pool = getattr(multiprocessing, "Pool", None)
    old_ppe = getattr(concurrent.futures, "ProcessPoolExecutor", None)

    sleep_count = 0

    def mock_sleep(s: Any) -> None:
        nonlocal sleep_count
        sleep_count += 1
        if sleep_count >= 2:
            raise KeyboardInterrupt("Simulated test loop exit")

    time.sleep = mock_sleep
    multiprocessing.Pool = DummyPool
    concurrent.futures.ProcessPoolExecutor = concurrent.futures.ThreadPoolExecutor

    # Redirect stdout and feed mock stdin to keep test execution non-blocking
    import io

    old_stdout = sys.stdout
    old_stdin = sys.stdin
    sys.stdout = io.StringIO()
    sys.stdin = io.StringIO("PING\nget\n.1.3.6.1.4.1.99999.1.1.0\n\n")

    # Mock external network bindings
    try:
        import prometheus_client

        prometheus_client.start_http_server = lambda *a, **k: None
    except Exception:
        pass

    import subprocess

    old_popen = subprocess.Popen

    class DummyProc:
        def __init__(self, *a: Any, **k: Any):
            self.returncode = 0

        def terminate(self) -> None:
            pass

        def wait(self, *a: Any, **k: Any) -> int:
            return 0

        def poll(self) -> int:
            return 0

    subprocess.Popen = DummyProc  # type: ignore

    # Mock importlib.metadata.version for ezsnmp package version lookups
    import importlib.metadata

    old_version_fn = getattr(importlib.metadata, "version", None)

    def mock_version(pkg_name: str) -> str:
        if pkg_name == "ezsnmp":
            return "2.5.0"
        if old_version_fn is not None:
            return old_version_fn(pkg_name)
        return "1.0.0"

    importlib.metadata.version = mock_version  # type: ignore

    try:
        flags = ast.PyCF_ALLOW_TOP_LEVEL_AWAIT if sys.version_info >= (3, 8) else 0
        compiled = compile(
            block.code,
            filename=f"{block.post_path.name}:{block.line_number}",
            mode="exec",
            flags=flags,
        )
        CO_COROUTINE = 0x0080
        if getattr(compiled, "co_flags", 0) & CO_COROUTINE:
            coro = eval(compiled, sandbox_globals)
            if inspect.iscoroutine(coro):
                asyncio.run(coro)
        else:
            exec(compiled, sandbox_globals)
    except KeyboardInterrupt:
        # Graceful exit for continuous telemetry loops
        pass
    except (ImportError, ModuleNotFoundError) as e:
        err_msg = str(e)
        mod_name = getattr(e, "name", "") or ""
        if isinstance(e, importlib.metadata.PackageNotFoundError):
            # In CI environments where ezsnmp isn't installed as a distribution wheel
            pass
        elif "cannot import name" in err_msg and (
            "ezsnmp" in err_msg or "EasySNMP" in err_msg
        ):
            issues.append(
                ValidationIssue(
                    post_path=block.post_path,
                    line_number=block.line_number,
                    severity="ERROR",
                    message=f"Invalid ezsnmp symbol or import: {type(e).__name__}: {e}",
                )
            )
        elif (
            mod_name.startswith("ezsnmp") or "ezsnmp" in err_msg
        ) and "No package metadata" not in err_msg:
            issues.append(
                ValidationIssue(
                    post_path=block.post_path,
                    line_number=block.line_number,
                    severity="ERROR",
                    message=f"Invalid ezsnmp import: {type(e).__name__}: {e}",
                )
            )
        else:
            # If external optional package like pynetbox or opentelemetry is missing in test environment, skip execution
            pass
    except Exception as e:
        issues.append(
            ValidationIssue(
                post_path=block.post_path,
                line_number=block.line_number,
                severity="ERROR",
                message=f"Runtime test execution failed: {type(e).__name__}: {e}",
            )
        )
    finally:
        if old_version_fn is not None:
            importlib.metadata.version = old_version_fn  # type: ignore
        sys.stdout = old_stdout
        sys.stdin = old_stdin
        subprocess.Popen = old_popen
        time.sleep = old_sleep
        if old_pool is not None:
            multiprocessing.Pool = old_pool
        if old_ppe is not None:
            concurrent.futures.ProcessPoolExecutor = old_ppe
        if old_ezsnmp is not None:
            sys.modules["ezsnmp"] = old_ezsnmp
        else:
            sys.modules.pop("ezsnmp", None)
        if old_exceptions is not None:
            sys.modules["ezsnmp.exceptions"] = old_exceptions
        else:
            sys.modules.pop("ezsnmp.exceptions", None)
        if old_purpleair is not None:
            sys.modules["purpleair_api"] = old_purpleair
        else:
            sys.modules.pop("purpleair_api", None)
        if old_purpleair_api is not None:
            sys.modules["purpleair_api.PurpleAirAPI"] = old_purpleair_api
        else:
            sys.modules.pop("purpleair_api.PurpleAirAPI", None)
        if old_purpleair_read is not None:
            sys.modules["purpleair_api.PurpleAirReadAPI"] = old_purpleair_read
        else:
            sys.modules.pop("purpleair_api.PurpleAirReadAPI", None)
        if old_purpleair_write is not None:
            sys.modules["purpleair_api.PurpleAirWriteAPI"] = old_purpleair_write
        else:
            sys.modules.pop("purpleair_api.PurpleAirWriteAPI", None)
        if old_purpleair_local is not None:
            sys.modules["purpleair_api.PurpleAirLocalAPI"] = old_purpleair_local
        else:
            sys.modules.pop("purpleair_api.PurpleAirLocalAPI", None)

    return issues


# ---------------------------------------------------------------------------
# Auto-Fixer Utility
# ---------------------------------------------------------------------------


def auto_fix_code_block(code: str) -> str:
    """Normalize legacy easysnmp patterns to ezsnmp equivalents."""
    # 1. Fix exception imports
    for old_exc, new_exc in LEGACY_EXCEPTION_MAP.items():
        code = re.sub(
            rf"\bfrom\s+ezsnmp\.exceptions\s+import\s+([^#\n]*)\b{old_exc}\b",
            lambda m: m.group(0).replace(old_exc, new_exc),
            code,
        )
        code = re.sub(rf"\b{old_exc}\b", new_exc, code)

    # 2. Fix session methods
    code = re.sub(r"\.bulkwalk\(", ".bulk_walk(", code)
    code = re.sub(r"\.get_bulk\(", ".bulk_get(", code)

    # 3. Fix Result attributes
    code = re.sub(r"\.oid_index\b", ".index", code)
    code = re.sub(r"\.snmp_type\b", ".type", code)

    return code


def auto_fix_post_file(post_path: Path) -> Tuple[bool, int]:
    """Fix legacy API references across code blocks, preserving comparison tables and historical prose."""
    content = post_path.read_text(encoding="utf-8")
    original = content
    changes_count = 0

    lines = content.splitlines()
    new_lines = []
    in_migration_section = False
    in_table = False
    in_code_block = False

    for line in lines:
        stripped = line.strip()

        # Track migration comparison section
        if (
            "Migration Notes" in line
            or "Migration Guide" in line
            or "Modern API Differences" in line
        ):
            in_migration_section = True
        elif (
            in_migration_section
            and (line.startswith("===") or line.startswith("---"))
            and not line.startswith("   ")
        ):
            # Check if entering next major section
            if any(
                h in line for h in ["Useful Links", "Production Best", "Conclusion"]
            ):
                in_migration_section = False

        if (
            stripped.startswith(".. list-table::")
            or stripped.startswith("+---")
            or stripped.startswith("+===")
        ):
            in_table = True
        elif in_table and stripped == "" and not line.startswith(" "):
            in_table = False

        if re.match(r"^\s*\.\.\s+code-block::", line):
            in_code_block = True
        elif in_code_block and stripped and not line.startswith("   "):
            in_code_block = False

        # Only apply fixes to code blocks or outside comparison tables
        if not in_table:
            # Replace legacy method names in code
            if in_code_block:
                if ".bulkwalk(" in line:
                    line = line.replace(".bulkwalk(", ".bulk_walk(")
                    changes_count += 1
                if ".get_bulk(" in line:
                    line = line.replace(".get_bulk(", ".bulk_get(")
                    changes_count += 1
                line = re.sub(r"\.oid_index\b", ".index", line)
                line = re.sub(r"\.snmp_type\b", ".type", line)

            # Fix exception names only when not in a migration table comparing the two
            if not in_migration_section:
                for old_exc, new_exc in LEGACY_EXCEPTION_MAP.items():
                    if old_exc in line:
                        line = line.replace(old_exc, new_exc)
                        changes_count += 1

        new_lines.append(line)

    content = "\n".join(new_lines) + "\n"

    if content != original:
        post_path.write_text(content, encoding="utf-8")
        return True, changes_count
    return False, 0


# ---------------------------------------------------------------------------
# Example Scripts Extraction & Linking
# ---------------------------------------------------------------------------


def slugify_heading(heading: str) -> str:
    """Clean heading into a valid snake_case file identifier."""
    h = re.sub(r"^[0-9]+[\.\)]\s*", "", heading.strip())
    h = re.sub(r"^Practical Implementation:\s*", "", h, flags=re.IGNORECASE)
    h = re.sub(r"\([^)]*\)", "", h)
    s = re.sub(r"[^a-zA-Z0-9]+", "_", h).strip("_").lower()
    return s[:40].strip("_")


def derive_script_filename(
    code: str, heading: str, index: int, total_in_post: int
) -> str:
    """Derive an idiomatic filename for an example script from code or section heading."""
    base = ""
    try:
        tree = ast.parse(code)
        funcs = [
            n.name
            for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not n.name.startswith("_")
        ]
        classes = [
            n.name
            for n in ast.walk(tree)
            if isinstance(n, ast.ClassDef) and not n.name.startswith("_")
        ]
        main_calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                        main_calls.append(sub.func.id)

        called_in_main = [
            f for f in funcs if f in main_calls and f not in ("main", "run", "test")
        ]
        meaningful_funcs = [
            f
            for f in funcs
            if f
            not in (
                "main",
                "run",
                "test",
                "extract_peer_ip",
                "parse_numeric",
                "parse_hex_or_bytes",
            )
        ]

        if called_in_main:
            base = called_in_main[0]
        elif meaningful_funcs:
            base = meaningful_funcs[-1]
        elif funcs:
            base = funcs[-1]
        elif classes:
            base = slugify_heading(classes[0])
    except Exception:
        pass

    if not base or len(base) < 3:
        base = slugify_heading(heading) if heading else f"example_{index}"

    if not base or len(base) < 2:
        base = f"example_{index}"

    if total_in_post > 1:
        return f"{index:02d}_{base}.py"
    else:
        return f"{base}.py"


def extract_script_blocks_from_post(post_path: Path) -> List[Tuple[int, str, str]]:
    """Extract eligible Python example scripts with line numbers and section headings."""
    content = post_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    blocks: List[Tuple[int, str, str]] = []

    for i, line in enumerate(lines):
        m = re.match(r"^([ \t]*)\.\.\s+code-block::\s*python", line)
        if m:
            indent = len(m.group(1))
            block_lines: List[str] = []
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            while j < len(lines):
                l = lines[j]
                if not l.strip():
                    block_lines.append("")
                    j += 1
                    continue
                curr_indent = len(l) - len(l.lstrip())
                if curr_indent > indent:
                    block_lines.append(l)
                    j += 1
                else:
                    break
            code = textwrap.dedent("\n".join(block_lines)).strip()
            num_code_lines = len([l for l in block_lines if l.strip()])

            # Eligible example scripts: >= 4 code lines, contains keywords
            if num_code_lines >= 4 and any(
                kw in code
                for kw in ["import ", "def ", "class ", "Session(", "PurpleAir"]
            ):
                # Look backwards for preceding section heading
                heading = ""
                for k in range(i - 1, -1, -1):
                    l_k = lines[k].strip()
                    if (
                        not l_k
                        or l_k.startswith("..")
                        or l_k.startswith(":")
                        or l_k.startswith("*")
                    ):
                        continue
                    if (
                        k + 1 < len(lines)
                        and len(lines[k + 1].strip()) >= 3
                        and set(lines[k + 1].strip()).issubset({"=", "-", "~", "^"})
                    ):
                        heading = l_k
                        break
                    if (
                        k > 0
                        and len(lines[k - 1].strip()) >= 3
                        and set(lines[k - 1].strip()).issubset({"=", "-", "~", "^"})
                    ):
                        heading = l_k
                        break
                blocks.append((i, code, heading))

    return blocks


def save_example_scripts(
    post_path: Path,
    output_base: Optional[Path] = None,
    update_links: bool = True,
) -> List[Path]:
    """Save example scripts from a post into example_scripts/<slug>/ and link them in the post."""
    if output_base is None:
        output_base = EXAMPLE_SCRIPTS_DIR

    slug = post_path.stem
    content = post_path.read_text(encoding="utf-8")
    title_m = re.search(
        r"^[=\-~#`^]{4,}\n([^\n]+)\n[=\-~#`^]{4,}", content, re.MULTILINE
    )
    title = title_m.group(1).strip() if title_m else slug

    blocks = extract_script_blocks_from_post(post_path)
    if not blocks:
        return []

    target_dir = output_base / slug
    target_dir.mkdir(parents=True, exist_ok=True)

    saved_files: List[Path] = []
    block_link_map: Dict[int, str] = {}
    total = len(blocks)

    for idx, (orig_i, code, heading) in enumerate(blocks, start=1):
        filename = derive_script_filename(code, heading, idx, total)
        out_file = target_dir / filename

        header = f'#!/usr/bin/env python3\n"""Example script for: {title}\nSource: https://carlkidcrypto.github.io/blog/{slug}.html\n"""\n\n'
        full_script = header + code.strip() + "\n"
        out_file.write_text(full_script, encoding="utf-8")
        out_file.chmod(0o755)
        saved_files.append(out_file)

        raw_url = f"{GITHUB_RAW_BASE}/{slug}/{filename}"
        block_link_map[orig_i] = f"📥 `Download this script: {filename} <{raw_url}>`_"

    # Clean up stale scripts in target_dir
    for old_file in target_dir.glob("*.py"):
        if old_file not in saved_files:
            old_file.unlink(missing_ok=True)

    if update_links:
        lines = content.splitlines()
        i = 0
        new_lines: List[str] = []
        while i < len(lines):
            line = lines[i]
            m = re.match(r"^([ \t]*)\.\.\s+code-block::\s*python", line)
            if m and i in block_link_map:
                orig_i = i
                indent = len(m.group(1))
                new_lines.append(line)
                i += 1
                while i < len(lines) and not lines[i].strip():
                    new_lines.append(lines[i])
                    i += 1
                while i < len(lines):
                    l = lines[i]
                    if not l.strip():
                        new_lines.append(l)
                        i += 1
                        continue
                    curr_indent = len(l) - len(l.lstrip())
                    if curr_indent > indent:
                        new_lines.append(l)
                        i += 1
                    else:
                        break
                while new_lines and not new_lines[-1].strip():
                    new_lines.pop()

                k = i
                while k < len(lines) and not lines[k].strip():
                    k += 1
                has_link = k < len(lines) and (
                    "Download this script:" in lines[k] or "example_scripts" in lines[k]
                )

                new_lines.append("")
                new_lines.append(block_link_map[orig_i])
                new_lines.append("")
                if has_link:
                    i = k + 1
                    while i < len(lines) and not lines[i].strip():
                        i += 1
                continue
            new_lines.append(line)
            i += 1

        new_content = "\n".join(new_lines) + "\n"
        if new_content != content:
            post_path.write_text(new_content, encoding="utf-8")

    return saved_files


def save_all_example_scripts(
    blog_dir: Optional[Path] = None,
    output_base: Optional[Path] = None,
    update_links: bool = True,
) -> Dict[str, List[Path]]:
    """Process all blog posts in blog_dir and save their example scripts."""
    if blog_dir is None:
        blog_dir = BLOG_DIR
    results: Dict[str, List[Path]] = {}
    for post in sorted(blog_dir.glob("*.rst")):
        if post.name == "index.rst":
            continue
        saved = save_example_scripts(
            post, output_base=output_base, update_links=update_links
        )
        if saved:
            results[post.stem] = saved
    return results


# ---------------------------------------------------------------------------
# Runner & CLI
# ---------------------------------------------------------------------------


def validate_post(
    post_path: Path,
    run_tests: bool = True,
    save_scripts: bool = True,
) -> List[ValidationIssue]:
    blocks = extract_code_blocks(post_path)
    issues: List[ValidationIssue] = []
    article_scope: Dict[str, Any] = {
        "__name__": "__main__",
        "__file__": str(post_path),
    }

    for block in blocks:
        if block.language == "python":
            syntax_issues = validate_python_syntax_and_api(block)
            issues.extend(syntax_issues)
            if not syntax_issues and run_tests:
                test_issues = execute_test_harness(block, article_scope)
                issues.extend(test_issues)
        elif block.language in ("bash", "sh"):
            issues.extend(validate_bash_syntax(block))
        elif block.language == "yaml":
            issues.extend(validate_yaml_syntax(block))

    if save_scripts:
        save_example_scripts(post_path, update_links=True)

    return issues


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Test and validate all example code in blog posts."
    )
    parser.add_argument(
        "--post", type=str, help="Specific post file or slug to validate"
    )
    parser.add_argument(
        "--all", action="store_true", help="Validate all blog posts in source/blog/"
    )
    parser.add_argument(
        "--fix", action="store_true", help="Automatically fix legacy API patterns"
    )
    parser.add_argument(
        "--skip-runtime", action="store_true", help="Skip runtime test execution"
    )
    parser.add_argument(
        "--save-examples",
        action="store_true",
        default=True,
        help="Save example scripts to example_scripts/<slug>/ and link in post",
    )
    parser.add_argument(
        "--no-save-examples",
        action="store_false",
        dest="save_examples",
        help="Skip saving example scripts",
    )
    args = parser.parse_args(argv)

    if not BLOG_DIR.exists():
        print(f"Error: Blog directory not found at {BLOG_DIR}")
        return 1

    posts: List[Path] = []
    if args.post:
        target = Path(args.post)
        if not target.exists():
            target = BLOG_DIR / f"{args.post}.rst"
        if not target.exists():
            print(f"Error: Post not found: {args.post}")
            return 1
        posts = [target]
    else:
        posts = [
            f
            for f in sorted(BLOG_DIR.glob("*"))
            if f.name != "index.rst" and f.suffix in (".rst", ".md")
        ]

    if args.fix:
        print(f"🔧 Scanning and auto-fixing code in {len(posts)} blog post(s)...")
        total_fixed = 0
        for post in posts:
            changed, count = auto_fix_post_file(post)
            if changed:
                print(f"  Fixed {count} API issue(s) in {post.relative_to(REPO_ROOT)}")
                total_fixed += 1
        print(f"Auto-fix completed. Updated {total_fixed} file(s).\n")

    print(f"🔍 Validating code blocks in {len(posts)} blog post(s)...")
    total_blocks = 0
    total_issues: List[ValidationIssue] = []

    for post in posts:
        blocks = extract_code_blocks(post)
        total_blocks += len(blocks)
        issues = validate_post(
            post,
            run_tests=not args.skip_runtime,
            save_scripts=args.save_examples,
        )
        if issues:
            total_issues.extend(issues)
            print(f"  ❌ {post.name}: {len(issues)} issue(s)")
            for iss in issues:
                print(f"     [Line {iss.line_number}] {iss.severity}: {iss.message}")
                if iss.code_snippet:
                    print(f"       Code: {iss.code_snippet}")
        else:
            print(f"  ✅ {post.name} ({len(blocks)} code blocks verified)")

    print("\n" + "=" * 60)
    if total_issues:
        print(
            f"CODE VALIDATION FAILED: {len(total_issues)} issue(s) found across {len(posts)} post(s)."
        )
        print("Run with --fix to automatically correct known legacy API patterns.")
        print("=" * 60)
        return 1

    print(
        f"SUCCESS: All {total_blocks} code blocks across {len(posts)} post(s) passed validation!"
    )
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
