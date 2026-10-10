import json, sys
sys.argv = ["x"]
exec(open("scripts/hk_results.py").read().split("SCHEDULE_Q =")[0])
out = {}
for name, v in [("n4000", {"lastNDraw": 4000, "drawType": "All"}), ("range", {"startDate": "20250101", "endDate": "20250331", "drawType": "All"}),
                ("range2", {"startDate": "2025-01-01", "endDate": "2025-03-31", "drawType": "All"}), ("nodt", {"lastNDraw": 3})]:
    try:
        d = draws(v); out[name] = {"n": len(d), "first": d[0] if d else None, "last": d[-1] if d else None}
        if name == "n4000": json.dump([c for c in (clean(x) for x in d) if c], open("history.json", "w"), ensure_ascii=False)
    except Exception as e: out[name] = str(e)[:300]
json.dump(out, open("probe.json", "w"), ensure_ascii=False, indent=1)
print({k: (v if isinstance(v, str) else v["n"]) for k, v in out.items()})
