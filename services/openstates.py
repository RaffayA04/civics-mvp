import os, datetime, requests

BASE = "https://v3.openstates.org"

def _headers():
    key = os.getenv("OPENSTATES_KEY", "")
    if not key:
        raise RuntimeError("Missing OPENSTATES_KEY in environment")
    return {"X-API-KEY": key}

def recent_bills_for_state(state_name: str, days: int = 14, limit: int = 25):
    """Return most recently updated bills for a state (jurisdiction = full state name)."""
    since = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    params = {
        "jurisdiction": state_name,
        "sort": "updated_desc",
        "per_page": str(limit),
        "updated_since": since
    }
    r = requests.get(f"{BASE}/bills", params=params, headers=_headers(), timeout=20)
    r.raise_for_status()
    data = r.json() or {}
    bills = []
    for b in data.get("results", []) or []:
        la = b.get("latest_action") or {}
        link = b.get("openstates_url") or f"https://openstates.org/bill/{b.get('id')}"
        bills.append({
            "title": b.get("title"),
            "identifier": b.get("identifier"),
            "status": la.get("description"),
            "latest_action_date": la.get("date"),
            "link": link,
        })
    return bills
