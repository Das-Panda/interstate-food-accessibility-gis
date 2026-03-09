# Interstate Food Accessibility Analysis (Python + GIS)

## Overview

This project analyzes the spatial accessibility of quick-service restaurants along major interstate transportation corridors in the United States using **Python-based geospatial data collection and QGIS spatial analysis**.

Restaurant locations are automatically collected from **OpenStreetMap using the Overpass API**, allowing the creation of a scalable national dataset of food services. The analysis evaluates how easily travelers can access food services while driving long distances across major interstate routes.

This project demonstrates how **Python data pipelines and GIS spatial analysis can be combined to study real-world accessibility problems in transportation geography.**

---

## Research Questions

Primary Question:

How accessible are quick-service restaurants to travelers along major interstate transportation corridors in the United States?

Supporting Questions:

* Which interstate corridors have the highest restaurant density?
* Which interstate exits provide reliable access to food services?
* Where are the longest distances between food service locations?
* Are there geographic regions where travelers encounter **food service deserts**?

---

## Study Area

Major east-west interstate highways across the continental United States:

* I-10
* I-20
* I-30
* I-40
* I-70
* I-80
* I-90

These routes represent major long-distance transportation corridors used for freight movement, tourism, and interstate travel.

---

## Data Sources

### Interstate Highway Data

U.S. Census Bureau **TIGER/Line road datasets**

### Interstate Exit Data

Interstate exit locations are collected from **OpenStreetMap** using the Overpass API.

Feature used:

```
highway = motorway_junction
```

These nodes represent official highway exits.

---

### Restaurant Location Data

Restaurant locations are automatically collected using **OpenStreetMap's Overpass API**.

Query filters include:

```
amenity = fast_food
amenity = restaurant
```

Each location includes:

* name
* latitude
* longitude
* city
* state
* amenity type
* OpenStreetMap ID

This approach produces a scalable dataset representing thousands of food service locations across the United States.

Output dataset:

```
restaurants.csv
```

---

## Methodology

### 1. Automated Data Collection (Python)

Python scripts retrieve spatial data from OpenStreetMap.

Libraries used:

* requests
* pandas
* geopandas

Datasets generated:

```
restaurants.csv
interstate_exits.csv
```

This approach demonstrates automated geospatial dataset construction.

---

### 2. Data Preparation

Datasets are cleaned and prepared for GIS analysis.

Processing steps include:

* removing duplicate records
* validating coordinate values
* converting CSV files to spatial point layers
* aligning coordinate reference systems

---

### 3. Interstate Corridor Analysis

Major interstate highways are buffered by **2 miles** to represent the approximate distance travelers may drive from an exit to access nearby services.

Restaurants located within this corridor are classified as **accessible from the interstate corridor**.

---

### 4. Exit Accessibility Analysis

Interstate exits are analyzed to determine which exits provide access to nearby restaurants.

A **2-mile buffer around each exit** identifies food services reachable shortly after leaving the highway.

Outputs include:

* exits with nearby food services
* exits lacking nearby food services
* clusters of restaurants near major exits

---

### 5. Density Analysis

Spatial density analysis evaluates clustering of restaurants along interstate corridors.

Methods include:

* Kernel Density Estimation
* restaurant counts per interstate segment
* restaurants per 100 miles of corridor

---

### 6. Travel Gap Analysis

Distances between accessible restaurants along interstate corridors are measured to identify **service gaps for long-distance travelers**.

Segments where the distance between accessible restaurants exceeds **50 miles** are classified as potential **food service deserts**.

These gaps are mapped along interstate routes.

---

## Tools Used

Python

* pandas
* geopandas
* requests

GIS Software

* QGIS

Spatial Data

* OpenStreetMap Overpass API
* U.S. Census TIGER/Line datasets

---

## Repository Structure

```
interstate-food-accessibility-gis
│
├── data
│   ├── restaurants.csv
│   ├── interstate_exits.csv
│   └── interstates.geojson
│
├── scripts
│   ├── collect_osm_restaurants.py
│   ├── collect_interstate_exits.py
│   ├── clean_data.py
│   └── corridor_analysis.py
│
├── qgis
│   └── interstate_analysis.qgz
│
├── outputs
│   ├── corridor_map.png
│   ├── exit_accessibility_map.png
│   └── service_gap_map.png
│
└── README.md
```

---

## Example Outputs

The analysis produces several spatial outputs:

* interstate corridor accessibility maps
* restaurant density heatmaps
* interstate exit accessibility maps
* food service gap visualizations

These outputs illustrate patterns of food accessibility for long-distance travelers across the United States.

---

## Skills Demonstrated

This project demonstrates integration of **Python programming, spatial data engineering, and GIS analysis**.

Key skills include:

* automated geospatial data collection
* API-based dataset creation
* spatial buffering and corridor modeling
* spatial joins and density analysis
* transportation accessibility modeling
* GIS cartography and visualization
* reproducible geospatial workflows

---

## Applications

This type of spatial accessibility analysis is used in:

* transportation planning
* logistics network planning
* truck stop and rest area planning
* retail site selection
* EV charging infrastructure planning
* tourism infrastructure analysis

---

## Future Improvements

Potential extensions include:

* network-based travel distance analysis
* travel time between food service locations
* gas station and EV charger accessibility modeling
* interactive web mapping
* integration with traffic volume datasets

---

## Author

Kenneth Struck
Master of Geoscience – Geographic Information Science & Technology
Texas A&M University

GIS • Python • Spatial Analytics • Transportation Geography
