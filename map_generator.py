#!/usr/bin/env python3
"""
GeoBucket Site Mapper
Reads a CSV of sites with coordinates and bucket tags, computes region convex hulls,
and generates a premium dark-themed zoomable HTML map with multi-dimensional viewing
(bucket, status, complexity).
"""

import os
import sys
import json
import csv
import argparse

DEFAULT_CONFIG = {
    "theme": "dark",
    "tile_provider": "esri",
    "zone_buffer_radius_km": 40,
    "prevent_overlaps": False,
    "show_bucket_boundaries": True,
    "default_view": "bucket",
    "html_title": "GeoBucket Site Explorer",
    "sidebar_title": "GeoBucket Explorer",
    "sidebar_subtitle": "Interactive site planner & geographic regions",
    "label_total_sites": "Total Sites",
    "label_buckets": "Buckets",
    "label_status": "Status",
    "label_complexity": "Complexity",
    "search_placeholder": "Search sites, regions, status or complexity...",
    "status_color_scheme": "default",
    "complexity_color_scheme": "default",
    "bucket_color_scheme": "default",
    "color_schemes": {
        "status": {
            "default": {
                "Not started": "#94a3b8",
                "in progress": "#3b82f6",
                "complete": "#10b981"
            },
            "traffic_light": {
                "Not started": "#ef4444",
                "in progress": "#f59e0b",
                "complete": "#10b981"
            },
            "neon": {
                "Not started": "#64748b",
                "in progress": "#06b6d4",
                "complete": "#a855f7"
            }
        },
        "complexity": {
            "default": {
                "small": "#10b981",
                "medium": "#f59e0b",
                "large": "#ef4444"
            },
            "cool": {
                "small": "#38bdf8",
                "medium": "#818cf8",
                "large": "#c084fc"
            },
            "warm": {
                "small": "#fde047",
                "medium": "#fb923c",
                "large": "#f43f5e"
            }
        }
    },
    "bucket_colors": {},
    "status_colors": {},
    "complexity_colors": {},
    "default_colors": [
        "#ff4b5c", # Coral/Pink
        "#a855f7", # Violet Purple
        "#06b6d4", # Cyan
        "#10b981", # Emerald
        "#f59e0b", # Amber/Gold
        "#3b82f6", # Blue
        "#ec4899", # Deep Pink
        "#f97316", # Orange
        "#14b8a6", # Teal
        "#6366f1", # Indigo
    ]
}


def hsl_to_hex(h, s, l):
    """
    Converts HSL color to HEX string.
    h: hue (0-360), s: saturation (0-1), l: lightness (0-1)
    """
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2
    
    if 0 <= h < 60:
        r, g, b = c, x, 0
    elif 60 <= h < 120:
        r, g, b = x, c, 0
    elif 120 <= h < 180:
        r, g, b = 0, c, x
    elif 180 <= h < 240:
        r, g, b = 0, x, c
    elif 240 <= h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
        
    r_hex = hex(int((r + m) * 255))[2:].zfill(2)
    g_hex = hex(int((g + m) * 255))[2:].zfill(2)
    b_hex = hex(int((b + m) * 255))[2:].zfill(2)
    
    return f"#{r_hex}{g_hex}{b_hex}"


def assign_category_colors(dim_name, values, config):
    """
    Assigns colors to category values (bucket, status, complexity).
    Resolution priority:
    1. Direct dimension color map (e.g., config['status_colors'], config['complexity_colors'], config['bucket_colors'])
    2. Selected color scheme from config['color_schemes'][dim_name][selected_scheme]
    3. Built-in defaults in DEFAULT_CONFIG
    4. Preset default_colors
    5. Dynamic Golden Ratio HSL generation
    Matches keys case-insensitively when finding configured colors.
    """
    preset_colors = config.get("default_colors", DEFAULT_CONFIG["default_colors"])
    direct_colors = config.get(f"{dim_name}_colors", {})
    
    # Check scheme selection
    scheme_name = config.get(f"{dim_name}_color_scheme", "default")
    scheme_colors = {}
    
    # Check in user config color_schemes first, then fallback to DEFAULT_CONFIG color_schemes
    user_schemes = config.get("color_schemes", {})
    default_schemes = DEFAULT_CONFIG.get("color_schemes", {})
    
    dim_schemes = {}
    if isinstance(user_schemes, dict) and dim_name in user_schemes:
        dim_schemes = user_schemes[dim_name]
    elif isinstance(default_schemes, dict) and dim_name in default_schemes:
        dim_schemes = default_schemes[dim_name]
        
    if isinstance(dim_schemes, dict):
        scheme_colors = dim_schemes.get(scheme_name, {}) or dim_schemes.get("default", {})
        
    # Combine scheme colors with direct overrides (direct takes priority)
    combined_configured = {}
    if isinstance(scheme_colors, dict):
        combined_configured.update(scheme_colors)
    if isinstance(direct_colors, dict):
        combined_configured.update(direct_colors)
        
    # Build lower-case lookup map for case-insensitive matching
    ci_lookup = {k.strip().lower(): v for k, v in combined_configured.items() if isinstance(k, str)}
    
    assigned_colors = {}
    remaining_values = []
    
    for val in sorted(values):
        val_str = str(val).strip()
        val_lower = val_str.lower()
        if val_str in combined_configured:
            assigned_colors[val] = combined_configured[val_str]
        elif val_lower in ci_lookup:
            assigned_colors[val] = ci_lookup[val_lower]
        else:
            remaining_values.append(val)
            
    # Assign preset colors to remaining values, avoiding colors already used
    used_colors = set(assigned_colors.values())
    available_presets = [c for c in preset_colors if c not in used_colors]
    
    preset_idx = 0
    for val in remaining_values:
        if preset_idx < len(available_presets):
            assigned_colors[val] = available_presets[preset_idx]
            preset_idx += 1
        elif preset_idx < len(preset_colors):
            assigned_colors[val] = preset_colors[preset_idx - len(available_presets)]
            preset_idx += 1
        else:
            # Generate HSL dynamically using golden ratio spacing
            i = len(assigned_colors)
            hue = (i * 137.5) % 360
            assigned_colors[val] = hsl_to_hex(hue, 0.85, 0.6)
            
    return assigned_colors


def assign_bucket_colors(buckets, config):
    """Backwards-compatible wrapper for assigning bucket colors."""
    return assign_category_colors("bucket", buckets, config)


def load_config(config_path=None):
    """
    Loads config from the specified path, or searches default locations:
    1. The path provided via CLI.
    2. config.json in the current working directory.
    3. config.json in the same directory as this script.
    """
    config = json.loads(json.dumps(DEFAULT_CONFIG)) # Deep copy default
    loaded_path = None
    
    if config_path:
        if os.path.exists(config_path):
            loaded_path = config_path
        else:
            print(f"Error: Specified config file not found: {config_path}", file=sys.stderr)
            sys.exit(1)
    else:
        # Search defaults
        cwd_config = "config.json"
        script_dir = os.path.dirname(os.path.realpath(__file__))
        script_config = os.path.join(script_dir, "config.json")
        
        if os.path.exists(cwd_config):
            loaded_path = cwd_config
        elif os.path.exists(script_config):
            loaded_path = script_config
            
    if loaded_path:
        print(f"Loading configuration from: {loaded_path}")
        try:
            with open(loaded_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                
                # Deep merge config values
                def deep_update(d, u):
                    for k, v in u.items():
                        if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                            deep_update(d[k], v)
                        else:
                            d[k] = v
                    return d
                    
                deep_update(config, user_config)
        except Exception as e:
            print(f"Warning: Failed to load config at {loaded_path}: {e}", file=sys.stderr)
            
    return config


def compute_convex_hull(coords):
    """
    Computes the convex hull of a list of (lat, lon) coordinates.
    Converts to (x, y) where x=lon and y=lat for the algorithm.
    Returns: (list of [lat, lon], hull_type_string)
    """
    # Remove duplicates
    unique_coords = sorted(list(set(coords)), key=lambda c: (c[1], c[0])) # Sort by Lon (x) then Lat (y)
    
    n = len(unique_coords)
    if n == 0:
        return [], "none"
    if n == 1:
        return [[unique_coords[0][0], unique_coords[0][1]]], "circle"
    if n == 2:
        return [[c[0], c[1]] for c in unique_coords], "polyline"
        
    def cross(o, a, b):
        # 2D cross product of OA and OB vectors: (A_x - O_x) * (B_y - O_y) - (A_y - O_y) * (B_x - O_x)
        # Coordinates: [lat, lon] -> [y, x]
        # x is index 1 (lon), y is index 0 (lat)
        return (a[1] - o[1]) * (b[0] - o[0]) - (a[0] - o[0]) * (b[1] - o[1])
        
    # Build lower hull
    lower = []
    for p in unique_coords:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
        
    # Build upper hull
    upper = []
    for p in reversed(unique_coords):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
        
    # Concatenate lower and upper hulls (excluding the last element of each because it is repeated)
    hull = lower[:-1] + upper[:-1]
    
    # Check if collinearity reduced the hull size
    if len(hull) <= 1:
        return [[c[0], c[1]] for c in unique_coords[:1]], "circle"
    elif len(hull) == 2:
        return [[c[0], c[1]] for c in hull], "polyline"
    else:
        return [[c[0], c[1]] for c in hull], "polygon"


def parse_csv(csv_path):
    """
    Parses a CSV file for site details. Resolves column headers dynamically.
    Supports site name, latitude, longitude, bucket tag, status, and complexity.
    """
    sites = []
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
    # Probe for the correct encoding
    encoding = None
    encodings = ['utf-8-sig', 'cp1252', 'utf-16']
    for enc in encodings:
        try:
            with open(csv_path, 'r', encoding=enc) as f:
                f.read()
            encoding = enc
            break
        except UnicodeDecodeError:
            continue
            
    if encoding is None:
        encoding = 'utf-8-sig'
        
    with open(csv_path, 'r', encoding=encoding, errors='replace') as f:
        # Detect delimiter/format or fall back to standard reader
        try:
            dialect = csv.Sniffer().sniff(f.read(1024))
            f.seek(0)
            reader = csv.reader(f, dialect)
        except Exception:
            f.seek(0)
            reader = csv.reader(f)
            
        try:
            headers = next(reader)
        except StopIteration:
            raise ValueError("CSV file is empty.")
            
        clean_headers = [h.strip().lower() for h in headers]
        
        # Column Synonyms mapping
        name_synonyms = {"site name", "site", "name", "location", "label", "title", "id"}
        lat_synonyms = {"latitude", "lat", "y", "latitude_deg"}
        lon_synonyms = {"longitude", "lon", "lng", "x", "longitude_deg"}
        bucket_synonyms = {"bucket tag", "bucket", "group", "category", "tag", "region", "bucket_tag"}
        status_synonyms = {"status", "state", "progress", "workflow_status"}
        complexity_synonyms = {"complexity", "size", "difficulty", "effort", "scale"}
        
        name_idx = next((i for i, h in enumerate(clean_headers) if h in name_synonyms), None)
        lat_idx = next((i for i, h in enumerate(clean_headers) if h in lat_synonyms), None)
        lon_idx = next((i for i, h in enumerate(clean_headers) if h in lon_synonyms), None)
        bucket_idx = next((i for i, h in enumerate(clean_headers) if h in bucket_synonyms), None)
        status_idx = next((i for i, h in enumerate(clean_headers) if h in status_synonyms), None)
        complexity_idx = next((i for i, h in enumerate(clean_headers) if h in complexity_synonyms), None)
        
        if name_idx is None:
            raise ValueError(f"Could not identify site 'name' column. Header was: {headers}")
        if lat_idx is None:
            raise ValueError(f"Could not identify 'latitude' column. Header was: {headers}")
        if lon_idx is None:
            raise ValueError(f"Could not identify 'longitude' column. Header was: {headers}")
        if bucket_idx is None:
            raise ValueError(f"Could not identify 'bucket' tag column. Header was: {headers}")
            
        for line_num, row in enumerate(reader, start=2):
            if not row or all(val.strip() == '' for val in row):
                continue
                
            max_core_idx = max(name_idx, lat_idx, lon_idx, bucket_idx)
            if len(row) <= max_core_idx:
                print(f"Warning: Line {line_num} does not have enough columns (expected at least {max_core_idx+1}). Skipping.")
                continue
                
            name = row[name_idx].strip()
            lat_str = row[lat_idx].strip()
            lon_str = row[lon_idx].strip()
            bucket = row[bucket_idx].strip()
            
            # Optional status and complexity parsing with sensible fallbacks
            status = row[status_idx].strip() if (status_idx is not None and len(row) > status_idx) else "Not started"
            if not status:
                status = "Not started"
                
            complexity = row[complexity_idx].strip() if (complexity_idx is not None and len(row) > complexity_idx) else "medium"
            if not complexity:
                complexity = "medium"
            
            if not name or not lat_str or not lon_str or not bucket:
                print(f"Warning: Line {line_num} has empty essential fields. Skipping.")
                continue
                
            try:
                lat = float(lat_str)
                lon = float(lon_str)
            except ValueError:
                print(f"Warning: Line {line_num} has invalid coordinates: lat='{lat_str}', lon='{lon_str}'. Skipping.")
                continue
                
            sites.append({
                "name": name,
                "lat": lat,
                "lon": lon,
                "bucket": bucket,
                "status": status,
                "complexity": complexity
            })
            
    return sites


def main():
    parser = argparse.ArgumentParser(description="Generate interactive multi-dimensional GeoBucket maps from CSV.")
    parser.add_argument("csv_file", help="Path to input CSV file")
    parser.add_argument("-o", "--output", help="Path to output HTML file (default: same directory as CSV, named map.html)")
    parser.add_argument("-t", "--template", help="Path to custom map HTML template")
    parser.add_argument("-c", "--config", help="Path to configuration JSON file")
    parser.add_argument("-v", "--view", choices=["bucket", "status", "complexity"], help="Default active view (bucket, status, complexity)")
    boundary_group = parser.add_mutually_exclusive_group()
    boundary_group.add_argument(
        "--boundaries",
        dest="show_bucket_boundaries",
        action="store_true",
        default=None,
        help="Show dashed region boundary lines around categories"
    )
    boundary_group.add_argument(
        "--no-boundaries",
        "--hide-boundaries",
        dest="show_bucket_boundaries",
        action="store_false",
        help="Hide dashed region boundary lines around categories (show colored icons only)"
    )
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # CLI arguments override config
    if args.view:
        config["default_view"] = args.view
    if args.show_bucket_boundaries is not None:
        config["show_bucket_boundaries"] = args.show_bucket_boundaries
    elif "show_bucket_boundaries" not in config and "show_boundaries" in config:
        config["show_bucket_boundaries"] = config["show_boundaries"]

    show_boundaries = config.get("show_bucket_boundaries", True)
    if show_boundaries:
        print("Region boundaries: enabled (dashed boundary lines will be shown)")
    else:
        print("Region boundaries: disabled (showing colored icons only)")
    
    # 1. Parse CSV
    try:
        sites = parse_csv(args.csv_file)
    except Exception as e:
        print(f"Error parsing CSV: {e}", file=sys.stderr)
        sys.exit(1)
        
    if not sites:
        print("No valid sites found in the CSV file.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Loaded {len(sites)} sites from {args.csv_file}")
    
    # 2. Process groups, colors, and convex hulls for all 3 dimensions
    dimensions = ["bucket", "status", "complexity"]
    groups_data = {}
    
    for dim in dimensions:
        dim_groups = {}
        for site in sites:
            val = site.get(dim) or "Unknown"
            if val not in dim_groups:
                dim_groups[val] = []
            dim_groups[val].append((site["lat"], site["lon"]))
            
        dim_colors = assign_category_colors(dim, dim_groups.keys(), config)
        
        groups_data[dim] = {}
        print(f"\nProcessing dimension '{dim}': {len(dim_groups)} groups")
        for val, coords in dim_groups.items():
            hull, hull_type = compute_convex_hull(coords)
            groups_data[dim][val] = {
                "color": dim_colors[val],
                "hull": hull,
                "hull_type": hull_type
            }
            print(f"  [{dim}] '{val}' ({dim_colors[val]}): {len(coords)} sites -> Region style '{hull_type}' ({len(hull)} hull points)")
            
    # For backward compatibility
    bucket_data = groups_data["bucket"]
        
    # 3. Load HTML Template
    template_content = None
    script_dir = os.path.dirname(os.path.realpath(__file__))
    
    # Check template paths
    template_paths = []
    if args.template:
        template_paths.append(args.template)
    template_paths.append(os.path.join(script_dir, "map_template.html"))
    
    for path in template_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as tf:
                    template_content = tf.read()
                print(f"\nUsing map template from: {path}")
                break
            except Exception as e:
                print(f"Warning: Failed to read template at {path}: {e}")
                
    if template_content is None:
        sys.exit("Critical Error: Could not load map_template.html. Please ensure it is present in the script directory.")
        
    # 4. Inject JSON data and custom text into template
    site_data_json = json.dumps(sites, indent=2)
    bucket_data_json = json.dumps(bucket_data, indent=2)
    groups_data_json = json.dumps(groups_data, indent=2)
    config_json = json.dumps(config, indent=2)
    
    theme_class = "light-mode" if config.get("theme") == "light" else ""
    default_view = config.get("default_view", "bucket")
    
    output_html = template_content
    output_html = output_html.replace("{{SITE_DATA_JSON}}", site_data_json)
    output_html = output_html.replace("{{BUCKET_DATA_JSON}}", bucket_data_json)
    output_html = output_html.replace("{{GROUPS_DATA_JSON}}", groups_data_json)
    output_html = output_html.replace("{{CONFIG_JSON}}", config_json)
    output_html = output_html.replace("{{THEME_CLASS}}", theme_class)
    output_html = output_html.replace("{{DEFAULT_VIEW}}", default_view)
    output_html = output_html.replace("{{MAP_TITLE}}", config.get("html_title", "GeoBucket Site Explorer"))
    output_html = output_html.replace("{{SIDEBAR_TITLE}}", config.get("sidebar_title", "GeoBucket Explorer"))
    output_html = output_html.replace("{{MAP_SUBTITLE}}", config.get("sidebar_subtitle", ""))
    output_html = output_html.replace("{{LABEL_TOTAL_SITES}}", config.get("label_total_sites", "Total Sites"))
    output_html = output_html.replace("{{LABEL_BUCKETS}}", config.get("label_buckets", "Buckets"))
    output_html = output_html.replace("{{LABEL_STATUS}}", config.get("label_status", "Status"))
    output_html = output_html.replace("{{LABEL_COMPLEXITY}}", config.get("label_complexity", "Complexity"))
    output_html = output_html.replace("{{LABEL_BUCKET_BTN}}", config.get("label_bucket_btn") or config.get("label_buckets", "Bucket"))
    output_html = output_html.replace("{{LABEL_STATUS_BTN}}", config.get("label_status_btn") or config.get("label_status", "Status"))
    output_html = output_html.replace("{{LABEL_COMPLEXITY_BTN}}", config.get("label_complexity_btn") or config.get("label_complexity", "Complexity"))
    output_html = output_html.replace("{{SEARCH_PLACEHOLDER}}", config.get("search_placeholder", "Search sites..."))
    
    # 5. Write Output HTML
    if args.output:
        out_path = args.output
    else:
        out_dir = os.path.dirname(os.path.realpath(args.csv_file))
        out_path = os.path.join(out_dir, "map.html")
        
    try:
        with open(out_path, 'w', encoding='utf-8') as out_file:
            out_file.write(output_html)
        print(f"Success! Interactive map generated at: {os.path.realpath(out_path)}")
    except Exception as e:
        print(f"Error writing output HTML: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
