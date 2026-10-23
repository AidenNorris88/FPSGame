#!/usr/bin/env python3
"""Extract printable ASCII strings from .uasset files and filter by keywords."""

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

FILES = [
    PROJECT_ROOT / "Content" / "AI" / "BP_EnemyGuard.uasset",
    PROJECT_ROOT / "Content" / "Blueprints" / "BP_Player.uasset",
    PROJECT_ROOT / "Content" / "Blueprints" / "BP_Projectile.uasset",
    PROJECT_ROOT / "Content" / "Blueprints" / "Bp_HealthComponent.uasset",
    PROJECT_ROOT / "Content" / "AI" / "BT_Enemy_Base.uasset",
]

KEYWORDS = [
    "spawn",
    "projectile",
    "player",
    "fire",
    "attack",
    "damage",
    "health",
    "collision",
    "class",
    "mesh",
    "overlap",
    "hit",
]

MIN_LEN = 4
MAX_STRINGS = 200
SPAWN_WINDOW = 512  # bytes around K2_SpawnActor to search for class names


def extract_ascii_strings(data: bytes, min_len: int = MIN_LEN) -> list[str]:
    pattern = re.compile(rb"[\x20-\x7e]{%d,}" % min_len)
    seen: set[str] = set()
    out: list[str] = []
    for m in pattern.finditer(data):
        s = m.group().decode("ascii")
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def matches_keyword(s: str) -> bool:
    lower = s.lower()
    return any(kw in lower for kw in KEYWORDS)


def find_spawn_class_proximity(data: bytes) -> list[dict]:
    """Find BP_Player / spawn-related names near K2_SpawnActor in raw bytes."""
    markers = [
        b"K2_SpawnActor",
        b"SpawnActor",
        b"BeginDeferredActorSpawnFromClass",
        b"FinishSpawningActor",
    ]
    results: list[dict] = []
    for marker in markers:
        start = 0
        while True:
            idx = data.find(marker, start)
            if idx == -1:
                break
            lo = max(0, idx - SPAWN_WINDOW)
            hi = min(len(data), idx + len(marker) + SPAWN_WINDOW)
            window = data[lo:hi]
            strings = extract_ascii_strings(window, min_len=3)
            interesting = [
                s
                for s in strings
                if "BP_Player" in s
                or "Player" in s
                or "Spawn" in s
                or "Class" in s
                or "Projectile" in s
            ]
            results.append(
                {
                    "marker": marker.decode("ascii"),
                    "offset": idx,
                    "nearby_strings": interesting[:30],
                }
            )
            start = idx + 1
    return results


def process_file(path: Path) -> None:
    rel = path.relative_to(PROJECT_ROOT)
    print("=" * 72)
    print(f"FILE: {rel}")
    print("=" * 72)

    if not path.is_file():
        print("  [MISSING]")
        return

    data = path.read_bytes()
    all_strings = extract_ascii_strings(data)
    filtered = [s for s in all_strings if matches_keyword(s)]
    filtered = filtered[:MAX_STRINGS]

    print(f"  Total ASCII strings (len>={MIN_LEN}): {len(all_strings)}")
    print(f"  Filtered (keywords): {len(filtered)} (showing up to {MAX_STRINGS})")
    print()
    for i, s in enumerate(filtered, 1):
        print(f"  {i:4d}. {s}")

    spawn_hits = find_spawn_class_proximity(data)
    bp_player_near_spawn = [
        h
        for h in spawn_hits
        if any("BP_Player" in s for s in h["nearby_strings"])
    ]
    print()
    print("  --- Spawn API proximity (BP_Player / spawn class) ---")
    if not spawn_hits:
        print("  No K2_SpawnActor / SpawnActor markers found in this file.")
    else:
        for h in spawn_hits:
            has_bp = any("BP_Player" in s for s in h["nearby_strings"])
            flag = " *** BP_Player nearby ***" if has_bp else ""
            print(f"  @ offset {h['offset']}: {h['marker']}{flag}")
            for s in h["nearby_strings"][:15]:
                print(f"      -> {s}")
    if bp_player_near_spawn:
        print()
        print("  CONCLUSION: BP_Player appears near spawn-related API in this file.")
    elif any("K2_SpawnActor" in h["marker"] for h in spawn_hits):
        print()
        print("  CONCLUSION: K2_SpawnActor found but BP_Player not in nearby window.")
    print()


def main() -> int:
    for path in FILES:
        process_file(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
