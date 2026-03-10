from pathlib import Path
import sys
import math
import pandas as pd
import geopandas as gpd

try:
    import osmnx as ox
    import networkx as nx
except ImportError as exc:
    raise ImportError(
        "This script requires osmnx and networkx. "
        "Install them with: pip install osmnx networkx"
    ) from exc


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RESTAURANTS_FILE = DATA_DIR / "restaurants.csv"
EXITS_FILE = DATA_DIR / "interstate_exits.csv"

OUTPUT_GEOJSON = OUTPUT_DIR / "network_exit_food_access.geojson"
OUTPUT_CSV = OUTPUT_DIR / "network_exit_food_access.csv"
SUMMARY_CSV = OUTPUT_DIR / "network_exit_food_access_summary.csv"

GEOGRAPHIC_CRS = "EPSG:4326"

# Practical defaults
MAX_SEARCH_DISTANCE_MILES = 15.0
FOOD_DESERT_DRIVE_MILES = 10.0
FOOD_DESERT_DRIVE_MINUTES = 15.0


def require_file(path: Path, description: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {description}: {path}")


def meters_to_miles(value: float) -> float:
    return value / 1609.344


def seconds_to_minutes(value: float) -> float:
    return value / 60.0


def load_points(csv_path: Path, kind: str) -> gpd.GeoDataFrame:
    df = pd.read_csv(csv_path)

    required = {"lat", "lon"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{kind} CSV missing required columns: {sorted(missing)}")

    df = df.dropna(subset=["lat", "lon"]).copy()

    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["lon"], df["lat"]),
        crs=GEOGRAPHIC_CRS
    )

    return gdf


def get_combined_bbox(exits_gdf: gpd.GeoDataFrame, restaurants_gdf: gpd.GeoDataFrame, pad_degrees: float = 0.25):
    all_points = pd.concat(
        [
            exits_gdf[["geometry"]],
            restaurants_gdf[["geometry"]]
        ],
        ignore_index=True
    )
    bounds = gpd.GeoSeries(all_points["geometry"], crs=GEOGRAPHIC_CRS).total_bounds
    minx, miny, maxx, maxy = bounds
    return (miny - pad_degrees, minx - pad_degrees, maxy + pad_degrees, maxx + pad_degrees)


def build_graph_for_bbox(north: float, south: float, east: float, west: float):
    print("Downloading drivable road network from OpenStreetMap...")
    G = ox.graph_from_bbox(
        bbox=(west, south, east, north),
        network_type="drive",
        simplify=True,
        retain_all=False
    )

    print("Adding travel times...")
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)

    return G


def safe_text(value):
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text if text else None


def choose_exit_label(row: pd.Series) -> str:
    for field in ["ref", "name", "destination", "exit_to", "interstate_guess"]:
        if field in row.index:
            value = safe_text(row[field])
            if value:
                return value
    return f"Exit_{row.name}"


def choose_restaurant_label(row: pd.Series) -> str:
    for field in ["brand", "name", "display_name"]:
        if field in row.index:
            value = safe_text(row[field])
            if value:
                return value
    return f"Restaurant_{row.name}"


def nearest_graph_nodes(G, gdf: gpd.GeoDataFrame, x_col="lon", y_col="lat") -> pd.Series:
    return pd.Series(
        ox.distance.nearest_nodes(G, X=gdf[x_col].to_list(), Y=gdf[y_col].to_list()),
        index=gdf.index
    )


def compute_nearest_restaurant_for_exit(G, exit_node, restaurant_nodes_df: pd.DataFrame):
    """
    Compute nearest restaurant from a single exit using shortest path length by travel time,
    then return nearest record and distance.
    """
    best_idx = None
    best_seconds = math.inf
    best_meters = math.inf

    for idx, row in restaurant_nodes_df.iterrows():
        rest_node = row["graph_node"]

        try:
            travel_seconds = nx.shortest_path_length(G, exit_node, rest_node, weight="travel_time")
            travel_meters = nx.shortest_path_length(G, exit_node, rest_node, weight="length")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue

        if travel_seconds < best_seconds:
            best_seconds = travel_seconds
            best_meters = travel_meters
            best_idx = idx

    return best_idx, best_meters, best_seconds


def main() -> None:
    print("Checking input files...")
    require_file(RESTAURANTS_FILE, "restaurants file")
    require_file(EXITS_FILE, "interstate exits file")

    print("Loading points...")
    restaurants = load_points(RESTAURANTS_FILE, "restaurants")
    exits = load_points(EXITS_FILE, "interstate exits")

    print(f"Loaded {len(restaurants):,} restaurants")
    print(f"Loaded {len(exits):,} exits")

    if restaurants.empty or exits.empty:
        raise ValueError("Restaurants or exits dataset is empty.")

    print("Building combined study-area bounding box...")
    south, west, north, east = get_combined_bbox(exits, restaurants)

    print(f"Study area bbox: south={south:.4f}, west={west:.4f}, north={north:.4f}, east={east:.4f}")
    G = build_graph_for_bbox(north=north, south=south, east=east, west=west)

    print("Snapping restaurants and exits to network...")
    restaurants["graph_node"] = nearest_graph_nodes(G, restaurants)
    exits["graph_node"] = nearest_graph_nodes(G, exits)

    # Keep only relevant restaurant columns for matching
    restaurant_cols = [c for c in restaurants.columns if c != "geometry"]
    restaurant_nodes_df = restaurants[restaurant_cols].copy()

    print("Computing nearest drivable restaurant for each exit...")
    results = []

    for idx, exit_row in exits.iterrows():
        exit_node = exit_row["graph_node"]
        exit_label = choose_exit_label(exit_row)

        best_idx, best_meters, best_seconds = compute_nearest_restaurant_for_exit(
            G=G,
            exit_node=exit_node,
            restaurant_nodes_df=restaurant_nodes_df
        )

        result = exit_row.drop(labels=["geometry"]).to_dict()
        result["exit_label"] = exit_label

        if best_idx is None:
            result["nearest_restaurant_name"] = None
            result["nearest_restaurant_brand"] = None
            result["nearest_restaurant_lat"] = None
            result["nearest_restaurant_lon"] = None
            result["drive_distance_m"] = None
            result["drive_distance_mi"] = None
            result["drive_time_s"] = None
            result["drive_time_min"] = None
            result["food_desert_by_drive_distance"] = True
            result["food_desert_by_drive_time"] = True
        else:
            rest_row = restaurant_nodes_df.loc[best_idx]
            result["nearest_restaurant_name"] = safe_text(rest_row.get("name"))
            result["nearest_restaurant_brand"] = safe_text(rest_row.get("brand"))
            result["nearest_restaurant_lat"] = rest_row.get("lat")
            result["nearest_restaurant_lon"] = rest_row.get("lon")
            result["drive_distance_m"] = float(best_meters)
            result["drive_distance_mi"] = meters_to_miles(float(best_meters))
            result["drive_time_s"] = float(best_seconds)
            result["drive_time_min"] = seconds_to_minutes(float(best_seconds))
            result["food_desert_by_drive_distance"] = result["drive_distance_mi"] > FOOD_DESERT_DRIVE_MILES
            result["food_desert_by_drive_time"] = result["drive_time_min"] > FOOD_DESERT_DRIVE_MINUTES

        results.append(result)

        if (idx + 1) % 100 == 0:
            print(f"Processed {idx + 1:,} / {len(exits):,} exits")

    result_df = pd.DataFrame(results)

    # Optional convenience flag
    result_df["food_desert_combined"] = (
        result_df["food_desert_by_drive_distance"].fillna(True)
        | result_df["food_desert_by_drive_time"].fillna(True)
    )

    # Rebuild GeoDataFrame from exit coordinates
    result_gdf = gpd.GeoDataFrame(
        result_df,
        geometry=gpd.points_from_xy(result_df["lon"], result_df["lat"]),
        crs=GEOGRAPHIC_CRS
    )

    # Summary
    summary_rows = []

    if "interstate_guess" in result_df.columns:
        interstate_field = "interstate_guess"
    elif "interstate_guess_norm" in result_df.columns:
        interstate_field = "interstate_guess_norm"
    else:
        interstate_field = None

    if interstate_field:
        grouped = result_df.groupby(interstate_field, dropna=False)
        for interstate, group in grouped:
            summary_rows.append({
                "interstate": interstate,
                "exit_count": len(group),
                "avg_drive_distance_mi": group["drive_distance_mi"].mean(),
                "max_drive_distance_mi": group["drive_distance_mi"].max(),
                "avg_drive_time_min": group["drive_time_min"].mean(),
                "max_drive_time_min": group["drive_time_min"].max(),
                "food_desert_exit_count": int(group["food_desert_combined"].fillna(True).sum())
            })
    else:
        summary_rows.append({
            "interstate": "ALL",
            "exit_count": len(result_df),
            "avg_drive_distance_mi": result_df["drive_distance_mi"].mean(),
            "max_drive_distance_mi": result_df["drive_distance_mi"].max(),
            "avg_drive_time_min": result_df["drive_time_min"].mean(),
            "max_drive_time_min": result_df["drive_time_min"].max(),
            "food_desert_exit_count": int(result_df["food_desert_combined"].fillna(True).sum())
        })

    summary_df = pd.DataFrame(summary_rows)

    print("Saving outputs...")
    result_gdf.to_file(OUTPUT_GEOJSON, driver="GeoJSON")
    result_df.to_csv(OUTPUT_CSV, index=False)
    summary_df.to_csv(SUMMARY_CSV, index=False)

    print("\nDone.")
    print(f"Saved: {OUTPUT_GEOJSON}")
    print(f"Saved: {OUTPUT_CSV}")
    print(f"Saved: {SUMMARY_CSV}")

    print("\nSummary preview:")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)