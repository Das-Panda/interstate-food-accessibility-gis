from pathlib import Path
import sys
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

INTERSTATES_FILE = DATA_DIR / "interstates_real.geojson"
RESTAURANTS_FILE = DATA_DIR / "restaurants.csv"

PROJECTED_CRS = "EPSG:5070"
GEOGRAPHIC_CRS = "EPSG:4326"

TARGET_INTERSTATES = {"I-10", "I-20", "I-30", "I-40", "I-70", "I-80", "I-90"}

CORRIDOR_BUFFER_MILES = 2.0
FOOD_DESERT_THRESHOLD_MILES = 50.0

GAP_SEGMENTS_OUT = OUTPUT_DIR / "food_desert_gap_segments.geojson"
GAP_SEGMENTS_CSV = OUTPUT_DIR / "food_desert_gap_segments.csv"
GAP_SUMMARY_CSV = OUTPUT_DIR / "food_desert_summary.csv"


def miles_to_meters(miles: float) -> float:
    return miles * 1609.344


def meters_to_miles(meters: float) -> float:
    return meters / 1609.344


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
        "Could not identify an interstate name field. "
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

    return gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["lon"], df["lat"]),
        crs=GEOGRAPHIC_CRS
    )


def load_interstates(path: Path) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)

    if gdf.empty:
        raise ValueError("Interstates file loaded but contains no features.")

    if gdf.crs is None:
        gdf = gdf.set_crs(GEOGRAPHIC_CRS)

    name_field = find_interstate_field(gdf)
    print(f"Using interstate field: {name_field}")

    gdf["interstate_norm"] = gdf[name_field].apply(normalize_interstate_name)
    gdf = gdf[gdf["interstate_norm"].isin(TARGET_INTERSTATES)].copy()

    if gdf.empty:
        raise ValueError("No target east-west interstates found in interstates dataset.")

    return gdf


def merge_lines_by_interstate(interstates_proj: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    merged = interstates_proj[["interstate_norm", "geometry"]].dissolve(by="interstate_norm", as_index=False)
    merged = merged.explode(index_parts=False).reset_index(drop=True)

    merged["geom_length_m"] = merged.geometry.length
    merged = (
        merged.sort_values(["interstate_norm", "geom_length_m"], ascending=[True, False])
        .drop_duplicates(subset=["interstate_norm"], keep="first")
        .drop(columns=["geom_length_m"])
        .reset_index(drop=True)
    )

    return merged


def project_restaurants_to_interstate(line, restaurant_points_gdf: gpd.GeoDataFrame) -> list[float]:
    measures = []
    for pt in restaurant_points_gdf.geometry:
        try:
            m = line.project(pt)
            measures.append(float(m))
        except Exception:
            continue
    return sorted(measures)


def build_gap_segments(interstate_name: str, line, measures: list[float], threshold_miles: float) -> list[dict]:
    line_length_m = float(line.length)
    threshold_m = miles_to_meters(threshold_miles)

    points_along = [0.0] + measures + [line_length_m]

    segments = []
    for i in range(len(points_along) - 1):
        start_m = points_along[i]
        end_m = points_along[i + 1]

        if end_m < start_m:
            continue

        gap_m = end_m - start_m
        gap_mi = meters_to_miles(gap_m)

        start_pt = line.interpolate(start_m)
        end_pt = line.interpolate(end_m)

        seg_geom = LineString([start_pt, end_pt])

        segments.append({
            "interstate": interstate_name,
            "start_measure_m": start_m,
            "end_measure_m": end_m,
            "gap_length_m": gap_m,
            "gap_length_mi": gap_mi,
            "is_food_desert": gap_m >= threshold_m,
            "geometry": seg_geom
        })

    return segments


def main() -> None:
    print("Checking input files...")
    require_file(INTERSTATES_FILE, "interstates file")
    require_file(RESTAURANTS_FILE, "restaurants file")

    print("Loading datasets...")
    interstates = load_interstates(INTERSTATES_FILE)
    restaurants = load_restaurants(RESTAURANTS_FILE)

    print(f"Loaded {len(interstates):,} interstate features")
    print(f"Loaded {len(restaurants):,} restaurants")

    print("Reprojecting...")
    interstates_proj = interstates.to_crs(PROJECTED_CRS)
    restaurants_proj = restaurants.to_crs(PROJECTED_CRS)

    print("Merging interstate geometries...")
    interstate_mainlines = merge_lines_by_interstate(interstates_proj)

    print(f"Creating {CORRIDOR_BUFFER_MILES}-mile corridor buffers...")
    corridor_buffers = interstate_mainlines.copy()
    corridor_buffers["geometry"] = corridor_buffers.geometry.buffer(miles_to_meters(CORRIDOR_BUFFER_MILES))

    print("Selecting restaurants accessible from interstate corridors...")
    accessible_restaurants = gpd.sjoin(
        restaurants_proj,
        corridor_buffers[["interstate_norm", "geometry"]],
        how="inner",
        predicate="intersects"
    ).copy()

    accessible_restaurants = accessible_restaurants.rename(columns={"interstate_norm": "corridor_interstate"})

    dedupe_cols = [c for c in ["osm_type", "osm_id", "corridor_interstate"] if c in accessible_restaurants.columns]
    if dedupe_cols:
        accessible_restaurants = accessible_restaurants.drop_duplicates(subset=dedupe_cols)

    print("Computing gap segments...")
    all_segments = []

    for _, row in interstate_mainlines.iterrows():
        interstate_name = row["interstate_norm"]
        line = row.geometry

        route_restaurants = accessible_restaurants[
            accessible_restaurants["corridor_interstate"] == interstate_name
        ].copy()

        measures = project_restaurants_to_interstate(line, route_restaurants)
        segments = build_gap_segments(
            interstate_name=interstate_name,
            line=line,
            measures=measures,
            threshold_miles=FOOD_DESERT_THRESHOLD_MILES
        )
        all_segments.extend(segments)

        print(
            f"  {interstate_name}: {len(route_restaurants):,} accessible restaurants, "
            f"{len(segments):,} gap segments"
        )

    gap_gdf = gpd.GeoDataFrame(all_segments, geometry="geometry", crs=PROJECTED_CRS)

    if gap_gdf.empty:
        raise ValueError("No gap segments were created.")

    gap_gdf["segment_type"] = gap_gdf["is_food_desert"].map({True: "Food Desert", False: "Served Segment"})

    desert_only = gap_gdf[gap_gdf["is_food_desert"]].copy()

    summary = (
        gap_gdf.groupby("interstate")
        .agg(
            total_gap_segments=("gap_length_mi", "size"),
            max_gap_mi=("gap_length_mi", "max"),
            mean_gap_mi=("gap_length_mi", "mean"),
            food_desert_segments=("is_food_desert", "sum")
        )
        .reset_index()
        .sort_values("interstate")
    )

    print("Saving outputs...")
    gap_gdf.to_crs(GEOGRAPHIC_CRS).to_file(GAP_SEGMENTS_OUT, driver="GeoJSON")
    gap_gdf.drop(columns="geometry").to_csv(GAP_SEGMENTS_CSV, index=False)
    summary.to_csv(GAP_SUMMARY_CSV, index=False)

    print("\nDone.")
    print(f"Saved: {GAP_SEGMENTS_OUT}")
    print(f"Saved: {GAP_SEGMENTS_CSV}")
    print(f"Saved: {GAP_SUMMARY_CSV}")

    print("\nFood desert summary:")
    print(summary.to_string(index=False))

    if not desert_only.empty:
        print("\nTop longest food desert segments:")
        print(
            desert_only[["interstate", "gap_length_mi"]]
            .sort_values("gap_length_mi", ascending=False)
            .head(10)
            .to_string(index=False)
        )
    else:
        print("\nNo food desert segments exceeded the threshold.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)