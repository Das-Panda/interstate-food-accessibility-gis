import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import requests


# ============================================================
# CONFIG
# ============================================================

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# Re-query a state only if it hasn't been refreshed in this many days.
# Set to 0 to force refresh every run.
REQUERY_AFTER_DAYS = 30

# Continental U.S. + DC approximate bounding boxes
# Format: state_abbr: (south, west, north, east)
STATE_BBOXES = {
    "AL": (30.1375, -88.4732, 35.0080, -84.8882),
    "AZ": (31.3322, -114.8165, 37.0043, -109.0452),
    "AR": (33.0041, -94.6179, 36.4997, -89.6448),
    "CA": (32.5288, -124.4820, 42.0095, -114.1312),
    "CO": (36.9924, -109.0603, 41.0034, -102.0416),
    "CT": (40.9801, -73.7278, 42.0506, -71.7869),
    "DE": (38.4510, -75.7890, 39.8395, -75.0489),
    "FL": (24.3963, -87.6349, 31.0009, -80.0314),
    "GA": (30.3558, -85.6052, 35.0008, -80.8397),
    "ID": (41.9881, -117.2430, 49.0009, -111.0436),
    "IL": (36.9703, -91.5131, 42.5085, -87.4948),
    "IN": (37.7717, -88.0978, 41.7614, -84.7846),
    "IA": (40.3754, -96.6397, 43.5012, -90.1401),
    "KS": (36.9930, -102.0517, 40.0032, -94.5884),
    "KY": (36.4971, -89.5715, 39.1475, -81.9648),
    "LA": (28.8551, -94.0431, 33.0195, -88.7584),
    "ME": (43.0649, -71.0843, 47.4599, -66.9499),
    "MD": (37.8866, -79.4877, 39.7230, -75.0489),
    "MA": (41.2379, -73.5081, 42.8868, -69.9284),
    "MI": (41.6961, -90.4181, 48.3061, -82.1228),
    "MN": (43.4994, -97.2391, 49.3844, -89.4917),
    "MS": (30.1739, -91.6550, 34.9961, -88.0979),
    "MO": (35.9957, -95.7747, 40.6136, -89.0988),
    "MT": (44.3582, -116.0500, 49.0014, -104.0396),
    "NE": (39.9999, -104.0535, 43.0017, -95.3083),
    "NV": (35.0019, -120.0057, 42.0022, -114.0396),
    "NH": (42.6970, -72.5572, 45.3058, -70.6106),
    "NJ": (38.9285, -75.5636, 41.3574, -73.8939),
    "NM": (31.3323, -109.0502, 37.0003, -103.0019),
    "NY": (40.4774, -79.7624, 45.0159, -71.7517),
    "NC": (33.8423, -84.3219, 36.5881, -75.4606),
    "ND": (45.9351, -104.0493, 49.0007, -96.5544),
    "OH": (38.4032, -84.8203, 41.9775, -80.5187),
    "OK": (33.6158, -103.0025, 37.0023, -94.4307),
    "OR": (41.9921, -124.7035, 46.2920, -116.4635),
    "PA": (39.7198, -80.5199, 42.5161, -74.6895),
    "RI": (41.1465, -71.8628, 42.0188, -71.1206),
    "SC": (32.0346, -83.3539, 35.2155, -78.4993),
    "SD": (42.4796, -104.0579, 45.9455, -96.4365),
    "TN": (34.9829, -90.3103, 36.6781, -81.6469),
    "TX": (25.8371, -106.6456, 36.5007, -93.5080),
    "UT": (36.9979, -114.0529, 42.0017, -109.0411),
    "VT": (42.7269, -73.4377, 45.0167, -71.4650),
    "VA": (36.5407, -83.6754, 39.4660, -75.2424),
    "WA": (45.5435, -124.8489, 49.0025, -116.9156),
    "WV": (37.2015, -82.6447, 40.6388, -77.7190),
    "WI": (42.4917, -92.8894, 47.3098, -86.2495),
    "WY": (40.9947, -111.0569, 45.0059, -104.0522),
    "DC": (38.7916, -77.1198, 38.9955, -76.9094),
}

OUTPUT_ROOT = Path("data")
STATE_DIR = OUTPUT_ROOT / "state_exits"
RAW_DIR = OUTPUT_ROOT / "raw_osm_state_exits"
MASTER_CSV = OUTPUT_ROOT / "interstate_exits.csv"
REFRESH_LOG = OUTPUT_ROOT / "state_exit_refresh_log.csv"

STATE_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# HELPERS
# ============================================================

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_tag(tags: dict, key: str):
    value = tags.get(key)
    if value is None:
        return None
    value = str(value).strip()
    return value if value else None


def get_lat_lon(element: dict):
    if "lat" in element and "lon" in element:
        return element.get("lat"), element.get("lon")

    center = element.get("center", {})
    return center.get("lat"), center.get("lon")


def build_query(bbox):
    south, west, north, east = bbox
    return f"""
    [out:json][timeout:300];
    (
      node["highway"="motorway_junction"]({south},{west},{north},{east});
      way["highway"="motorway_junction"]({south},{west},{north},{east});
      relation["highway"="motorway_junction"]({south},{west},{north},{east});
    );
    out center tags;
    """


def fetch_overpass_data(query: str, max_retries_per_endpoint: int = 4, pause_seconds: int = 12):
    last_error = None

    for url in OVERPASS_URLS:
        for attempt in range(1, max_retries_per_endpoint + 1):
            try:
                print(f"  Trying {url} (attempt {attempt}/{max_retries_per_endpoint})")
                response = requests.get(
                    url,
                    params={"data": query},
                    timeout=600,
                    headers={"User-Agent": "KennethStruck-GIS-Project/1.0"}
                )
                response.raise_for_status()
                data = response.json()

                if "elements" not in data:
                    raise ValueError("Response JSON missing 'elements'.")

                return data

            except Exception as exc:
                last_error = exc
                print(f"  Request failed: {exc}")
                if attempt < max_retries_per_endpoint:
                    print(f"  Waiting {pause_seconds} seconds before retry...")
                    time.sleep(pause_seconds)

        print("  Switching Overpass endpoint...")

    raise RuntimeError(f"All Overpass endpoints failed. Last error: {last_error}")


def normalize_record(element: dict, state_abbr: str, fetched_at: str):
    tags = element.get("tags", {})
    lat, lon = get_lat_lon(element)

    if lat is None or lon is None:
        return None

    ref = safe_tag(tags, "ref")
    name = safe_tag(tags, "name")
    exit_to = safe_tag(tags, "exit_to")
    destination = safe_tag(tags, "destination")
    destination_ref = safe_tag(tags, "destination:ref")
    interstate_guess = guess_interstate(tags)

    return {
        "osm_type": element.get("type"),
        "osm_id": element.get("id"),
        "state_bbox_source": state_abbr,
        "highway": safe_tag(tags, "highway"),
        "ref": ref,
        "name": name,
        "exit_to": exit_to,
        "destination": destination,
        "destination_ref": destination_ref,
        "interstate_guess": interstate_guess,
        "lat": lat,
        "lon": lon,
        "fetched_at_utc": fetched_at,
    }


def guess_interstate(tags: dict):
    """
    Very light heuristic.
    Sometimes motorway_junction tags include refs/destinations like I 35, I-40, etc.
    This keeps it simple for now.
    """
    candidates = [
        safe_tag(tags, "destination:ref"),
        safe_tag(tags, "destination"),
        safe_tag(tags, "ref"),
        safe_tag(tags, "name"),
    ]
    for value in candidates:
        if not value:
            continue
        upper = value.upper()
        for interstate in ["I-10", "I-20", "I-30", "I-35", "I-40", "I-45", "I-70", "I-80", "I-90", "I-95"]:
            if interstate in upper or interstate.replace("-", " ") in upper:
                return interstate
    return None


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.dropna(subset=["lat", "lon"]).copy()

    text_cols = [
        "osm_type", "state_bbox_source", "highway", "ref", "name",
        "exit_to", "destination", "destination_ref", "interstate_guess"
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    df["osm_id"] = pd.to_numeric(df["osm_id"], errors="coerce").astype("Int64")

    if "fetched_at_utc" in df.columns:
        df = df.sort_values("fetched_at_utc")

    # Keep latest version of same OSM object
    df = df.drop_duplicates(subset=["osm_type", "osm_id"], keep="last").copy()

    # Secondary dedupe for same exit ref + coordinates
    dedupe_cols = [c for c in ["ref", "lat", "lon"] if c in df.columns]
    if len(dedupe_cols) == 3:
        df = df.drop_duplicates(subset=dedupe_cols, keep="last").copy()

    sort_cols = [c for c in ["state_bbox_source", "interstate_guess", "ref", "name"] if c in df.columns]
    df = df.sort_values(sort_cols, na_position="last").reset_index(drop=True)

    return df


def load_refresh_log() -> pd.DataFrame:
    if REFRESH_LOG.exists():
        df = pd.read_csv(REFRESH_LOG)
        if "last_refresh_utc" in df.columns:
            df["last_refresh_utc"] = pd.to_datetime(df["last_refresh_utc"], utc=True, errors="coerce")
        return df
    return pd.DataFrame(columns=["state", "last_refresh_utc", "records_after_refresh"])


def save_refresh_log(df: pd.DataFrame):
    out = df.copy()
    if "last_refresh_utc" in out.columns:
        out["last_refresh_utc"] = out["last_refresh_utc"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    out.to_csv(REFRESH_LOG, index=False)


def state_needs_refresh(state_abbr: str, refresh_log: pd.DataFrame, requery_after_days: int) -> bool:
    if requery_after_days <= 0:
        return True

    if refresh_log.empty or state_abbr not in set(refresh_log["state"]):
        return True

    row = refresh_log.loc[refresh_log["state"] == state_abbr].sort_values("last_refresh_utc").tail(1)
    if row.empty:
        return True

    last_refresh = row.iloc[0]["last_refresh_utc"]
    if pd.isna(last_refresh):
        return True

    cutoff = datetime.now(timezone.utc) - timedelta(days=requery_after_days)
    return last_refresh.to_pydatetime() < cutoff


# ============================================================
# CORE PROCESSING
# ============================================================

def collect_state(state_abbr: str, bbox):
    print(f"\nCollecting exits for {state_abbr} ...")
    fetched_at = utc_now_iso()
    query = build_query(bbox)
    data = fetch_overpass_data(query)

    raw_path = RAW_DIR / f"{state_abbr.lower()}_exits_raw.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    elements = data.get("elements", [])
    print(f"  Raw OSM elements: {len(elements):,}")

    records = []
    skipped = 0

    for element in elements:
        rec = normalize_record(element, state_abbr, fetched_at)
        if rec is None:
            skipped += 1
            continue
        records.append(rec)

    state_df = pd.DataFrame(records)
    state_df = clean_dataframe(state_df)

    print(f"  Cleaned records: {len(state_df):,}")
    print(f"  Skipped: {skipped:,}")

    state_csv = STATE_DIR / f"{state_abbr.lower()}_exits.csv"
    state_df.to_csv(state_csv, index=False, encoding="utf-8")

    return state_df


def rebuild_master_from_state_files():
    frames = []
    for csv_path in sorted(STATE_DIR.glob("*_exits.csv")):
        try:
            df = pd.read_csv(csv_path)
            frames.append(df)
        except Exception as exc:
            print(f"Warning: could not read {csv_path.name}: {exc}")

    if not frames:
        return pd.DataFrame()

    master = pd.concat(frames, ignore_index=True)
    master = clean_dataframe(master)
    return master


def main():
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    refresh_log = load_refresh_log()

    refreshed_states = []
    skipped_states = []

    for state_abbr, bbox in STATE_BBOXES.items():
        if not state_needs_refresh(state_abbr, refresh_log, REQUERY_AFTER_DAYS):
            print(f"Skipping {state_abbr} exits (recently refreshed)")
            skipped_states.append(state_abbr)
            continue

        try:
            state_df = collect_state(state_abbr, bbox)

            now_ts = pd.Timestamp.now(tz="UTC")
            refresh_log = refresh_log.loc[refresh_log["state"] != state_abbr].copy()
            refresh_log = pd.concat([
                refresh_log,
                pd.DataFrame([{
                    "state": state_abbr,
                    "last_refresh_utc": now_ts,
                    "records_after_refresh": len(state_df)
                }])
            ], ignore_index=True)

            save_refresh_log(refresh_log)
            refreshed_states.append(state_abbr)

            print("  Sleeping 5 seconds before next state...")
            time.sleep(5)

        except Exception as exc:
            print(f"ERROR while processing exits for {state_abbr}: {exc}")

    print("\nRebuilding master interstate exits CSV from per-state CSVs...")
    master_df = rebuild_master_from_state_files()
    master_df.to_csv(MASTER_CSV, index=False, encoding="utf-8")

    print("\nDone.")
    print(f"Master CSV: {MASTER_CSV}")
    print(f"Refresh log: {REFRESH_LOG}")
    print(f"Refreshed states: {', '.join(refreshed_states) if refreshed_states else 'None'}")
    print(f"Skipped states: {', '.join(skipped_states) if skipped_states else 'None'}")
    print(f"Master exit record count: {len(master_df):,}")


if __name__ == "__main__":
    main()