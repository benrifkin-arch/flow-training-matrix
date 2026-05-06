#!/usr/bin/env python3
"""
build_dashboard.py
Fetches attendance data from all Typeform forms in the Flow Training Tracking
workspace and regenerates index.html with up-to-date participant data.
Required env var: TYPEFORM_TOKEN  (Typeform Personal Access Token)
"""
import json, os, re, sys, requests
from datetime import datetime, timezone

TYPEFORM_TOKEN = os.environ.get("TYPEFORM_TOKEN", "")
if not TYPEFORM_TOKEN:
    sys.exit("ERROR: TYPEFORM_TOKEN environment variable not set")

TRAININGS = [
    "Salesforce", "Tableau", "Quoting", "Success w/ Customers",
    "Pricing/RGAs", "Highspot 1", "Customer Care & BP", "AS Toilets",
    "DXV Product Overview", "AS Faucets & Kitchen", "AS Commercial 1",
    "AS Commercial 2", "AS Showering", "GROHE Faucets & Ceramics",
    "GROHE Showering", "GROHE Kitchen", "Display Management",
    "Loyalty Programs & Ansira", "Highspot 2", "LIXIL Pro",
    "Forecasting", "Concierge & Service", "Adding Value to Showroom",
    "FLOW Wrap Up",
    "In Person Training",
]

FORM_MAPPING = {
    "iCNBozco": {"training": "Salesforce",               "group": 1},
    "NT7Zg1vr": {"training": "Tableau",                  "group": 1},
    "SufacUmT": {"training": "Quoting",                  "group": 1},
    "t5avrImy": {"training": "Success w/ Customers",     "group": 1},
    "Nn3f31WT": {"training": "Pricing/RGAs",             "group": 1},
    "Myx2B8oe": {"training": "Highspot 1",               "group": 1},
    "VHAeAr9h": {"training": "Customer Care & BP",       "group": 1},
    "SeK5serH": {"training": "AS Toilets",               "group": 1},
    "FKMrX8yw": {"training": "DXV Product Overview",     "group": 1},
    "BVrIec0k": {"training": "AS Faucets & Kitchen",     "group": 1},
    "Fctkx22I": {"training": "AS Commercial 1",          "group": 1},
    "FuCgh6Ct": {"training": "AS Commercial 2",          "group": 1},
    "GXFHuHfI": {"training": "GROHE Showering",          "group": 1},
    "y9bfjWHB": {"training": "GROHE Faucets & Ceramics", "group": 1},
    "SzDEPMlT": {"training": "GROHE Kitchen",            "group": 1},
    "QwuEXi83": {"training": "Display Management",       "group": 1},
    "JC3SSubG": {"training": "Concierge & Service",      "group": 1},
    "LW0gk8zC": {"training": "Forecasting",              "group": 1},
    "gMAvzoOI": {"training": "LIXIL Pro",                "group": 1},
    "tGMZoIJK": {"training": "Highspot 2",               "group": 1},
    "K39z6Tfi": {"training": "Adding Value to Showroom", "group": 1},
    "AXB6gX5C": {"training": "Salesforce",               "group": 2},
    "YQ2HR43W": {"training": "Tableau",                  "group": 2},
    "K1GKMBWa": {"training": "Quoting",                  "group": 2},
    "fwTGsQbc": {"training": "Customer Care & BP",       "group": 2},
    "OHOz9gSO": {"training": "Pricing/RGAs",             "group": 2},
    "LjocCTQm": {"training": "Highspot 1",               "group": 2},
    "oOl3VGUn": {"training": "AS Faucets & Kitchen",     "group": 2},
    "ZJCKZanE": {"training": "AS Commercial 1",          "group": 2},
    "tmhIYwwI": {"training": "AS Commercial 2",          "group": 2},
    "hfg5g3bx": {"training": "AS Showering",             "group": 2},
    "QBuj7Z0B": {"training": "Loyalty Programs & Ansira","group": 2},
    "fcMuvrfw": {"training": "GROHE Showering",          "group": 2},
    "x2DR6sj4": {"training": "GROHE Faucets & Ceramics", "group": 2},
    "UTkhq2NE": {"training": "GROHE Kitchen",            "group": 2},
    "o767iMMc": {"training": "AS Toilets",               "group": 2},
    "ZUcnzhx1": {"training": "Forecasting",              "group": 2},
    "W8OuN0le": {"training": "Success w/ Customers",     "group": 2},
    "Ie0bENbr": {"training": "Concierge & Service",      "group": 2},
    "TG5Bs2hL": {"training": "LIXIL Pro",                "group": 2},
    "DuXp5OwS": {"training": "Loyalty Programs & Ansira","group": 2},
    "uGvCEqGH": {"training": "DXV Product Overview",     "group": 2},
    "NRBc4lkA": {"training": "Adding Value to Showroom", "group": 2},
    "bMNZDEy7": {"training": "Highspot 2",               "group": 2},
    "CoH24ULg": {"training": "Display Management",       "group": 2},
    "IyWdAb5U": {"training": "Quoting",                  "group": 0},
    "DXHSQBd7": {"training": "In Person Training",       "group": 0},
}

AGENCY_ALIASES = {
    "big rivers": "Big Rivers", "cathell naylor": "Cathell Naylor",
    "elmco associates": "Elmco Associates", "elmco stewart": "Elmco Stewart",
    "harry warren - florida": "Harry Warren - Florida",
    "harry warren florida": "Harry Warren - Florida",
    "harry warren fl": "Harry Warren - Florida",
    "harry warren - georgia": "Harry Warren - Georgia",
    "harry warren georgia": "Harry Warren - Georgia",
    "harry warren ga": "Harry Warren - Georgia",
    "mid america": "Mid America", "mmi": "MMI", "next luxury": "Next Luxury",
    "norpac": "NorPac", "pepco": "Pepco", "ranvier": "Ranvier",
    "rep source": "Rep Source", "rep south": "Rep South", "rkr": "RKR",
}

def tf_headers():
    return {"Authorization": f"Bearer {TYPEFORM_TOKEN}"}

def get_field_map(form_id):
    """Fetch form definition and return {field_id: title} mapping."""
    r = requests.get(f"https://api.typeform.com/forms/{form_id}",
                     headers=tf_headers(), timeout=30)
    if r.status_code != 200:
        return {}
    data = r.json()
    field_map = {}
    for field in data.get("fields", []):
        fid = field.get("id")
        title = field.get("title", "")
        if fid:
            field_map[fid] = title
        # Also handle fields inside groups
        for sub in field.get("properties", {}).get("fields", []):
            sid = sub.get("id")
            if sid:
                field_map[sid] = sub.get("title", "")
    return field_map

def get_form_responses(form_id):
    url = f"https://api.typeform.com/forms/{form_id}/responses"
    items = []
    before = None
    while True:
        params = {"page_size": 200, "completed": "true"}
        if before:
            params["before"] = before
        r = requests.get(url, headers=tf_headers(), params=params, timeout=30)
        if r.status_code != 200:
            print(f"  ⚠ Error {r.status_code} fetching {form_id}")
            break
        data = r.json()
        batch = data.get("items", [])
        items.extend(batch)
        if len(batch) < 200:
            break
        before = batch[-1]["token"]
    return items

def extract_name_agency(response, field_map):
    name = agency = None
    for ans in response.get("answers", []):
        field_id = ans.get("field", {}).get("id", "")
        title = field_map.get(field_id, "").lower()
        atype = ans.get("type", "")
        # Check agency FIRST — title like "What is the name of your agency?" also contains "name"
        if "agency" in title or "rep " in title or "company" in title:
            if atype == "choice":
                agency = ans.get("choice", {}).get("label", "").strip()
            elif atype == "text":
                agency = (ans.get("text") or "").strip()
        elif "name" in title:
            if atype == "text":
                name = (ans.get("text") or "").strip()
    return name, agency

def norm_name(n):
    return " ".join((n or "").lower().split())

def norm_agency(a):
    return AGENCY_ALIASES.get((a or "").lower().strip(), a or "Other")

def build_rows():
    participants = {}
    debug_done = False
    for form_id, mapping in FORM_MAPPING.items():
        training = mapping["training"]
        form_group = mapping["group"]
        print(f"  Fetching {form_id}: {training} (G{form_group})")
        field_map = get_field_map(form_id)
        responses = get_form_responses(form_id)
        print(f"    → {len(responses)} responses")

        # Debug: print field map for first form only
        if not debug_done:
            print(f"  DEBUG field_map for {form_id}: {field_map}")
            debug_done = True

        for resp in responses:
            name, agency = extract_name_agency(resp, field_map)
            if not name:
                continue
            nn = norm_name(name)
            agency = norm_agency(agency)
            if nn not in participants:
                participants[nn] = {"name": name, "agency": agency,
                                    "group": form_group if form_group > 0 else 0,
                                    "attended": set()}
            else:
                p = participants[nn]
                if p["group"] == 0 and form_group > 0:
                    p["group"] = form_group
                if agency != "Other" and (not p["agency"] or p["agency"] == "Other"):
                    p["agency"] = agency
            if training in TRAININGS:
                participants[nn]["attended"].add(training)
    rows = []
    for p in participants.values():
        attended = sorted(p["attended"], key=lambda t: TRAININGS.index(t))
        pct = round(len(attended) / len(TRAININGS) * 100)
        rows.append({"agency": p["agency"], "name": p["name"],
                     "group": p["group"] if p["group"] > 0 else 1,
                     "attended": attended, "pct": pct})
    rows.sort(key=lambda r: (r["agency"], r["name"]))
    return rows

def build_summary(rows):
    stats = {}
    for r in rows:
        ag = r["agency"]
        if ag not in stats:
            stats[ag] = {"count": 0, "total_pct": 0}
        stats[ag]["count"] += 1
        stats[ag]["total_pct"] += r["pct"]
    return {ag: {"count": v["count"], "pct": round(v["total_pct"] / v["count"])}
            for ag, v in sorted(stats.items())}

def find_const_end(content, start_pos):
    open_ch = content[start_pos]
    close_ch = "]" if open_ch == "[" else "}"
    depth = 0
    in_str = False
    esc = False
    str_ch = None
    i = start_pos
    while i < len(content):
        c = content[i]
        if esc: esc = False
        elif c == "\\" and in_str: esc = True
        elif in_str:
            if c == str_ch: in_str = False
        elif c in ('"', "'", "`"):
            in_str = True; str_ch = c
        elif c == open_ch: depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                end = i + 1
                if end < len(content) and content[end] == ";":
                    end += 1
                return end
        i += 1
    raise ValueError("Unterminated JS value")

def replace_js_const(content, const_name, new_value_str):
    pattern = re.compile(rf"const\s+{re.escape(const_name)}\s*=\s*")
    m = pattern.search(content)
    if not m:
        raise ValueError(f"Could not find 'const {const_name}' in HTML")
    val_start = m.end()
    val_end = find_const_end(content, val_start)
    replacement = f"const {const_name:<8} = {new_value_str};"
    return content[:m.start()] + replacement + content[val_end:]

def update_html(rows, summary):
    html_path = os.path.join(os.path.dirname(__file__), "..", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()
    content = replace_js_const(content, "ROWS", json.dumps(rows, ensure_ascii=False))
    content = replace_js_const(content, "SUMMARY", json.dumps(summary, ensure_ascii=False))
    now = datetime.now(timezone.utc)
    ts = f"{now.strftime('%B')} {now.day}, {now.strftime('%Y')} at {now.strftime('%I:%M %p').lstrip('0')}"
    content = re.sub(r"Last updated:.*?(?=</span>)", f"Last updated: {ts}", content)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ index.html updated: {len(rows)} participants, {len(summary)} agencies")

if __name__ == "__main__":
    print("Fetching Typeform responses...")
    rows = build_rows()
    summary = build_summary(rows)
    print(f"\nBuilding dashboard: {len(rows)} participants across {len(summary)} agencies")
    update_html(rows, summary)
