"""Build gd-player/shows.json: one row per Grateful Dead show date in the
Live Music Archive, with venue, city, coordinates and the most-downloaded
recording.

    python3 build_shows.py GAZETTEER.txt [RAW.json]

GAZETTEER.txt is the US Census place gazetteer (public domain):
https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_Gaz_place_national.zip
RAW.json, if given, is a cached copy of the archive.org search results;
otherwise they are fetched (and saved there if a path was given).
"""
import collections, json, os, re, sys, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))

STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA", "colorado": "CO",
    "connecticut": "CT", "delaware": "DE", "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS", "kentucky": "KY", "louisiana": "LA",
    "maine": "ME", "maryland": "MD", "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD", "tennessee": "TN", "texas": "TX",
    "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC",
    # abbreviations seen in the metadata
    "pa.": "PA", "mass.": "MA", "r.i.": "RI", "ct.": "CT", "nb": "NE", "calif.": "CA", "conn.": "CT",
    "n.y.": "NY", "n.j.": "NJ", "wash.": "WA", "ore.": "OR", "colo.": "CO", "ill.": "IL", "mich.": "MI",
    "wis.": "WI", "minn.": "MN", "fla.": "FL", "ga.": "GA", "tenn.": "TN", "va.": "VA", "md.": "MD",
}
CODES = set(STATES.values())

# Cities whose names don't match a Census place as written.
CITY_ALIAS = {
    ("new york city", "NY"): "new york", ("nyc", "NY"): "new york", ("manhattan", "NY"): "new york",
    ("brooklyn", "NY"): "new york", ("queens", "NY"): "new york", ("bronx", "NY"): "new york",
    ("flushing meadows", "NY"): "new york", ("flushing", "NY"): "new york", ("st. louis", "MO"): "st. louis",
    ("saint louis", "MO"): "st. louis", ("st. paul", "MN"): "st. paul", ("saint paul", "MN"): "st. paul",
    ("washington", "DC"): "washington", ("ft. lauderdale", "FL"): "fort lauderdale",
    ("hollywood", "CA"): "los angeles", ("honolulu", "HI"): "urban honolulu",
    ("nashville", "TN"): "nashville-davidson", ("lexington", "KY"): "lexington-fayette", ("boise", "ID"): "boise city",
}

# Coordinates for places outside the US or missing from the gazetteer.
MANUAL = {
    "london, england": (51.5072, -0.1276), "paris, france": (48.8566, 2.3522), "berlin, germany": (52.52, 13.405),
    "cairo, egypt": (30.0444, 31.2357), "giza, egypt": (29.9773, 31.1325), "amsterdam, netherlands": (52.3676, 4.9041),
    "essen, germany": (51.4556, 7.0116), "frankfurt, germany": (50.1109, 8.6821), "copenhagen, denmark": (55.6761, 12.5683),
    "hamburg, germany": (53.5511, 9.9937), "munich, germany": (48.1351, 11.582), "stockholm, sweden": (59.3293, 18.0686),
    "bremen, germany": (53.0793, 8.8017), "dijon, france": (47.322, 5.0415), "edinburgh, scotland": (55.9533, -3.1883),
    "luxembourg, luxembourg": (49.6116, 6.1319), "barcelona, spain": (41.3874, 2.1686), "aarhus, denmark": (56.1629, 10.2039),
    "wigan, england": (53.545, -2.6325), "newcastle, england": (54.9783, -1.6178), "russelsheim, germany": (49.9897, 8.4119),
    "rotterdam, netherlands": (51.9244, 4.4777), "lille, france": (50.6292, 3.0573), "herouville, france": (49.2036, -0.3226),
    "dusseldorf, germany": (51.2277, 6.7735), "montego bay, jamaica": (18.4762, -77.8939),
    "vancouver, canada": (49.2827, -123.1207), "toronto, canada": (43.6532, -79.3832), "hamilton, canada": (43.2557, -79.8711),
    "montreal, canada": (45.5019, -73.5674), "maple, canada": (43.8563, -79.5085), "ottawa, canada": (45.4215, -75.6972),
    "winnipeg, canada": (49.8954, -97.1385), "calgary, canada": (51.0447, -114.0719), "edmonton, canada": (53.5461, -113.4938),
    "newcastle-under-lyme, england": (53.0131, -2.2273), "bickershaw, england": (53.5196, -2.5652),
}
# US places the gazetteer misses or places badly (San Francisco's internal
# point is out at the Farallon Islands).
MANUAL_US = {
    "San Francisco, CA": (37.7749, -122.4194), "Ventura, CA": (34.2746, -119.229), "Upper Darby, PA": (39.9601, -75.2846),
    "Clarkston, MI": (42.7356, -83.4188), "Universal City, CA": (34.1381, -118.3534), "Foxboro, MA": (42.0654, -71.2478),
    "Rio Nido, CA": (38.5163, -122.9811), "North Hollywood, CA": (34.1870, -118.3813), "Highgate, VT": (44.9381, -73.0496),
    "Hallandale, FL": (25.9812, -80.1484), "West Hollywood, FL": (26.0112, -80.1495), "San Framcisco, CA": (37.7749, -122.4194),
    "Bethel, NY": (41.7015, -74.8800), "Dania, FL": (26.0523, -80.1439), "Oahu, HI": (21.3069, -157.8583),
    "Wayne, NJ": (40.9254, -74.2765), "San Pedro, CA": (33.7361, -118.2923), "Champaign-Urbana, IL": (40.1106, -88.2073),
    "Van Nuys, CA": (34.1899, -118.4514), "De Kalb, IL": (41.9295, -88.7504), "Billerica, MA": (42.5584, -71.2689),
    "Amherst, MA": (42.3732, -72.5199), "Piscataway, NJ": (40.5549, -74.4643), "Devore, CA": (34.2161, -117.4031),
    "San Rafael?, CA": (37.9735, -122.5311), "Donner'S Summit, CA": (39.3157, -120.3299), "Angel'S Camp, CA": (38.0683, -120.5396),
    "Angels Camp, CA": (38.0683, -120.5396),
}
CANADA = {"bc": "canada", "british columbia": "canada", "ontario": "canada", "on": "canada", "quebec": "canada",
          "qc": "canada", "alberta": "canada", "ab": "canada", "manitoba": "canada", "canada": "canada"}
COUNTRY_ALIAS = {"west germany": "germany", "en": "england", "fr": "france", "dänemark (denmark)": "denmark", "uk": "england"}
CITY_FIX = {"københavn (copenhagen)": "copenhagen"}
NON_PLACES = {"unknown", "various", "various - see info file", "unknown location", "", "none"}


def load_gazetteer(path):
    places = {}
    with open(path, encoding="utf-8") as f:
        next(f)
        for line in f:
            p = [x.strip() for x in line.split("\t")]
            name = p[3]
            while True:
                stripped = re.sub(r" (city|town|village|borough|CDP|municipality|government|metropolitan|"
                                  r"unified|consolidated|metro|\(balance\)|urban county|comunidad|zona urbana)$", "", name)
                if stripped == name:
                    break
                name = stripped
            name = name.lower()
            key = (name, p[0])
            # Prefer the larger place when names collide (e.g. a city and a CDP).
            if key not in places or float(p[8]) > places[key][2]:
                places[key] = (float(p[10]), float(p[11]), float(p[8]))
    return places


def parse_coverage(cov):
    """Return ("US", city, ST) or ("INTL", "city, country") or None."""
    if not isinstance(cov, str):
        return None
    cov = cov.strip()
    if cov.lower() in NON_PLACES or " and " in cov:
        return None
    if re.fullmatch(r"washington,? ?d\.?c\.?", cov, re.I):
        return ("US", "washington", "DC")
    parts = [x.strip() for x in cov.split(",") if x.strip()]
    if len(parts) < 2:
        return None
    city = CITY_FIX.get(parts[0].lower(), parts[0].lower())
    rest = [x.lower() for x in parts[1:]]
    if city in NON_PLACES or not city.strip("?") or city == "allover":
        return None
    if rest[-1] in CANADA or (len(rest) > 1 and rest[0] in CANADA):
        return ("INTL", f"{city}, canada")
    st = rest[0].upper() if rest[0].upper() in CODES else STATES.get(rest[0])
    if st and len(rest) == 1:
        return ("US", city, st)
    country = COUNTRY_ALIAS.get(rest[-1], rest[-1])
    return ("INTL", f"{city}, {country}")


def fetch_raw():
    items, cursor = [], None
    while True:
        q = {"q": "collection:GratefulDead", "count": "10000",
             "fields": "identifier,date,venue,coverage,downloads,avg_rating,num_reviews"}
        if cursor:
            q["cursor"] = cursor
        with urllib.request.urlopen("https://archive.org/services/search/v1/scrape?" + urllib.parse.urlencode(q)) as r:
            d = json.load(r)
        items += d["items"]
        cursor = d.get("cursor")
        if not cursor:
            return items


def most_common(values):
    values = [v for v in values if v]
    return collections.Counter(values).most_common(1)[0][0] if values else None


def main():
    places = load_gazetteer(sys.argv[1])
    raw_path = sys.argv[2] if len(sys.argv) > 2 else None
    if raw_path and os.path.exists(raw_path):
        items = json.load(open(raw_path))
    else:
        items = fetch_raw()
        if raw_path:
            json.dump(items, open(raw_path, "w"))

    by_date = collections.defaultdict(list)
    for it in items:
        if isinstance(it.get("date"), str):
            by_date[it["date"][:10]].append(it)

    shows, missing = [], collections.Counter()
    for date in sorted(by_date):
        recs = by_date[date]
        loc = most_common([parse_coverage(r.get("coverage")) for r in recs])
        venue = most_common([r.get("venue").strip() for r in recs if isinstance(r.get("venue"), str)])
        best = max(recs, key=lambda r: r.get("downloads") or 0)
        lat = lon = None
        city = country = None
        if loc and loc[0] == "US":
            _, c, st = loc
            name = CITY_ALIAS.get((c, st), c)
            hit = places.get((name, st)) or places.get((name.replace("saint ", "st. "), st)) \
                or places.get((name.replace("st. ", "saint "), st)) or places.get((name.replace("mt. ", "mount "), st))
            city = f"{c.title()}, {st}"
            if city in MANUAL_US:
                lat, lon = MANUAL_US[city]
            elif hit:
                lat, lon = hit[0], hit[1]
            else:
                missing[city] += 1
            country = "US"
        elif loc:
            city = loc[1].title()
            country = loc[1].split(", ")[-1].title()
            if loc[1] in MANUAL:
                lat, lon = MANUAL[loc[1]]
            else:
                missing[city] += 1
        shows.append({
            "d": date, "v": venue, "c": city, "co": country,
            "lat": round(lat, 4) if lat is not None else None, "lon": round(lon, 4) if lon is not None else None,
            "n": len(recs), "id": best["identifier"],
        })

    out = os.path.join(HERE, "shows.json")
    with open(out, "w") as f:
        json.dump({"source": "archive.org collection:GratefulDead (Live Music Archive); "
                             "US coordinates from the US Census 2023 place gazetteer",
                   "shows": shows}, f, separators=(",", ":"))
    placed = sum(1 for s in shows if s["lat"] is not None)
    print(f"{len(shows)} show dates, {placed} placed, {len(items)} recordings -> {out}")
    for city, n in missing.most_common():
        print(f"  unplaced: {city} ({n})")


if __name__ == "__main__":
    main()
