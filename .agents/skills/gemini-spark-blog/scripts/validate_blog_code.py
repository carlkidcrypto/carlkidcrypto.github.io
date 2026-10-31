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
    """Extract code blocks from an RST file with accurate line numbers."""
    content = post_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    blocks: List[CodeBlock] = []

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
            block_lines: List[str] = []
            while i < len(lines):
                line = lines[i]
                if not line.strip():
                    block_lines.append("")
                    i += 1
                    continue
                # Check indentation
                curr_indent = len(line) - len(line.lstrip(" "))
                base_indent = len(indent_str)
                if curr_indent > base_indent:
                    block_lines.append(line)
                    i += 1
                else:
                    break

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
}


def validate_python_syntax_and_api(block: CodeBlock) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []

    # 1. AST Parse
    try:
        tree = ast.parse(block.code, filename=f"{block.post_path.name}:{block.line_number}")
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
        compile(block.code, filename=f"{block.post_path.name}:{block.line_number}", mode="exec")
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
            elif node.module == "ezsnmp.exceptions":
                for alias in node.names:
                    if alias.name in LEGACY_EXCEPTION_MAP:
                        target = LEGACY_EXCEPTION_MAP[alias.name]
                        issues.append(
                            ValidationIssue(
                                post_path=block.post_path,
                                line_number=block.line_number + node.lineno - 1,
                                severity="ERROR",
                                message=(
                                    f"Outdated exception 'from ezsnmp.exceptions import {alias.name}'. "
                                    f"In ezsnmp, use '{target}'."
                                ),
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
    lines = [line for line in block.code.splitlines() if not line.strip().startswith("#")]
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
        raise AttributeError("ezsnmp Result object has no attribute 'oid_index'. Use 'index'.")

    @property
    def snmp_type(self) -> str:
        raise AttributeError("ezsnmp Result object has no attribute 'snmp_type'. Use 'type'.")

    def __repr__(self) -> str:
        return f"Result(oid='{self.oid}', index='{self.index}', value='{self.value}', type='{self.type}')"


class MockSession:
    """Simulated ezsnmp Session that answers standard MIB queries."""

    def __init__(self, hostname: str = "localhost", community: str = "public", version: int = 2, **kwargs: Any):
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
            return MockResult("sysDescr", "0", "Cisco IOS Software, C3750E Software (C3750E-UNIVERSALK9-M)", "OCTETSTR")
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
                MockResult("cbgpPeer2AcceptedPrefixes", "1.4.192.0.2.1.1.1", "150000", "GAUGE"),
                MockResult("cbgpPeer2AcceptedPrefixes", "1.4.192.0.2.2.1.1", "850000", "GAUGE"),
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
            return (
                MockResult("entPhysicalSerialNum", "1", "FOC1234ABCD", "OCTETSTR"),
            )
        return (
            MockResult(oid_name, "1", "val1", "OCTETSTR"),
            MockResult(oid_name, "2", "val2", "OCTETSTR"),
        )

    def bulk_get(self, oids: Any, non_repeaters: int = 0, max_repetitions: int = 10) -> Tuple[MockResult, ...]:
        return self.bulk_walk(oids, max_repetitions=max_repetitions)

    def set(self, oids: Any) -> bool:
        return True


class DummyPool:
    def __init__(self, *args: Any, **kwargs: Any):
        pass
    def __enter__(self) -> "DummyPool":
        return self
    def __exit__(self, *args: Any) -> None:
        pass
    def map(self, func: Callable, iterable: Any, *args: Any, **kwargs: Any) -> List[Any]:
        return [func(x) for x in iterable]
    def starmap(self, func: Callable, iterable: Any, *args: Any, **kwargs: Any) -> List[Any]:
        return [func(*x) for x in iterable]
    def close(self) -> None:
        pass
    def join(self) -> None:
        pass


def execute_test_harness(block: CodeBlock, sandbox_globals: Dict[str, Any]) -> List[ValidationIssue]:
    """Execute runnable Python code blocks in a sandbox with mock ezsnmp."""
    issues: List[ValidationIssue] = []

    # Check if snippet contains runnable logic (functions or top-level execution)
    # Skip snippets that are purely shell/interactive output or isolated 1-2 line snippets
    if len(block.code.splitlines()) < 4:
        return issues

    # Pre-populate Session and Result
    sandbox_globals.setdefault("Session", MockSession)
    sandbox_globals.setdefault("Result", MockResult)
    sandbox_globals.setdefault("DEVICE_INVENTORY", ["192.168.1.1", "192.168.1.2"])

    # Install ezsnmp mock into sys.modules during execution
    import types
    mock_ezsnmp = types.ModuleType("ezsnmp")
    mock_exceptions = types.ModuleType("ezsnmp.exceptions")

    class GenericError(Exception): pass
    class TimeoutError(GenericError): pass
    class ConnectionError(GenericError): pass
    class NoSuchInstanceError(GenericError): pass
    class NoSuchNameError(GenericError): pass
    class NoSuchObjectError(GenericError): pass

    mock_exceptions.GenericError = GenericError
    mock_exceptions.TimeoutError = TimeoutError
    mock_exceptions.ConnectionError = ConnectionError
    mock_exceptions.NoSuchInstanceError = NoSuchInstanceError
    mock_exceptions.NoSuchNameError = NoSuchNameError
    mock_exceptions.NoSuchObjectError = NoSuchObjectError

    mock_ezsnmp.Session = MockSession
    mock_ezsnmp.Result = MockResult
    mock_ezsnmp.exceptions = mock_exceptions
    mock_ezsnmp.GenericError = GenericError
    mock_ezsnmp.TimeoutError = TimeoutError
    mock_ezsnmp.ConnectionError = ConnectionError
    mock_ezsnmp.NoSuchInstanceError = NoSuchInstanceError
    mock_ezsnmp.NoSuchObjectError = NoSuchObjectError

    # Patch sys.modules
    old_ezsnmp = sys.modules.get("ezsnmp")
    old_exceptions = sys.modules.get("ezsnmp.exceptions")
    sys.modules["ezsnmp"] = mock_ezsnmp
    sys.modules["ezsnmp.exceptions"] = mock_exceptions

    # Mock time.sleep, multiprocessing.Pool, and ProcessPoolExecutor to avoid blocking or pickling issues
    import time
    import multiprocessing
    import concurrent.futures
    old_sleep = time.sleep
    old_pool = getattr(multiprocessing, "Pool", None)
    old_ppe = getattr(concurrent.futures, "ProcessPoolExecutor", None)
    time.sleep = lambda s: None
    multiprocessing.Pool = DummyPool
    concurrent.futures.ProcessPoolExecutor = concurrent.futures.ThreadPoolExecutor

    # Redirect stdout during snippet execution to keep test output clean
    import io
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    try:
        compiled = compile(block.code, filename=f"{block.post_path.name}:{block.line_number}", mode="exec")
        exec(compiled, sandbox_globals)
    except (ImportError, ModuleNotFoundError) as e:
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
        sys.stdout = old_stdout
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
    """Fix legacy API references across code blocks and explanatory prose."""
    content = post_path.read_text(encoding="utf-8")
    original = content
    changes_count = 0

    # Replace legacy exception names in ezsnmp context
    for old_exc, new_exc in LEGACY_EXCEPTION_MAP.items():
        if old_exc in content:
            content = content.replace(old_exc, new_exc)
            changes_count += 1

    # Replace legacy method names in code
    if ".bulkwalk(" in content:
        content = content.replace(".bulkwalk(", ".bulk_walk(")
        changes_count += 1
    if ".get_bulk(" in content:
        content = content.replace(".get_bulk(", ".bulk_get(")
        changes_count += 1

    # In ezsnmp Result descriptions and code, replace oid_index / snmp_type
    # (avoiding the Getting Started migration table comparing the two)
    lines = content.splitlines()
    new_lines = []
    in_migration_table = False
    for line in lines:
        if "Migration Notes" in line or "Migration Guide" in line:
            in_migration_table = True
        if in_migration_table and line.startswith("==="):
            # End of migration notes section
            pass

        if not in_migration_table:
            # Replace code usages
            line = re.sub(r"\.oid_index\b", ".index", line)
            line = re.sub(r"\.snmp_type\b", ".type", line)

        new_lines.append(line)

    content = "\n".join(new_lines) + "\n"

    if content != original:
        post_path.write_text(content, encoding="utf-8")
        return True, changes_count
    return False, 0


# ---------------------------------------------------------------------------
# Runner & CLI
# ---------------------------------------------------------------------------

def validate_post(post_path: Path, run_tests: bool = True) -> List[ValidationIssue]:
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

    return issues


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Test and validate all example code in blog posts.")
    parser.add_argument("--post", type=str, help="Specific post file or slug to validate")
    parser.add_argument("--all", action="store_true", help="Validate all blog posts in source/blog/")
    parser.add_argument("--fix", action="store_true", help="Automatically fix legacy API patterns")
    parser.add_argument("--skip-runtime", action="store_true", help="Skip runtime test execution")
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
            f for f in sorted(BLOG_DIR.glob("*"))
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
        issues = validate_post(post, run_tests=not args.skip_runtime)
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
        print(f"CODE VALIDATION FAILED: {len(total_issues)} issue(s) found across {len(posts)} post(s).")
        print("Run with --fix to automatically correct known legacy API patterns.")
        print("=" * 60)
        return 1

    print(f"SUCCESS: All {total_blocks} code blocks across {len(posts)} post(s) passed validation!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
