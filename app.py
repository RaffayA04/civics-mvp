# app.py — template-based UI (v12)
import os, re
from flask import Flask, request, Response, render_template

# --- Load .env (no third-party deps) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
def load_env(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
load_env(ENV_PATH)

print(">>> RUNNING app.py (templates + styles.css) at", os.path.abspath(__file__), flush=True)

# --- Address → State (local parser) ---
_ABBR_TO_NAME = {
    "AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California","CO":"Colorado","CT":"Connecticut",
    "DE":"Delaware","FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho","IL":"Illinois","IN":"Indiana","IA":"Iowa",
    "KS":"Kansas","KY":"Kentucky","LA":"Louisiana","ME":"Maine","MD":"Maryland","MA":"Massachusetts","MI":"Michigan",
    "MN":"Minnesota","MS":"Mississippi","MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada","NH":"New Hampshire",
    "NJ":"New Jersey","NM":"New Mexico","NY":"New York","NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma",
    "OR":"Oregon","PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota","TN":"Tennessee",
    "TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia","WA":"Washington","WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming",
    "DC":"District of Columbia"
}
_STATE_RE = re.compile(r'\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC)\b', re.IGNORECASE)
def state_from_freeform_address(address: str) -> str | None:
    if not address: return None
    m = _STATE_RE.search(address.upper())
    return _ABBR_TO_NAME.get(m.group(1).upper()) if m else None

# --- External services ---
from services.openstates import recent_bills_for_state
from services.civic import voterinfo, _debug_next_election_id

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["TEMPLATES_AUTO_RELOAD"] = True

# ========== Utility/Debug ==========
@app.get("/health")
def health():
    return "ok"

@app.get("/debug/info")
def debug_info():
    lines = []
    lines.append(f"cwd: {os.getcwd()}")
    lines.append(f"app.py path: {os.path.abspath(__file__)}")
    lines.append(f".env exists: {os.path.exists(ENV_PATH)}")
    lines.append(f"OPENSTATES_KEY: {bool(os.getenv('OPENSTATES_KEY'))}")
    lines.append(f"GOOGLE_CIVIC_KEY: {bool(os.getenv('GOOGLE_CIVIC_KEY'))}")
    lines.append("routes:")
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        lines.append(f"  {rule.rule} -> {','.join(sorted(rule.methods))}")
    return Response("\n".join(lines), mimetype="text/plain")

@app.get("/debug/keys")
def debug_keys():
    return {
        "OPENSTATES_KEY": bool(os.getenv("OPENSTATES_KEY")),
        "GOOGLE_CIVIC_KEY": bool(os.getenv("GOOGLE_CIVIC_KEY")),
    }

@app.get("/debug/election")
def debug_election():
    try:
        eid = _debug_next_election_id()
        return f"next electionId: {eid}", 200
    except Exception as e:
        return f"error: {e}", 500

# ========== Main ==========
@app.route("/", methods=["GET", "POST"])
def index():
    ctx = {"address":"", "state_name":None, "bills":[], "vote":None, "errors":[]}

    if request.method == "POST":
        address = (request.form.get("address") or "").strip()
        ctx["address"] = address

        state_name = state_from_freeform_address(address)
        ctx["state_name"] = state_name

        if not state_name:
            ctx["errors"].append("Could not parse state from your address. Include the 2-letter state code (e.g., WA) and ZIP.")
        else:
            try:
                ctx["bills"] = recent_bills_for_state(state_name, days=14, limit=20)
            except Exception as e:
                ctx["errors"].append(f"Bills lookup failed: {e}")

        try:
            ctx["vote"] = voterinfo(address) if address else None
        except Exception as e:
            ctx["errors"].append(f"Voting info lookup failed: {e}")

    return render_template("index.html", **ctx)

if __name__ == "__main__":
    print(">>> Starting Flask dev server (no reloader)", flush=True)
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
