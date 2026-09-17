# GeoBucket Site Mapper 🗺️

A Python tool that turns CSV site data with coordinates into standalone, interactive Leaflet web maps. Supports multi-dimensional viewing by **Bucket** (region/tag), **Status**, and **Complexity**, with dynamic color schemes, search filtering, and optional convex hull boundary overlays.

---

## ✨ Features

- **Multi-Dimensional View Selector**: Switch dynamically between **Bucket**, **Status**, and **Complexity** using the selector on the map canvas or sidebar. Markers and cards update instantly without reloading the page.
- **Glassmorphic Floating Sidebar**:
  - Real-time HUD showing visible sites and active category counts.
  - Interactive search bar filtering across names, buckets, statuses, and complexities.
  - Expandable category cards with individual visibility toggle switches (show/hide specific groups).
  - Click any site in the sidebar to smoothly pan the camera and open its popup.
- **Rich Popups**: Displays site name, coordinates, and colored badges for Bucket, Status, and Complexity, with the active view highlighted.
- **Region Boundaries & Convex Hulls**: Calculates convex hulls for groups with optional Voronoi buffering to display clean, non-overlapping boundary zones.
- **Configurable Colour Schemes**: Supports named palettes (`traffic_light`, `neon`, `cool`, `warm`) and direct color overrides in `config.json` with automatic fallback to dynamic Golden Ratio HSL generation.
- **Zero External Backend**: Compiles into a single, self-contained HTML file (`map.html`) that can be opened directly in any browser or hosted statically.

---

## 🚀 Quick Start

### 1. Requirements

- Python 3.7+ (no third-party Python packages required; uses standard libraries `json`, `csv`, `os`, `sys`, `argparse`).
- Modern web browser with internet access (to load Leaflet and map tiles via CDN).

### 2. Generate the Map

Run the generator against the sample CSV:

```bash
python3 map_generator.py sample_sites.csv
```

Open `map.html` in your browser:

```bash
# On Linux (e.g., xdg-open)
xdg-open map.html

# On macOS
open map.html
```

---

## 📂 CSV Data Format

The input CSV should include coordinates and category tags. Column headers are flexible (case-insensitive with synonym matching):

| Column | Accepted Synonyms | Example Values |
| :--- | :--- | :--- |
| **Site Name** | `site name`, `site`, `name`, `location`, `label`, `title` | `Mount Fuji`, `Colosseum` |
| **Latitude** | `latitude`, `lat`, `y`, `latitude_deg` | `35.3606`, `-13.1631` |
| **Longitude** | `longitude`, `lon`, `lng`, `x`, `longitude_deg` | `138.7274`, `-72.5450` |
| **Bucket Tag** | `bucket tag`, `bucket`, `group`, `category`, `tag`, `region` | `Pacific Ring of Fire`, `Mediterranean Antiquity` |
| **Status** *(optional)* | `status`, `state`, `progress`, `workflow_status` | `Not started`, `in progress`, `complete` |
| **Complexity** *(optional)* | `complexity`, `size`, `difficulty`, `effort`, `scale` | `small`, `medium`, `large` |

### Sample CSV (`sample_sites.csv`)

```csv
site name,latitude,longitude,bucket tag,status,complexity
Mount Fuji,35.3606,138.7274,Pacific Ring of Fire,complete,large
Mount Ruapehu,-39.2792,175.5639,Pacific Ring of Fire,in progress,medium
Mount Rainier,46.8523,-121.7603,Pacific Ring of Fire,Not started,large
Colosseum,41.8902,12.4922,Mediterranean Antiquity,complete,small
```

> **Note**: You can define custom values for status and complexity (e.g. `Blocked`, `Under review`, or `XS`, `S`, `M`, `L`, `XL`). The generator dynamically groups whatever unique values exist in your data.

---

## ⚙️ Configuration (`config.json`)

Customize themes, labels, boundary display, and color schemes in `config.json`:

```json
{
  "theme": "light",
  "tile_provider": "esri",
  "show_bucket_boundaries": false,
  "default_view": "bucket",
  "label_total_sites": "Total Locations",
  "label_buckets": "Regions",
  "label_status": "Statuses",
  "label_complexity": "Complexities",
  "search_placeholder": "Search sites, regions, status or complexity...",
  "status_color_scheme": "default",
  "complexity_color_scheme": "default",
  "status_colors": {
    "Not started": "#94a3b8",
    "in progress": "#3b82f6",
    "complete": "#10b981"
  },
  "complexity_colors": {
    "small": "#10b981",
    "medium": "#f59e0b",
    "large": "#ef4444"
  }
}
```

### Tile Providers

Set `"tile_provider"` in `config.json` to:
- `"esri"`: Minimalist light/dark gray canvas matching the theme (*default*).
- `"osm"`: OpenStreetMap standard tiles.
- `"esri_topo"`: Esri World Topographic map.
- `"esri_imagery"`: Esri Satellite World Imagery.

### Colour Scheme Options

1. **Direct Overrides**: Set hex colors directly in `bucket_colors`, `status_colors`, or `complexity_colors`.
2. **Named Schemes**: Set `status_color_scheme` or `complexity_color_scheme` to any scheme defined under `color_schemes`:
   - Status presets: `"default"`, `"traffic_light"`, `"neon"`
   - Complexity presets: `"default"`, `"cool"`, `"warm"`

---

## 🛠️ CLI Options

```
usage: map_generator.py [-h] [-o OUTPUT] [-t TEMPLATE] [-c CONFIG]
                        [-v {bucket,status,complexity}]
                        [--boundaries | --no-boundaries]
                        csv_file

Generate interactive multi-dimensional GeoBucket maps from CSV.

positional arguments:
  csv_file              Path to input CSV file

options:
  -h, --help            Show help message and exit
  -o, --output OUTPUT   Path to output HTML file (default: map.html)
  -t, --template PATH   Path to custom map HTML template
  -c, --config PATH     Path to configuration JSON file
  -v, --view VIEW       Default active view (bucket, status, complexity)
  --boundaries          Show dashed region boundary lines around categories
  --no-boundaries       Hide dashed region boundary lines (colored icons only)
```

### Examples

Generate map with Status as default view and region boundaries enabled:
```bash
python3 map_generator.py sample_sites.csv --view status --boundaries
```

Generate using a custom configuration file and custom output path:
```bash
python3 map_generator.py sites.csv -c my_config.json -o my_custom_map.html
```

---

## 📁 Repository Structure

```
site_mapper/
├── config.json          # Map settings, labels, and color palettes
├── map.html             # Generated standalone interactive map
├── map_generator.py     # Python CLI parser and HTML builder
├── map_template.html    # Base Leaflet + Turf.js HTML/CSS/JS template
├── sample_sites.csv     # Sample CSV dataset with coordinates, tags, and status
└── README.md            # Documentation
```
