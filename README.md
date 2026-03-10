# Interstate Food Accessibility Analysis (Python + GIS)

## Overview

This project analyzes the spatial accessibility of food services along major **east–west interstate transportation corridors** in the United States using **Python-based geospatial data engineering and GIS analysis**.

The workflow automatically collects restaurant and interstate exit data from **OpenStreetMap** using the **Overpass API**, then performs spatial analysis to evaluate how easily travelers can access food services along long-distance interstate routes.

This repository is designed to demonstrate a **reproducible geospatial data pipeline** that integrates:

- Python data collection
- spatial data engineering
- GIS-based corridor analysis
- transportation accessibility modeling
- automated geospatial workflows

The project functions as both a **graduate-level GIS research project** and a **professional portfolio demonstration** of Python and geospatial analysis skills.

---

# Research Questions

### Primary Question

How accessible are food services to travelers along major interstate transportation corridors in the United States?

### Supporting Questions

- Which interstate corridors have the highest density of food services?
- Which interstate exits provide reliable access to nearby restaurants?
- Where are the longest travel gaps between accessible food-service locations?
- Are there geographic regions where travelers encounter **food-service deserts**?
- How can automated geospatial pipelines support long-term accessibility monitoring?

---

# Study Area

This project focuses on major **east–west interstate highways** across the continental United States:

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
- interstate travel
- economic connectivity

Future expansions may include **north–south interstates** and additional transportation infrastructure layers.

---

# Project Goals

The project was designed with four primary goals:

1. Build a **national restaurant dataset** using automated OpenStreetMap collection.
2. Build a matching **national interstate exit dataset**.
3. Analyze food accessibility along interstate corridors using spatial GIS analysis.
4. Create a **reproducible pipeline** that can be rerun in future years to detect new locations.

---

# Data Sources

## Interstate Highways

Interstate highway geometries are sourced from:

- **U.S. Census TIGER/Line datasets**

These datasets provide the base network for corridor analysis.

---

## Interstate Exits

Interstate exit locations are collected from **OpenStreetMap** using the Overpass API.

Primary query feature:

```
highway = motorway_junction
```

These nodes represent official motorway or interstate exits.

---

## Restaurant Locations

Restaurant locations are collected from **OpenStreetMap** using:

```
amenity = fast_food
amenity = restaurant
```

This captures a broad range of food-service locations including:

- fast-food chains
- quick-service restaurants
- independent restaurants
- highway-adjacent diners

---

# Data Collection Design

Instead of attempting a single nationwide query, the project collects data **state-by-state**.

This design improves reliability and scalability because it:

- avoids large API timeouts
- allows incremental dataset refresh
- preserves raw API responses
- simplifies debugging and updates
- enables long-term dataset maintenance

Each collector script performs the following workflow:

1. Query OpenStreetMap for a single state.
2. Save the raw JSON response.
3. Convert the response into a cleaned CSV.
4. Store the state dataset.
5. Merge all state datasets into a national dataset.

---

# Incremental Dataset Refresh

The project includes a **refresh log system** that tracks when each state dataset was last collected.

When the pipeline is rerun later:

- recently refreshed states can be skipped
- older states can be refreshed
- newly added restaurants or exits are incorporated

This allows the project to function as a **living dataset** rather than a one-time snapshot.

---

# Methodology

## 1. Automated Data Collection

Python scripts collect restaurant and interstate exit data from OpenStreetMap using the Overpass API.

This step creates the base national datasets.

---

## 2. Raw Data Archiving

Each API response is saved as raw JSON to ensure:

- reproducibility
- traceability
- debugging capability
- transparency of source data

---

## 3. Data Cleaning and Standardization

Collected data is standardized into consistent CSV datasets.

Typical cleaning tasks include:

- removing duplicate features
- validating coordinates
- standardizing text attributes
- constructing display names
- preserving the newest version of OSM features

---

## 4. Interstate Corridor Analysis

Major interstate highways are buffered by **2 miles** to represent a realistic service-access zone.

Restaurants inside these buffers are classified as **accessible from the interstate corridor**.

---

## 5. Exit Accessibility Analysis

Interstate exits are buffered by **2 miles** to identify food services reachable shortly after leaving the highway.

This distinguishes:

- corridor-level accessibility
- exit-based accessibility

---

## 6. Distance Analysis

The distance module calculates the nearest distance from each restaurant to:

- the nearest interstate corridor
- the nearest interstate exit

Outputs include:

- straight-line distance measures
- accessibility rankings

---

## 7. Travel Gap Analysis

Distances between accessible restaurants along interstate corridors are evaluated.

Large distances between food-service locations indicate **service gaps for travelers**.

---

## 8. Food Desert Detection

The project identifies long interstate segments where food access is limited.

Restaurants accessible from the corridor are projected onto each interstate line.

Segments exceeding **50 miles** between food-service opportunities are classified as potential:

> **Food deserts for interstate travelers**

---

## 9. Network-Based Accessibility Analysis

A network analysis module uses the **OpenStreetMap drivable road network** to calculate real travel distances.

This step estimates:

- drive distance to nearest restaurant
- drive time to nearest restaurant
- exits with poor real-world accessibility

This provides more realistic results than straight-line distance alone.

---

## 10. GIS Visualization

Outputs are visualized in **QGIS** using:

- corridor maps
- exit accessibility maps
- restaurant density heatmaps
- food desert gap maps
- drive-distance accessibility maps

---

# Scripts

### collect_osm_restaurants_by_state.py

Builds the national restaurant dataset from OpenStreetMap.

Outputs:

- per-state restaurant CSV files
- raw JSON responses
- national `restaurants.csv`
- refresh logs

---

### collect_interstate_exits_by_state.py

Builds the national interstate exit dataset.

Outputs:

- per-state exit CSV files
- raw JSON responses
- national `interstate_exits.csv`
- refresh logs

---

### corridor_analysis.py

Performs corridor-based accessibility analysis.

Responsibilities include:

- selecting major interstate routes
- creating corridor buffers
- identifying accessible restaurants
- generating summary tables

---

### distance_analysis.py

Calculates nearest distances between restaurants and transportation infrastructure.

Outputs include:

- distance to nearest interstate
- distance to nearest exit

---

### food_desert_detection.py

Identifies long interstate segments with limited food access.

Outputs:

- gap segment maps
- desert segment classifications
- interstate gap statistics

---

### network_access_analysis.py

Performs network-based accessibility analysis using a drivable road network.

Outputs:

- nearest restaurant by driving route
- drive distance and travel time from exits
- network-based food-desert indicators

---

### run_pipeline.py

Runs the entire workflow automatically.

---

# Repository Structure

```
interstate-food-accessibility-gis
│
├── data
│   ├── restaurants.csv
│   ├── interstate_exits.csv
│   ├── state_refresh_log.csv
│   ├── state_exit_refresh_log.csv
│
│   ├── states
│   ├── state_exits
│   ├── raw_osm_states
│   └── raw_osm_state_exits
│
├── scripts
│   ├── collect_osm_restaurants_by_state.py
│   ├── collect_interstate_exits_by_state.py
│   ├── corridor_analysis.py
│   ├── distance_analysis.py
│   ├── food_desert_detection.py
│   ├── network_access_analysis.py
│   └── clean_data.py
│
├── qgis
│   └── interstate_analysis.qgz
│
├── outputs
│
├── run_pipeline.py
├── requirements.txt
└── README.md
```

---

# Example Outputs

The pipeline generates multiple datasets including:

- restaurants near interstate corridors
- restaurants near interstate exits
- corridor accessibility summaries
- exit accessibility summaries
- restaurant distance analysis
- interstate food desert segments
- network-based accessibility results

These outputs can be used directly in **QGIS** for visualization and mapping.

---

# Tools Used

### Python

- pandas
- requests
- geopandas
- shapely
- networkx
- osmnx
- pyproj
- fiona

### GIS

- QGIS

### Data Sources

- OpenStreetMap Overpass API
- U.S. Census TIGER/Line

---

# Skills Demonstrated

This project demonstrates expertise in:

### Geospatial Data Engineering

- automated API data collection
- scalable spatial pipelines
- incremental dataset refresh workflows

### GIS Analysis

- corridor buffering
- spatial joins
- density analysis
- nearest-distance modeling
- network-based accessibility analysis

### Research Design

- transportation geography
- service accessibility modeling
- infrastructure support analysis

---

# Applications

This analysis is relevant to:

- transportation planning
- logistics network analysis
- truck stop planning
- retail site selection
- tourism infrastructure planning
- EV charging network placement
- roadside service accessibility studies

---

# Running the Project

Install dependencies:

```
pip install -r requirements.txt
```

Run the full pipeline:

```
python run_pipeline.py
```

The pipeline will automatically:

1. Collect restaurant locations
2. Collect interstate exit locations
3. Run corridor accessibility analysis
4. Run distance analysis
5. Detect food desert segments
6. Perform network accessibility analysis

Outputs will be written to the **data** and **outputs** directories.

---

# Future Improvements

Potential project expansions include:

- adding north–south interstates
- incorporating traffic volume datasets
- performing full network routing analysis
- integrating gas stations and truck stops
- adding EV charging infrastructure analysis
- publishing interactive web maps
- building dashboards for accessibility monitoring

---

# Author

**Kenneth Struck**  
Master of Geoscience — Geographic Information Science & Technology  
Texas A&M University

Focus Areas:

GIS • Python • Spatial Analytics • Transportation Geography

---

# Portfolio Purpose

This repository demonstrates the ability to design and implement a **full geospatial analysis pipeline** integrating:

- automated spatial data collection
- reproducible GIS workflows
- transportation accessibility analysis
- Python-based geospatial engineering

The project supports applications for:

- GIS Analyst roles
- Transportation GIS positions
- Spatial Data Engineering roles
- Geospatial research opportunities