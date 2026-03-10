import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = BASE_DIR / "scripts"

PIPELINE = [
    "collect_osm_restaurants_by_state.py",
    "collect_interstate_exits_by_state.py",
    "corridor_analysis.py",
    "distance_analysis.py",
    "food_desert_detection.py",
    "network_access_analysis.py",
]


def run_script(script_name: str) -> None:
    script_path = SCRIPTS_DIR / script_name

    if not script_path.exists():
        print(f"ERROR: Script not found: {script_path}")
        sys.exit(1)

    print("\n==================================================")
    print(f"Running: {script_name}")
    print("==================================================\n")

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=BASE_DIR
    )

    if result.returncode != 0:
        print(f"\nERROR: {script_name} failed with exit code {result.returncode}")
        sys.exit(result.returncode)

    print(f"\nCompleted: {script_name}\n")


def main() -> None:
    print("\n==================================================")
    print("Interstate Food Accessibility Pipeline")
    print("==================================================\n")

    print("This pipeline will run:")
    for script in PIPELINE:
        print(f" - {script}")

    for script in PIPELINE:
        run_script(script)

    print("\n==================================================")
    print("Pipeline Complete")
    print("==================================================\n")
    print("Key output locations:")
    print(" - data/")
    print(" - outputs/")


if __name__ == "__main__":
    main()