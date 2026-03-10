from pathlib import Path
import geopandas as gpd
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"

OUTPUT_DIR.mkdir(exist_ok=True)

INTERSTATES_FILE = DATA_DIR / "interstates_real.geojson"
RESTAURANTS_FILE = DATA_DIR / "restaurants.csv"
EXITS_FILE = DATA_DIR / "interstate_exits.csv"

PROJECTED_CRS = "EPSG:5070"
GEOGRAPHIC_CRS = "EPSG:4326"


def meters_to_miles(m):
    return m / 1609.344


def load_restaurants():
    df = pd.read_csv(RESTAURANTS_FILE, low_memory=False)

    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df.lon, df.lat),
        crs=GEOGRAPHIC_CRS
    )

    return gdf


def load_exits():
    df = pd.read_csv(EXITS_FILE, low_memory=False)

    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df.lon, df.lat),
        crs=GEOGRAPHIC_CRS
    )

    return gdf


def main():
    print("Loading datasets...")

    restaurants = load_restaurants()
    exits = load_exits()
    interstates = gpd.read_file(INTERSTATES_FILE)

    restaurants = restaurants.to_crs(PROJECTED_CRS)
    exits = exits.to_crs(PROJECTED_CRS)
    interstates = interstates.to_crs(PROJECTED_CRS)

    print("Computing nearest interstate distances...")

    nearest_corridor = gpd.sjoin_nearest(
        restaurants,
        interstates,
        how="left",
        distance_col="dist_to_interstate_m"
    )

    nearest_corridor["dist_to_interstate_mi"] = nearest_corridor["dist_to_interstate_m"].apply(meters_to_miles)

    for col in ["index_right", "index_left"]:
        if col in nearest_corridor.columns:
            nearest_corridor = nearest_corridor.drop(columns=[col])

    print("Computing nearest exit distances...")

    nearest_exit = gpd.sjoin_nearest(
        nearest_corridor,
        exits,
        how="left",
        distance_col="dist_to_exit_m",
        rsuffix="exit"
    )

    nearest_exit["dist_to_exit_mi"] = nearest_exit["dist_to_exit_m"].apply(meters_to_miles)

    output_file = OUTPUT_DIR / "restaurant_distance_analysis.geojson"
    nearest_exit.to_crs(GEOGRAPHIC_CRS).to_file(output_file, driver="GeoJSON")

    csv_file = OUTPUT_DIR / "restaurant_distance_analysis.csv"
    nearest_exit.drop(columns="geometry").to_csv(csv_file, index=False)

    print("Saved outputs:")
    print(output_file)
    print(csv_file)


if __name__ == "__main__":
    main()