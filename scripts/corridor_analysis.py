from pathlib import Path
import sys
import pandas as pd
import geopandas as gpd


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

INTERSTATES_FILE = DATA_DIR / "interstates_real.geojson"
RESTAURANTS_FILE = DATA_DIR / "restaurants.csv"
EXITS_FILE = DATA_DIR / "interstate_exits.csv"

# Output files
EW_INTERSTATES_OUT = OUTPUT_DIR / "east_west_interstates.geojson"
INTERSTATE_BUFFER_OUT = OUTPUT_DIR / "east_west_interstate_buffer_2mi.geojson"
EXIT_BUFFER_OUT = OUTPUT_DIR / "interstate_exit_buffer_2mi.geojson"

RESTAURANTS_NEAR_CORRIDOR_OUT = OUTPUT_DIR / "restaurants_near_corridor.geojson"
RESTAURANTS_NEAR_EXITS_OUT = OUTPUT_DIR / "restaurants_near_exits.geojson"

RESTAURANTS_NEAR_CORRIDOR_CSV = OUTPUT_DIR / "restaurants_near_corridor.csv"
RESTAURANTS_NEAR_EXITS_CSV = OUTPUT_DIR / "restaurants_near_exits.csv"

EXIT_SUMMARY_CSV = OUTPUT_DIR / "exit_accessibility_summary.csv"
CORRIDOR_SUMMARY_CSV = OUTPUT_DIR / "corridor_summary.csv"

TARGET_INTERSTATES = {"I-10", "I-20", "I-30", "I-40", "I-70", "I-80", "I-90"}

BUFFER_MILES = 2.0

PROJECTED_CRS = "EPSG:5070"
GEOGRAPHIC_CRS = "EPSG:4326"


# ============================================================
# HELPERS
# ============================================================

def miles_to_meters(miles: float) -> float:
    return miles * 1609.344


def normalize_interstate_name(value) -> str | None:
    if pd.isna(value):
        return None

    text = str(value).strip().upper()
    if not text:
        return None

    replacements = {
        "INTERSTATE ": "I-",
        "I ": "I-",
        "I_": "I-",
        "IH ": "I-",
        "IH-": "I-",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = text.replace("--", "-").replace("  ", " ").strip()

    if text.startswith("I-"):
        return text.split()[0]

    if text.isdigit():
        return f"I-{text}"

    if text.startswith("I") and text[1:].isdigit():
        return f"I-{text[1:]}"

    return text


def find_interstate_field(gdf: gpd.GeoDataFrame) -> str:
    preferred = [
        "FULLNAME", "fullname",
        "route_num", "route", "name", "ref", "highway"
    ]

    for p in preferred:
        if p in gdf.columns:
            return p

    cols_lower = {c.lower(): c for c in gdf.columns}
    for p in ["fullname", "route_num", "route", "name", "ref", "highway"]:
        if p in cols_lower:
            return cols_lower[p]

    for col in gdf.columns:
        if col == "geometry":
            continue
        if pd.api.types.is_object_dtype(gdf[col]) or pd.api.types.is_string_dtype(gdf[col]):
            return col

    raise ValueError(
        "Could not identify an interstate name field in interstates dataset. "
        f"Available columns: {list(gdf.columns)}"
    )


def require_file(path: Path, description: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {description}: {path}")


def load_restaurants(path: Path) -> gpd.GeoDataFrame:
    df = pd.read_csv(path, low_memory=False)

    required = {"lat", "lon"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"restaurants.csv is missing required columns: {sorted(missing)}")

    df = df.dropna(subset=["lat", "lon"]).copy()

    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["lon"], df["lat"]),
        crs=GEOGRAPHIC_CRS
    )
    return gdf


def load_exits(path: Path) -> gpd.GeoDataFrame:
    df = pd.read_csv(path, low_memory=False)

    required = {"lat", "lon"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"interstate_exits.csv is missing required columns: {sorted(missing)}")

    df = df.dropna(subset=["lat", "lon"]).copy()

    if "interstate_guess" in df.columns:
        df["interstate_guess_norm"] = df["interstate_guess"].apply(normalize_interstate_name)
    else:
        df["interstate_guess_norm"] = None

    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["lon"], df["lat"]),
        crs=GEOGRAPHIC_CRS
    )
    return gdf


def load_interstates(path: Path) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)

    if gdf.empty:
        raise ValueError("Interstates file loaded but contains no features.")

    if gdf.crs is None:
        print("Warning: interstates file has no CRS; assuming EPSG:4326")
        gdf = gdf.set_crs(GEOGRAPHIC_CRS)

    name_field = find_interstate_field(gdf)
    print(f"Using interstate field: {name_field}")

    gdf["interstate_norm"] = gdf[name_field].apply(normalize_interstate_name)
    ew = gdf[gdf["interstate_norm"].isin(TARGET_INTERSTATES)].copy()

    if ew.empty:
        unique_vals = sorted({str(v) for v in gdf[name_field].dropna().unique()[:50]})
        raise ValueError(
            "No target east-west interstates found. "
            f"Field checked: {name_field}. Example values: {unique_vals}"
        )

    return ew


# ============================================================
# ANALYSIS
# ============================================================

def main() -> None:
    print("Checking input files...")
    require_file(INTERSTATES_FILE, "interstates file")
    require_file(RESTAURANTS_FILE, "restaurants file")
    require_file(EXITS_FILE, "interstate exits file")

    print("Loading datasets...")
    interstates = load_interstates(INTERSTATES_FILE)
    restaurants = load_restaurants(RESTAURANTS_FILE)
    exits = load_exits(EXITS_FILE)

    print(f"Loaded {len(interstates):,} interstate features")
    print(f"Loaded {len(restaurants):,} restaurants")
    print(f"Loaded {len(exits):,} exits")

    print("Reprojecting datasets...")
    interstates_proj = interstates.to_crs(PROJECTED_CRS)
    restaurants_proj = restaurants.to_crs(PROJECTED_CRS)
    exits_proj = exits.to_crs(PROJECTED_CRS)

    buffer_m = miles_to_meters(BUFFER_MILES)

    print(f"Creating {BUFFER_MILES}-mile interstate corridor buffers...")
    interstate_buffers = interstates_proj[["interstate_norm", "geometry"]].copy()
    interstate_buffers["geometry"] = interstate_buffers.geometry.buffer(buffer_m)
    interstate_buffers = interstate_buffers.dissolve(by="interstate_norm", as_index=False)

    print(f"Creating {BUFFER_MILES}-mile exit buffers...")
    exit_buffers = exits_proj.copy()
    exit_buffers["geometry"] = exit_buffers.geometry.buffer(buffer_m)

    print("Finding restaurants near interstate corridors...")
    restaurants_near_corridor = gpd.sjoin(
        restaurants_proj,
        interstate_buffers[["interstate_norm", "geometry"]],
        how="inner",
        predicate="intersects"
    ).copy()

    restaurants_near_corridor = restaurants_near_corridor.rename(
        columns={"interstate_norm": "corridor_interstate"}
    )

    subset_cols = [c for c in ["osm_type", "osm_id", "corridor_interstate"] if c in restaurants_near_corridor.columns]
    if subset_cols:
        restaurants_near_corridor = restaurants_near_corridor.drop_duplicates(subset=subset_cols)

    print("Finding restaurants near exits...")
    exits_for_join = exits_proj.copy()
    exits_for_join["exit_uid"] = exits_for_join.index.astype(str)

    exit_buffers_for_join = exit_buffers.copy()
    exit_buffers_for_join["exit_uid"] = exits_for_join["exit_uid"].values

    keep_cols = ["exit_uid", "geometry"]
    for col in ["ref", "name", "interstate_guess_norm"]:
        if col in exit_buffers_for_join.columns:
            keep_cols.append(col)

    restaurants_near_exits = gpd.sjoin(
        restaurants_proj,
        exit_buffers_for_join[keep_cols],
        how="inner",
        predicate="intersects"
    ).copy()

    rename_map = {}
    if "ref" in restaurants_near_exits.columns:
        rename_map["ref"] = "exit_ref"
    if "name" in restaurants_near_exits.columns:
        rename_map["name"] = "exit_name"
    if "interstate_guess_norm" in restaurants_near_exits.columns:
        rename_map["interstate_guess_norm"] = "exit_interstate_guess"

    restaurants_near_exits = restaurants_near_exits.rename(columns=rename_map)

    dedupe_cols = [c for c in ["osm_type", "osm_id", "exit_uid"] if c in restaurants_near_exits.columns]
    if dedupe_cols:
        restaurants_near_exits = restaurants_near_exits.drop_duplicates(subset=dedupe_cols)

    print("Building summaries...")

    corridor_summary = (
        restaurants_near_corridor.groupby("corridor_interstate")
        .size()
        .reset_index(name="restaurant_count")
        .sort_values("corridor_interstate")
    )

    exit_summary = (
        restaurants_near_exits.groupby("exit_uid")
        .size()
        .reset_index(name="restaurants_within_2mi")
    )

    exits_summary = exits_proj.copy()
    exits_summary["exit_uid"] = exits_summary.index.astype(str)

    exits_summary = exits_summary.merge(
        exit_summary,
        on="exit_uid",
        how="left"
    )

    exits_summary["restaurants_within_2mi"] = exits_summary["restaurants_within_2mi"].fillna(0).astype(int)
    exits_summary["has_food_within_2mi"] = exits_summary["restaurants_within_2mi"] > 0

    print("Saving outputs...")

    interstates.to_crs(GEOGRAPHIC_CRS).to_file(EW_INTERSTATES_OUT, driver="GeoJSON")
    interstate_buffers.to_crs(GEOGRAPHIC_CRS).to_file(INTERSTATE_BUFFER_OUT, driver="GeoJSON")
    exit_buffers.to_crs(GEOGRAPHIC_CRS).to_file(EXIT_BUFFER_OUT, driver="GeoJSON")

    restaurants_near_corridor.to_crs(GEOGRAPHIC_CRS).to_file(RESTAURANTS_NEAR_CORRIDOR_OUT, driver="GeoJSON")
    restaurants_near_exits.to_crs(GEOGRAPHIC_CRS).to_file(RESTAURANTS_NEAR_EXITS_OUT, driver="GeoJSON")

    restaurants_near_corridor.drop(columns="geometry").to_csv(RESTAURANTS_NEAR_CORRIDOR_CSV, index=False)
    restaurants_near_exits.drop(columns="geometry").to_csv(RESTAURANTS_NEAR_EXITS_CSV, index=False)
    corridor_summary.to_csv(CORRIDOR_SUMMARY_CSV, index=False)
    exits_summary.drop(columns="geometry").to_csv(EXIT_SUMMARY_CSV, index=False)

    print("\nDone.")
    print(f"Saved: {EW_INTERSTATES_OUT}")
    print(f"Saved: {INTERSTATE_BUFFER_OUT}")
    print(f"Saved: {EXIT_BUFFER_OUT}")
    print(f"Saved: {RESTAURANTS_NEAR_CORRIDOR_OUT}")
    print(f"Saved: {RESTAURANTS_NEAR_EXITS_OUT}")
    print(f"Saved: {RESTAURANTS_NEAR_CORRIDOR_CSV}")
    print(f"Saved: {RESTAURANTS_NEAR_EXITS_CSV}")
    print(f"Saved: {CORRIDOR_SUMMARY_CSV}")
    print(f"Saved: {EXIT_SUMMARY_CSV}")

    print("\nSummary:")
    print(corridor_summary.to_string(index=False))
    print(f"\nRestaurants near corridor: {len(restaurants_near_corridor):,}")
    print(f"Restaurants near exits:    {len(restaurants_near_exits):,}")
    print(f"Exits total:               {len(exits_summary):,}")
    print(f"Exits with food nearby:    {exits_summary['has_food_within_2mi'].sum():,}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)