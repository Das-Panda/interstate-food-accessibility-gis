# Interstate Food Accessibility Analysis (Python + GIS)

## Overview

This project analyzes the spatial accessibility of food services along major east-west interstate transportation corridors in the United States using **Python** and **QGIS**.

The workflow automatically collects restaurant and interstate exit data from **OpenStreetMap** using the **Overpass API** on a **state-by-state basis**, then integrates those datasets with interstate highway data to evaluate service accessibility for long-distance travelers.

The project is designed as a **transportation geography and spatial accessibility study** that demonstrates:

- automated geospatial data collection
- scalable Python data engineering
- incremental dataset refresh workflows
- corridor and exit-based accessibility analysis
- GIS visualization and cartographic output

This repository is intended to function as both a **graduate-level GIS research project** and a **professional portfolio project** showcasing Python and geospatial analysis skills.

---

## Research Questions

### Primary Question

How accessible are food services to travelers along major interstate transportation corridors in the United States?

### Supporting Questions

- Which interstate corridors have the highest density of food services?
- Which interstate exits provide reliable access to nearby restaurants?
- Where are the longest travel gaps between accessible food-service locations?
- Are there geographic regions where travelers encounter **food-service deserts**?
- How can automated geospatial data pipelines support repeatable transportation accessibility analysis over time?

---

## Study Area

This project focuses on major east-west interstate highways across the continental United States, including:

- I-10
- I-20
- I-30
- I-40
- I-70
- I-80
- I-90

These routes represent major long-distance transportation corridors used for:

- freight movement
- tourism
- cross-country travel
- regional economic connectivity

Future project expansions may include north-south interstates and additional transportation infrastructure layers.

---

## Project Goals

The project has four major goals:

1. Build a **reproducible national restaurant dataset** using OpenStreetMap and Python.
2. Build a matching **national interstate exit dataset** using the same automated workflow.
3. Analyze food accessibility along interstate corridors using GIS-based corridor and exit buffers.
4. Create a workflow that can be rerun in future years to detect **newly added locations** and maintain an updated accessibility dataset.

---

## Data Sources

### 1. Interstate Highway Data
U.S. Census Bureau **TIGER/Line road datasets** or other highway network datasets used for mapping and corridor creation.

### 2. Interstate Exit Data
Collected from **OpenStreetMap** using the Overpass API.

Primary query feature:

- `highway=motorway_junction`

These represent interstate and motorway exit nodes.

### 3. Restaurant Data
Collected from **OpenStreetMap** using the Overpass API.

Primary query features:

- `amenity=fast_food`
- `amenity=restaurant`

This captures a broad set of food-service locations, including chain fast food and sit-down restaurants where tagged in OpenStreetMap.

---

## Data Collection Design

A major focus of this project is building a workflow that is both **scalable** and **maintainable**.

Instead of making a single nationwide API request, the collector runs **state by state**. This design is more reliable because it:

- reduces API timeout risk
- makes reruns safer
- allows incremental data refreshes
- preserves intermediate outputs
- supports long-term maintenance of the dataset

Both restaurant and interstate exit datasets follow the same general workflow:

- query one state at a time
- save a raw JSON response
- convert results into a cleaned per-state CSV
- rebuild a merged national master CSV
- maintain a refresh log so recently updated states can be skipped

This means the project can be rerun later and used to detect **new restaurants or exits added since the last collection cycle**.

---

## Incremental Refresh Workflow

One of the key technical features of this project is its **incremental refresh design**.

### Restaurant Collector
The restaurant collector:

- stores one CSV per state
- saves raw OpenStreetMap JSON responses
- maintains a `state_refresh_log.csv`
- rebuilds a national `restaurants.csv`

When rerun in the future, the script can:

- skip states refreshed recently
- refresh older states
- replace outdated per-state CSVs
- add newly built restaurant locations
- update changed OpenStreetMap feature attributes

### Interstate Exit Collector
The interstate exit collector follows the same logic:

- stores one exit CSV per state
- saves raw exit JSON responses
- maintains a `state_exit_refresh_log.csv`
- rebuilds a national `interstate_exits.csv`

This makes the repository useful not just as a one-time project, but as an **updatable geospatial infrastructure dataset**.

---

## Methodology

### 1. State-by-State Automated Data Collection

Python scripts collect restaurant and interstate exit data from OpenStreetMap on a state-by-state basis.

This avoids the instability of extremely large nationwide API requests and creates a more robust data engineering workflow.

### 2. Raw Data Archiving

Each state-level API response is saved as raw JSON for transparency, troubleshooting, and reproducibility.

This allows future review of source responses if data cleaning rules need to be adjusted.

### 3. Data Cleaning and Standardization

Collected records are standardized into consistent tabular outputs.

Typical cleaning steps include:

- removing duplicate features
- validating coordinates
- standardizing text fields
- building full address fields where possible
- preserving the newest version of matching OSM features
- creating analysis-friendly columns such as display names and likely chain indicators

### 4. Interstate Corridor Analysis

Major interstate highways are buffered by **2 miles** to represent a realistic service-access zone for nearby travelers.

Restaurants inside these buffers are classified as potentially accessible from the interstate corridor.

### 5. Exit Accessibility Analysis

Interstate exits are buffered by **2 miles** to identify food services reachable shortly after leaving the highway.

This allows the project to distinguish between:

- general food availability near a highway corridor
- food access specifically associated with exit points

### 6. Distance Analysis

A dedicated distance module calculates the distance from each restaurant to:

- the nearest interstate corridor
- the nearest interstate exit

This adds continuous accessibility measures beyond a simple within/not-within threshold approach.

### 7. Density Analysis

Spatial density analysis is used to evaluate clustering patterns along interstate corridors.

Potential methods include:

- kernel density estimation
- restaurant counts by corridor
- restaurant counts by state
- restaurants per 100 miles of interstate

### 8. Travel Gap Analysis

Distances between accessible food-service locations are evaluated along interstate routes to identify long service gaps.

Corridor segments with long distances between accessible locations can be classified as **food-service deserts** for travelers.

### 9. Food Desert Detection

A dedicated module identifies long interstate segments with limited food access by projecting accessible restaurant locations onto each interstate mainline and measuring gaps between consecutive food-service opportunities.

Segments exceeding a threshold of **50 miles** are classified as potential **food deserts for travelers**.

### 10. GIS Visualization

Final outputs are intended to be displayed and analyzed in QGIS through:

- corridor maps
- exit-accessibility maps
- density heatmaps
- travel-gap maps
- food-desert segment maps
- brand or amenity distribution maps

---

## Scripts

### `collect_osm_restaurants_by_state.py`
Builds the national restaurant dataset from OpenStreetMap using state-by-state collection.

Key outputs:

- per-state restaurant CSVs
- raw JSON source files
- national `restaurants.csv`
- refresh log for restaurant collection

### `collect_interstate_exits_by_state.py`
Builds the national interstate exit dataset using the same incremental workflow.

Key outputs:

- per-state exit CSVs
- raw JSON source files
- national `interstate_exits.csv`
- refresh log for exit collection

### `corridor_analysis.py`
Runs the core corridor and exit accessibility analysis.

Planned or current responsibilities include:

- loading interstate datasets
- selecting major east-west interstates
- buffering interstate corridors
- buffering interstate exits
- tagging restaurants within corridor buffers
- tagging restaurants near exits
- producing analysis-ready outputs for QGIS and summary tables

### `distance_analysis.py`
Calculates nearest-distance relationships between restaurants, interstate corridors, and interstate exits.

Key outputs:

- distance to nearest interstate
- distance to nearest exit
- geospatial outputs for QGIS visualization
- analysis-ready CSV summaries

### `food_desert_detection.py`
Identifies interstate gap segments where travelers may encounter long distances between accessible food-service locations.

Key outputs:

- food-desert segment GeoJSON
- gap-length summary tables
- per-interstate food-desert statistics

### `clean_data.py`
Reserved for any additional data harmonization, cleaning, or post-processing steps beyond the collection scripts.

### `run_pipeline.py`
Runs the full end-to-end workflow in sequence so the project can be reproduced with a single command.

---

## Repository Structure

```text
interstate-food-accessibility-gis
│
├── data
│   ├── restaurants.csv
│   ├── interstate_exits.csv
│   ├── state_refresh_log.csv
│   ├── state_exit_refresh_log.csv
│   ├── states
│   │   ├── tx_restaurants.csv
│   │   ├── ok_restaurants.csv
│   │   └── ...
│   ├── state_exits
│   │   ├── tx_exits.csv
│   │   ├── ok_exits.csv
│   │   └── ...
│   ├── raw_osm_states
│   │   ├── tx_restaurants_raw.json
│   │   └── ...
│   └── raw_osm_state_exits
│       ├── tx_exits_raw.json
│       └── ...
│
├── scripts
│   ├── collect_osm_restaurants_by_state.py
│   ├── collect_interstate_exits_by_state.py
│   ├── corridor_analysis.py
│   ├── distance_analysis.py
│   ├── food_desert_detection.py
│   └── clean_data.py
│
├── qgis
│   └── interstate_analysis.qgz
│
├── outputs
│   ├── east_west_interstates.geojson
│   ├── east_west_interstate_buffer_2mi.geojson
│   ├── interstate_exit_buffer_2mi.geojson
│   ├── restaurants_near_corridor.geojson
│   ├── restaurants_near_exits.geojson
│   ├── restaurants_near_corridor.csv
│   ├── restaurants_near_exits.csv
│   ├── corridor_summary.csv
│   ├── exit_accessibility_summary.csv
│   ├── restaurant_distance_analysis.geojson
│   ├── restaurant_distance_analysis.csv
│   ├── food_desert_gap_segments.geojson
│   ├── food_desert_gap_segments.csv
│   └── food_desert_summary.csv
│
├── run_pipeline.py
├── requirements.txt
├── .gitignore
└── README.md
```

Expected Outputs

This project is intended to produce several map and data outputs, including:

interstate corridor accessibility maps

interstate exit accessibility maps

food-service density heatmaps

service-gap maps

food-desert segment maps

cleaned restaurant datasets

cleaned exit datasets

nearest-distance analysis tables

analysis-ready tables for QGIS or further Python workflows

Example derived tables may include:

restaurants within 2 miles of target interstate corridors

exits with at least one nearby food-service location

exits without nearby food-service locations

corridor segments with large travel gaps between food opportunities

restaurants ranked by proximity to exits or corridors

longest interstate food-desert segments

Tools Used
Python

pandas

requests

geopandas

shapely

fiona

pyproj

GIS

QGIS

Spatial Data Sources

OpenStreetMap Overpass API

U.S. Census TIGER/Line datasets

Future versions may also incorporate:

network analysis libraries

traffic or AADT datasets

interactive web mapping libraries

Skills Demonstrated

This project demonstrates a combination of GIS, Python, and geospatial data engineering skills.

Programming and Data Engineering

automated API-based geospatial data collection

state-by-state scalable data ingestion

incremental refresh workflows

raw-to-clean dataset processing

reproducible project structure

pipeline automation

GIS and Spatial Analysis

corridor buffering

exit-based accessibility modeling

nearest-distance analysis

spatial joins

density analysis

travel-gap identification

food-desert segment detection

cartographic presentation in QGIS

Research and Applied Analysis

transportation geography

service accessibility analysis

infrastructure support analysis

reproducible GIS project design

Applications

This type of analysis is relevant to many real-world domains, including:

transportation planning

logistics and route-support analysis

truck stop and service planning

retail site selection

tourism infrastructure analysis

EV charging accessibility studies

gas station and roadside service analysis

corridor-based economic geography

Why This Project Matters

This project goes beyond simply mapping restaurants.

It demonstrates how a geospatial analyst can:

build a national dataset from public spatial data sources

maintain that dataset over time

connect point-based services to transportation infrastructure

identify real accessibility patterns using repeatable methods

In other words, the project is intended to show not only GIS mapping ability, but also the ability to design and maintain a full geospatial workflow.

Future Improvements

Planned or possible future enhancements include:

replacing approximate state bounding boxes with polygon-based state clipping

adding north-south interstates

restricting exit analysis to the selected interstate corridors only

incorporating travel-time analysis instead of simple distance buffers

integrating gas stations, truck stops, and EV charging stations

using network analysis for more realistic route-based accessibility

including traffic volume or AADT datasets

publishing results as an interactive web map

adding notebooks for exploratory analysis and summary statistics

incorporating temporal comparisons between collection years

How to Run

Install dependencies:

pip install -r requirements.txt

Run the full pipeline:

python run_pipeline.py

This will automatically:

Collect restaurant locations from OpenStreetMap

Collect interstate exit locations

Run corridor accessibility analysis

Run nearest-distance analysis

Run food-desert detection

Outputs will be written to the data/ and outputs/ directories.

Requirements

Example requirements.txt:

pandas
requests
geopandas
shapely
fiona
pyproj
Author

Kenneth Struck
Master of Geoscience – Geographic Information Science & Technology
Texas A&M University

Focus Areas:
GIS • Python • Spatial Analytics • Transportation Geography

Portfolio Purpose

This repository is intended to showcase:

graduate-level GIS research design

Python-based geospatial data collection

practical transportation accessibility analysis

reproducible workflows for real-world geospatial projects

It is designed to support applications for:

GIS analyst roles

transportation and infrastructure GIS roles

spatial data engineering roles

graduate research opportunities


geospatial consulting and applied GIS work
