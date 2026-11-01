"""Fetch Elma (Iceland) day-ahead results via the site's Next.js server action 'FetchBatchData'
(the same call the 'Download Excel' button makes). Action id taken from
https://elma.is/_next/static/chunks/app/%5Blocale%5D/market-data/day-ahead/page-5183696b8bff9b88.js"""
import json, re, sys, datetime as dt, urllib.request
import pandas as pd

URL = "https://elma.is/en/market-data/day-ahead/"
ACTION = "605bda61875dd9d67513049cfcd55f0a8fd4b8a582"
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120",
       "Next-Action": ACTION, "Accept": "text/x-component",
       "Content-Type": "text/plain;charset=UTF-8"}

def fetch(a, b):
    req = urllib.request.Request(URL, data=json.dumps([a, b]).encode(), headers=HDR, method="POST")
    txt = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
    for line in txt.splitlines():
        m = re.match(r"^1:(\{.*)$", line)
        if m:
            return json.loads(m.group(1))
    raise RuntimeError(txt[:500])

rows, keys_seen = [], None
start, end = dt.date(2025, 3, 12), dt.date.today() + dt.timedelta(days=1)
d = start
while d <= end:
    e = min(d + dt.timedelta(days=30), end)
    res = fetch(d.isoformat(), e.isoformat())
    data = res.get("data") or []
    if data and keys_seen is None:
        keys_seen = data[0].keys(); print("day keys:", list(keys_seen),
              "price keys:", list(data[0]["priceMetrics"].keys()),
              "vol keys:", list(data[0]["volumeMetrics"].keys()))
    for day in data:
        vol = {v["time"]: v["volume"] for v in day["volumeMetrics"]["volumePerHour"]}
        for p in day["priceMetrics"]["pricePerHour"]:
            rows.append({"delivery_date": day["date"], "time_utc": p["time"],
                         "price_isk_mwh": p["price"], "volume_mwh": vol.get(p["time"])})
    print(d, e, len(data), "days", "" if "data" in res else res)
    d = e + dt.timedelta(days=1)

df = pd.DataFrame(rows).drop_duplicates("time_utc").sort_values("time_utc")
df.to_csv(sys.argv[1], index=False)
print(len(df), "rows", df.time_utc.min(), df.time_utc.max())
