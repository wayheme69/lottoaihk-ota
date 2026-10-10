#!/usr/bin/env python3
"""Robot LOTTO AI HK : résultats officiels du Mark Six (六合彩) depuis l'API publique du Hong Kong Jockey Club.
- 30 derniers tirages (numéros, 特別號碼, lots des 7 rangs par mise de HK$10, nombre de mises gagnantes)
- calendrier officiel des prochains tirages (dont 金多寶) + estimation du 頭獎 si publiée
Écrit hk_results.json UNIQUEMENT si tout est cohérent (sinon : sortie en erreur, l'ancien fichier reste).
Mode --history AAAA : exporte tous les tirages de l'année (vérification des statistiques)."""
import json, urllib.request, gzip, ssl, sys, datetime, csv
Q = open("scripts/marksix.graphql").read()
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
HKT = datetime.timezone(datetime.timedelta(hours=8))

def post(url, body, extra=None):
    h = {"Content-Type": "application/json", "Accept": "application/json", "Origin": "https://bet.hkjc.com",
         "Referer": "https://bet.hkjc.com/", "User-Agent": UA, **(extra or {})}
    raw = urllib.request.urlopen(urllib.request.Request(url, data=json.dumps(body).encode(), headers=h), timeout=60).read()
    if raw[:2] == b"\x1f\x8b": raw = gzip.decompress(raw)
    d = json.loads(raw)
    if d.get("errors"): raise RuntimeError(d["errors"])
    return d["data"]

def draws(variables):
    return post("https://info.cld.hkjc.com/graphql/base/", {"operationName": "marksixResult", "variables": variables, "query": Q})["lotteryDraws"]

def clean(x):
    r = x.get("drawResult") or {}
    nums, extra = r.get("drawnNo") or [], r.get("xDrawnNo")
    if x.get("status") != "Result" or len(nums) != 6 or extra is None: return None
    assert len(set(nums + [extra])) == 7 and all(1 <= n <= 49 for n in nums + [extra]), x["id"]
    pool = x.get("lotteryPool") or {}
    prizes = {str(p["type"]): p for p in pool.get("lotteryPrizes") or []}
    return {"draw": f"{x['year'][2:]}/{int(x['no']):03d}", "date": x["drawDate"][:10],
            "numbers": sorted(nums), "bonus": [extra],
            "snowball": bool(x.get("snowballCode")), "snowballName": x.get("snowballName_ch") or None,
            "unitBet": int(pool.get("unitBet") or 10),
            # dividende par mise de HK$10 (None = rang sans gagnant) ; mises gagnantes (l'API compte en dixièmes)
            "payouts": {k: (float(p["dividend"]) if float(p["winningUnit"] or 0) > 0 else None) for k, p in prizes.items()},
            "winners": {k: round(float(p["winningUnit"] or 0) / 10, 1) for k, p in prizes.items()},
            "investment": int(float(pool.get("totalInvestment") or 0))}

SCHEDULE_Q = """query MarksixFixtures($path: String!, $lang: String!) { item(path: $path, language: $lang) { years: children { year: name
 months: children { key: name dates: field(name: "NormalDrawDates") { ... on MultilistField { date: targetItems { value: name } } }
 snowballs: field(name: "SnowballDrawDates") { ... on MultilistField { date: targetItems { value: name } } } } } } }"""

def schedule():
    d = post("https://consvc.hkjc.com/JCBW/api/graph", {"query": SCHEDULE_Q, "variables": {"path": "/sitecore/content/Sites/JCBW/NextDrawSchedule/Schedule", "lang": "zh-HK"}},
             {"sc_apikey": "{FF2309B7-E8BB-49B2-82A7-36AE0B48F171}"})
    out = {}
    for y in (d.get("item") or {}).get("years") or []:
        if not (y.get("year") or "").isdigit(): continue
        for m in y.get("months") or []:
            try: mm = int(m["key"])
            except Exception: continue
            for kind in ("dates", "snowballs"):
                for it in ((m.get(kind) or {}).get("date") or []):
                    v = (it.get("value") or "").strip()
                    if v.isdigit():
                        k = f"{y['year']}-{mm:02d}-{int(v):02d}"
                        out[k] = out.get(k, False) or kind == "snowballs"
    return dict(sorted(out.items()))

if len(sys.argv) > 2 and sys.argv[1] == "--history":
    rows = []
    for y in sys.argv[2:]:
        for (a, b) in [(f"{y}0101", f"{y}0630"), (f"{y}0701", f"{y}1231")]:
            rows += [c for c in (clean(x) for x in draws({"startDate": a, "endDate": b, "drawType": "All"})) if c]
    rows.sort(key=lambda r: r["date"])
    json.dump(rows, open("history.json", "w"), ensure_ascii=False)
    print("history", len(rows)); sys.exit(0)

res = [c for c in (clean(x) for x in draws({"lastNDraw": 30, "drawType": "All"})) if c]
res.sort(key=lambda r: r["date"], reverse=True)
assert len(res) >= 25, f"seulement {len(res)} tirages"
assert len({r["draw"] for r in res}) == len(res)
nxt = {}
try:
    sch = schedule()
    today = datetime.datetime.now(HKT).date().isoformat()
    fut = [(k, v) for k, v in sch.items() if k > res[0]["date"] and k >= today] or [(k, v) for k, v in sch.items() if k > res[0]["date"]]
    if fut: nxt = {"date": fut[0][0], "snowball": fut[0][1]}
    nxt["upcoming"] = [k for k, _ in fut[:12]]
except Exception as e:
    print("calendrier indisponible :", e)
try:
    up = [x for x in draws({"lastNDraw": 1, "drawType": "Next"}) if x]
    if up:
        p = up[0].get("lotteryPool") or {}
        nxt["estimatedPrize"] = int(float(p.get("estimatedPrize") or 0)) or None
        nxt["jackpot"] = int(float(p.get("jackpot") or 0)) or None
        nxt["drawNo"] = f"{up[0]['year'][2:]}/{int(up[0]['no']):03d}"
        if up[0].get("drawDate"): nxt.setdefault("date", up[0]["drawDate"][:10])
except Exception as e:
    print("prochain tirage (API) indisponible :", e)
json.dump({"marksix": res, "next": nxt, "updated": datetime.datetime.now(HKT).isoformat(timespec="minutes")},
          open("hk_results.json", "w"), ensure_ascii=False, indent=1)
print("ok", len(res), res[0]["draw"], res[0]["date"], nxt)
