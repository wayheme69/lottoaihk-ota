# Sonde : vérifie l'accès à l'API officielle HKJC depuis GitHub Actions et sauvegarde la réponse brute
import json, urllib.request, sys, datetime, gzip
Q = open("scripts/marksix.graphql").read()
def gql(variables):
    body = json.dumps({"operationName": "marksixResult", "variables": variables, "query": Q}).encode()
    req = urllib.request.Request("https://info.cld.hkjc.com/graphql/base/", data=body, headers={
        "Content-Type": "application/json", "Origin": "https://bet.hkjc.com", "Referer": "https://bet.hkjc.com/",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"})
    raw = urllib.request.urlopen(req, timeout=60).read()
    if raw[:2] == b"\x1f\x8b": raw = gzip.decompress(raw)
    return json.loads(raw)
out = {"last": gql({"lastNDraw": 5, "drawType": "All"})}
today = datetime.date.today()
out["future"] = gql({"startDate": today.strftime("%Y%m%d"), "endDate": (today + datetime.timedelta(days=21)).strftime("%Y%m%d"), "drawType": "All"})
json.dump(out, open("probe.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False)[:3000])
