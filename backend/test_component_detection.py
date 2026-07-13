"""
Component detection validation script for current telemetry logic.

This script runs HardwareMonitor.get_system_health() and verifies whether
key components are detected and populated by the existing implementation.

Usage:
  python test_component_detection.py
  python test_component_detection.py --issue "screen flickering and no display"
  python test_component_detection.py --json
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Tuple

from pc_diagnostic.hardware_monitor import HardwareMonitor


def _has_error(payload: Any) -> bool:
    if isinstance(payload, dict):
        if payload.get("error"):
            return True
        if isinstance(payload.get("errors"), list) and len(payload.get("errors")) > 0:
            return True
    return False


def _list_has_items(payload: Any) -> bool:
    return isinstance(payload, list) and len(payload) > 0


def _dict_has_signal(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    if _has_error(payload):
        return False
    return len(payload.keys()) > 0


def _run_checks(telemetry: Dict[str, Any]) -> List[Tuple[str, bool, str]]:
    checks: List[Tuple[str, bool, str]] = []

    # Core telemetry blocks
    checks.append((
        "system_info",
        _dict_has_signal(telemetry.get("system_info")),
        "Basic OS/platform details",
    ))
    checks.append((
        "cpu",
        _dict_has_signal(telemetry.get("cpu")),
        "CPU usage and core details",
    ))
    checks.append((
        "memory",
        _dict_has_signal(telemetry.get("memory")),
        "Memory totals and usage",
    ))
    checks.append((
        "disk",
        _list_has_items(telemetry.get("disk")),
        "Disk partitions and usage",
    ))
    checks.append((
        "network",
        _dict_has_signal(telemetry.get("network")),
        "Network I/O counters",
    ))
    checks.append((
        "processes",
        _list_has_items(telemetry.get("processes")),
        "Top process snapshot",
    ))

    issue_specific = telemetry.get("issue_specific", {})
    display = issue_specific.get("display", {}) if isinstance(issue_specific, dict) else {}

    # Display path (important for flicker/no-display problems)
    if isinstance(display, dict):
        checks.append((
            "display.monitors",
            _list_has_items(display.get("monitors")),
            "Monitor devices detected",
        ))
        checks.append((
            "display.graphics_cards",
            _list_has_items(display.get("graphics_cards")),
            "GPU controllers detected (integrated/dedicated)",
        ))
        checks.append((
            "display.display_drivers",
            _list_has_items(display.get("display_drivers")),
            "Display drivers detected (currently may be empty in this logic)",
        ))

    return checks


def _print_human_report(telemetry: Dict[str, Any], checks: List[Tuple[str, bool, str]]) -> int:
    print("=" * 72)
    print("Component Detection Validation (Current Logic)")
    print("=" * 72)
    print(f"Issue description: {telemetry.get('user_description')}")
    print(f"Issue types detected: {telemetry.get('issue_types_detected')}")
    print("-" * 72)

    passed = 0
    failed = 0

    for key, ok, note in checks:
        status = "OK" if ok else "MISSING"
        print(f"[{status:7}] {key:24} - {note}")
        if ok:
            passed += 1
        else:
            failed += 1

    print("-" * 72)
    print(f"Passed: {passed}")
    print(f"Missing: {failed}")

    issue_specific = telemetry.get("issue_specific", {})
    display = issue_specific.get("display", {}) if isinstance(issue_specific, dict) else {}

    if isinstance(display, dict) and isinstance(display.get("errors"), list) and display["errors"]:
        print("\nDisplay detection errors:")
        for err in display["errors"]:
            print(f"- {err}")

    if failed > 0:
        print("\nResult: Some components were not detected by current logic.")
        return 1

    print("\nResult: All checked components were detected.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate component detection from current telemetry logic.")
    parser.add_argument(
        "--issue",
        default="screen flickering and display driver issue",
        help="Issue text used to trigger issue-specific telemetry collection.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full telemetry JSON in addition to summary checks.",
    )
    args = parser.parse_args()

    monitor = HardwareMonitor()
    telemetry = monitor.get_system_health(args.issue)
    checks = _run_checks(telemetry)

    exit_code = _print_human_report(telemetry, checks)

    if args.json:
        print("\nFull telemetry payload:")
        print(json.dumps(telemetry, indent=2, default=str, ensure_ascii=False))

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
