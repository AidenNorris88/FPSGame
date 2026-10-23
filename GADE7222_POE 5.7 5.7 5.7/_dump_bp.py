import os, re

files = [
    r"Content\AI\BP_EnemyGuard.uasset",
    r"Content\AI\BT_Enemy_Base.uasset",
    r"Content\AI\BB_Enemy_Base.uasset",
    r"Content\Blueprints\BP_Player.uasset",
    r"Content\Blueprints\BP_Projectile.uasset",
    r"Content\Blueprints\BP_EnemySpawner.uasset",
    r"Content\Blueprints\Bp_HealthComponent.uasset",
    r"Saved\Autosaves\Game\AI\BP_EnemyGuard_Auto1.uasset",
    r"Saved\Autosaves\Game\Blueprints\BP_Player_Auto1.uasset",
]
pat = re.compile(rb"[\x20-\x7e]{6,}")
keys = (
    "spawn", "projectile", "player", "enemy", "fire", "attack", "damage",
    "health", "collision", "class", "mesh", "character", "muzzle", "weapon",
    "trace", "ignore", "pawn", "shoot", "bullet", "ai controller", "possess",
    "k2_spawn", "beginplay", "event", "montage", "anim", "capsule",
)
for f in files:
    print("=" * 80)
    print(f)
    if not os.path.exists(f):
        print("MISSING")
        continue
    data = open(f, "rb").read()
    strings = [s.decode("ascii", "ignore") for s in pat.findall(data)]
    seen = set()
    out = []
    for s in strings:
        if s in seen:
            continue
        seen.add(s)
        sl = s.lower()
        if any(k in sl for k in keys):
            out.append(s)
    print("size", len(data), "filtered", len(out), "total", len(strings))
    for s in out[:400]:
        print(s)
