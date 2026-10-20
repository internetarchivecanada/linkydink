"""Add songs to gd-player/shows.json: for each show date, the songs played
and which track of the recording each one starts on.

    python3 build_songs.py RAW.json CACHE_DIR

RAW.json is the archive.org search dump that build_shows.py saves; it is used
to try the next most downloaded recording when the chosen one has no track
titles. CACHE_DIR keeps each recording's file list so reruns are fast.

Run build_shows.py first. This rewrites shows.json in place, adding a "songs"
list and, on each show, "s": [[song index, track index], ...]. Track indexes
follow the order gd-player/index.html plays the MP3s in.
"""
import collections, json, os, re, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
MIN_SHOWS = 3   # a song must turn up in this many shows to be listed

# track titles that are not songs
NOT_SONGS = re.compile(r"^(tuning|dead air|crowd|crowd noise|applause|intro|introduction|banter|stage banter|"
                       r"band intros?|announcements?|encore break|set ?break|noodling|jam|unknown|tape flip|"
                       r"\?+|soundcheck|sound check|e:|encore|set \d|disc \d|d\d|untitled|bill graham.*|"
                       r"(the )?(drums|space)? ?tuning|rap|stage announcements?|pa announcements?)$", re.I)
ALIAS = {  # spelling variants -> one key
    "stephen": "saintstephen", "ststephen": "saintstephen", "goingdowntheroadfeelingbad": "goingdowntheroadfeelinbad",
    "goindowntheroadfeelinbad": "goingdowntheroadfeelinbad", "gdtrfb": "goingdowntheroadfeelinbad",
    "truckin": "truckin", "truckin'": "truckin", "sugarmag": "sugarmagnolia", "dancininthestreets": "dancinginthestreet",
    "dancininthestreet": "dancinginthestreet", "dancinginthestreets": "dancinginthestreet",
    "nfa": "notfadeaway", "uncle johns band": "unclejohnsband", "playinintheband": "playingintheband",
    "playin": "playingintheband", "minglewood": "minglewoodblues", "newminglewoodblues": "minglewoodblues",
    "allnewminglewoodblues": "minglewoodblues", "thewheel": "wheel", "fotm": "fireonthemountain",
    "drumz": "drums", "drum": "drums", "spaced": "space",
    "biodtl": "beatitondowntheline", "babeitaintnolie": "ohbabeitaintnolie", "aintnolie": "ohbabeitaintnolie",
    "corinna": "corrina", "crypticalenvelopement": "crypticalenvelopment", "deepelementaryblues": "deepelemblues",
    "finiculifinicula": "funiculifunicula", "gimmiesomelovin": "gimmesomelovin",
    "goindowntheroad": "goingdowntheroadfeelinbad", "goindowntheroadfeelingbad": "goingdowntheroadfeelinbad",
    "goingdowntheroadfeelingbad": "goingdowntheroadfeelinbad", "goodtimesblues": "goodtimeblues",
    "greateststory": "greateststoryevertold", "helpisontheway": "helpontheway", "help": "helpontheway",
    "honkytonkwoman": "honkytonkwomen", "iaintsuperstitous": "iaintsuperstitious",
    "itsamansworld": "itsamansmansmansworld", "kingbee": "imakingbee", "lazylightnin": "lazylightning",
    "lovelight": "turnonyourlovelight", "mansmart": "mansmartwomansmarter", "mansmartwomensmarter": "mansmartwomansmarter",
    "womanaresmarter": "mansmartwomansmarter", "womenaresmarter": "mansmartwomansmarter", "mexicali": "mexicaliblues",
    "midnighthour": "inthemidnighthour", "mississippihalfstep": "mississippihalfstepuptowntoodeloo",
    "mississippihalfstepuptowntoodleloo": "mississippihalfstepuptowntoodeloo",
    "mississippihalfstepuptowntoodleoo": "mississippihalfstepuptowntoodeloo", "mistercharlie": "mrcharlie",
    "musicneverstopped": "themusicneverstopped", "newnewminglewoodblues": "minglewoodblues", "otherone": "theotherone",
    "playininthebandreprise": "playingintheband reprise", "playinreprise": "playingintheband reprise",
    "playingreprise": "playingintheband reprise", "playingthebandreprise": "playingintheband reprise",
    "playinginthebandreprise": "playingintheband reprise", "playininthebandjam": "playinginthebandjam",
    "playinjam": "playinginthebandjam", "playingjam": "playinginthebandjam", "promisedland": "thepromisedland",
    "queenjane": "queenjaneapproximately", "sampsonanddelilah": "samsonanddelilah", "seasons": "seasonsofmyheart",
    "smokestacklightnin": "smokestacklightning", "stofcircumstance": "saintofcircumstance",
    "sittinontopoftheworld": "sittingontopoftheworld",
    "stuckinmobilewiththememphisbluesagain": "stuckinsideofmobilewiththememphisbluesagain",
    "stuckinsideamobilewiththememphisbluesagain": "stuckinsideofmobilewiththememphisbluesagain",
    "tennessejed": "tennesseejed", "terrapin": "terrapinstation", "thedaysbetween": "daysbetween",
    "thefrozenlogger": "frozenlogger", "themonkeyandtheengineer": "monkeyandtheengineer", "touchofgray": "touchofgrey",
    "throwinstones": "throwingstones", "walkingblues": "walkinblues", "walkingthedog": "walkinthedog",
    "wecanrunbutwecanthide": "wecanrun", "webidyougoodnight": "andwebidyougoodnight",
    "weatherreportsuitepartone": "weatherreportsuitepart1", "wrsprelude": "weatherreportsuiteprelude",
    "workingmansblues": "workinmanblues", "tomthumbsblues": "justliketomthumbsblues",
    "nobodysfaultjam": "nobodysfaultbutminejam", "nobodysjam": "nobodysfaultbutminejam", "allovernow": "itsallovernow",
    "allaroundthisworld": "ivebeenallaroundthisworld", "bobbymcgee": "meandbobbymcgee", "dayjob": "keepyourdayjob",
    "longwaytogohome": "waytogohome", "ollinarageed": "ollinarrageed", "quinntheeskimo": "themightyquinn",
    "samething": "thesamething", "theotheronejam": "otheronejam",
}
JUNK = re.compile(r"^(track \d+|part \d+|outro|instrumental|tune up|crowd and tuning|tuning and crowd|bob's joke|bass|phil|"
                  r"jerry garcia interview|set \d+ intro|fireworks|yellow dog story|gentlemen, start your engines|"
                  r"crowd noise|crowd and|crowd)$", re.I)


def key(title):
    k = re.sub(r"[^a-z0-9]", "", title.lower().replace("&", "and"))
    return ALIAS.get(k, k)


def split_songs(title):
    """'Scarlet Begonias-> Fire On The Mountain' -> ['Scarlet Begonias', 'Fire On The Mountain']"""
    t = re.sub(r"^\s*(d\d+)?t?\d+[\s.\-:)]+", "", title)            # leading track numbers
    t = re.sub(r"[\[(][^\])]*[\])]", "", t)                          # (notes) [timings]
    parts = re.split(r"\s*(?:-+>|>|/|\s-\s|;|\+)\s*", t)
    out = []
    for p in parts:
        p = re.sub(r"[*#%@^~$!]+", "", p).strip(" .,:-'\"\t")
        p = re.sub(r"\s+", " ", p)
        p = re.sub(r"^(e|encore|set \d+|s\d+)\s*:\s*", "", p, flags=re.I)          # "E: U.S. Blues"
        p = re.sub(r"\s+(tuning|tease)$", "", p, flags=re.I)                     # "Beer Barrel Polka Tuning"
        if len(p) < 2 or NOT_SONGS.match(p) or JUNK.match(p) or re.fullmatch(r"[\d:.\s]+", p):
            continue
        out.append(p)
    return out


def play_order(files):
    """The MP3 list gd-player/index.html builds, in the same order."""
    mp3 = [f for f in files if f["name"].lower().endswith(".mp3")]
    s = [f for f in mp3 if f.get("format") == "VBR MP3"] or [f for f in mp3 if not f["name"].lower().endswith("_64kb.mp3")] or mp3
    def tn(f):
        m = re.match(r"\d+", str(f.get("track") or ""))
        return int(m.group()) if m else 0
    return sorted(s, key=lambda f: (tn(f), f["name"]))


def fetch_files(ident, cache):
    path = os.path.join(cache, re.sub(r"[^\w.-]", "_", ident) + ".json")
    if os.path.exists(path):
        return json.load(open(path))
    for attempt in range(4):
        try:
            with urllib.request.urlopen(f"https://archive.org/metadata/{urllib.parse.quote(ident)}/files", timeout=30) as r:
                files = json.load(r).get("result") or []
            json.dump(files, open(path, "w"))
            return files
        except Exception:
            time.sleep(2 * (attempt + 1))
    return []


def songs_for(files):
    """[(display title, track index)] for each song, first occurrence only."""
    seen, out = set(), []
    for i, f in enumerate(play_order(files)):
        for song in split_songs(f.get("title") or ""):
            k = key(song)
            if k and k not in seen:
                seen.add(k)
                out.append((song, i))
    return out


def main():
    raw, cache = sys.argv[1], sys.argv[2]
    os.makedirs(cache, exist_ok=True)
    data = json.load(open(os.path.join(HERE, "shows.json")))
    shows = data["shows"]

    by_date = collections.defaultdict(list)
    for it in json.load(open(raw)):
        if isinstance(it.get("date"), str):
            by_date[it["date"][:10]].append(it)
    for recs in by_date.values():
        recs.sort(key=lambda r: -(r.get("downloads") or 0))

    def work(show):
        # the most downloaded recording, or the next one if it has no track titles
        candidates = [show["id"]] + [r["identifier"] for r in by_date[show["d"]] if r["identifier"] != show["id"]][:2]
        for ident in candidates:
            got = songs_for(fetch_files(ident, cache))
            if len(got) >= 3 or ident == candidates[-1]:
                return ident, got
        return show["id"], []

    with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(work, shows))

    # display name per song: the spelling used most often
    spell = collections.defaultdict(collections.Counter)
    count = collections.Counter()
    for _, got in results:
        for song, _ in got:
            spell[key(song)][song] += 1
        for k in {key(s) for s, _ in got}:
            count[k] += 1
    keep = sorted((k for k, n in count.items() if n >= MIN_SHOWS), key=lambda k: spell[k].most_common(1)[0][0].lower())
    index = {k: i for i, k in enumerate(keep)}
    data["songs"] = [spell[k].most_common(1)[0][0] for k in keep]
    for show, (ident, got) in zip(shows, results):
        show["id"] = ident
        show["s"] = [[index[key(s)], t] for s, t in got if key(s) in index]

    with open(os.path.join(HERE, "shows.json"), "w") as f:
        json.dump(data, f, separators=(",", ":"))
    with_songs = sum(1 for s in shows if s["s"])
    print(f"{len(data['songs'])} songs (in {MIN_SHOWS}+ shows); {with_songs} of {len(shows)} shows have songs")


if __name__ == "__main__":
    main()
