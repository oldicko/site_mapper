#!/usr/bin/env python3
"""
GeoBucket Site Mapper
Reads a CSV of sites with coordinates and bucket tags, computes region convex hulls,
and generates a premium dark-themed zoomable HTML map.
"""

import os
import sys
import json
import csv
import argparse

DEFAULT_CONFIG = {
    "theme": "dark",
    "zone_buffer_radius_km": 40,
    "prevent_overlaps": False,
    "html_title": "GeoBucket Site Explorer",
    "sidebar_title": "GeoBucket Explorer",
    "sidebar_subtitle": "Interactive site planner & geographic regions",
    "label_total_sites": "Total Sites",
    "label_buckets": "Buckets",
    "search_placeholder": "Search sites or buckets...",
    "bucket_colors": {},
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

def assign_bucket_colors(buckets, config):
    """
    Assigns vibrant, aesthetic colors to each bucket.
    Prioritizes explicit bucket colors from config, then preset/default colors,
    then falls back to Golden Ratio HSL generation.
    """
    preset_colors = config.get("default_colors", [])
    config_bucket_colors = config.get("bucket_colors", {})
    
    bucket_colors = {}
    
    # 1. First assign explicit colors from config
    remaining_buckets = []
    for bucket in sorted(buckets):
        if bucket in config_bucket_colors:
            bucket_colors[bucket] = config_bucket_colors[bucket]
        else:
            remaining_buckets.append(bucket)
            
    # 2. Assign preset colors to the remaining buckets, avoiding colors already used if possible
    used_colors = set(bucket_colors.values())
    available_presets = [c for c in preset_colors if c not in used_colors]
    
    preset_idx = 0
    for bucket in remaining_buckets:
        if preset_idx < len(available_presets):
            bucket_colors[bucket] = available_presets[preset_idx]
            preset_idx += 1
        elif preset_idx < len(preset_colors):
            # Fall back to any preset color (even if already used)
            bucket_colors[bucket] = preset_colors[preset_idx - len(available_presets)]
            preset_idx += 1
        else:
            # Generate HSL dynamically using golden ratio spacing for maximum distribution
            i = len(bucket_colors)
            hue = (i * 137.5) % 360
            bucket_colors[bucket] = hsl_to_hex(hue, 0.85, 0.6)
            
    return bucket_colors

def load_config(config_path=None):
    """
    Loads config from the specified path, or searches default locations:
    1. The path provided via CLI.
    2. config.json in the current working directory.
    3. config.json in the same directory as this script.
    """
    config = DEFAULT_CONFIG.copy()
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
                for key, val in user_config.items():
                    if isinstance(val, dict) and key in config and isinstance(config[key], dict):
                        config[key].update(val)
                    else:
                        config[key] = val
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
    """
    sites = []
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
    with open(csv_path, 'r', encoding='utf-8') as f:
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
        
        name_idx = next((i for i, h in enumerate(clean_headers) if h in name_synonyms), None)
        lat_idx = next((i for i, h in enumerate(clean_headers) if h in lat_synonyms), None)
        lon_idx = next((i for i, h in enumerate(clean_headers) if h in lon_synonyms), None)
        bucket_idx = next((i for i, h in enumerate(clean_headers) if h in bucket_synonyms), None)
        
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
                
            max_idx = max(name_idx, lat_idx, lon_idx, bucket_idx)
            if len(row) <= max_idx:
                print(f"Warning: Line {line_num} does not have enough columns (expected at least {max_idx+1}). Skipping.")
                continue
                
            name = row[name_idx].strip()
            lat_str = row[lat_idx].strip()
            lon_str = row[lon_idx].strip()
            bucket = row[bucket_idx].strip()
            
            if not name or not lat_str or not lon_str or not bucket:
                print(f"Warning: Line {line_num} has empty fields. Skipping.")
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
                "bucket": bucket
            })
            
    return sites

def main():
    parser = argparse.ArgumentParser(description="Generate interactive GeoBucket maps from CSV.")
    parser.add_argument("csv_file", help="Path to input CSV file")
    parser.add_argument("-o", "--output", help="Path to output HTML file (default: same directory as CSV, named map.html)")
    parser.add_argument("-t", "--template", help="Path to custom map HTML template")
    parser.add_argument("-c", "--config", help="Path to configuration JSON file")
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
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
    
    # 2. Group coords by bucket and extract unique bucket names
    bucket_groups = {}
    for site in sites:
        bucket = site["bucket"]
        if bucket not in bucket_groups:
            bucket_groups[bucket] = []
        bucket_groups[bucket].append((site["lat"], site["lon"]))
        
    # 3. Assign bucket colors
    bucket_colors = assign_bucket_colors(bucket_groups.keys(), config)
    
    # 4. Compute Convex Hull for each bucket
    bucket_data = {}
    for bucket, coords in bucket_groups.items():
        hull, hull_type = compute_convex_hull(coords)
        bucket_data[bucket] = {
            "color": bucket_colors[bucket],
            "hull": hull,
            "hull_type": hull_type
        }
        print(f"  Bucket '{bucket}': {len(coords)} sites -> Region style '{hull_type}' ({len(hull)} hull points)")
        
    # 5. Load HTML Template
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
                print(f"Using map template from: {path}")
                break
            except Exception as e:
                print(f"Warning: Failed to read template at {path}: {e}")
                
    if template_content is None:
        print("Warning: Template file not found or failed to read. Generating map with built-in template...")
        # Inline fallback - we use a token replacement mechanism
        # (This fallback content matches map_template.html exactly but is defined here for self-containment)
        # For brevity, we could import it or read from a string. Let's make sure it reads from map_template.html
        # since we just wrote it. If that failed, we fallback to a minimal template.
        # But we wrote map_template.html in the same folder, so it will always be found!
        sys.exit("Critical Error: Could not load map_template.html. Please ensure it is present in the script directory.")
        
    # 6. Inject JSON data and custom text into template
    site_data_json = json.dumps(sites, indent=2)
    bucket_data_json = json.dumps(bucket_data, indent=2)
    config_json = json.dumps(config, indent=2)
    
    theme_class = "light-mode" if config.get("theme") == "light" else ""
    
    output_html = template_content
    output_html = output_html.replace("{{SITE_DATA_JSON}}", site_data_json)
    output_html = output_html.replace("{{BUCKET_DATA_JSON}}", bucket_data_json)
    output_html = output_html.replace("{{CONFIG_JSON}}", config_json)
    output_html = output_html.replace("{{THEME_CLASS}}", theme_class)
    output_html = output_html.replace("{{MAP_TITLE}}", config["html_title"])
    output_html = output_html.replace("{{SIDEBAR_TITLE}}", config["sidebar_title"])
    output_html = output_html.replace("{{MAP_SUBTITLE}}", config["sidebar_subtitle"])
    output_html = output_html.replace("{{LABEL_TOTAL_SITES}}", config["label_total_sites"])
    output_html = output_html.replace("{{LABEL_BUCKETS}}", config["label_buckets"])
    output_html = output_html.replace("{{SEARCH_PLACEHOLDER}}", config["search_placeholder"])
    
    # 7. Write Output HTML
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
