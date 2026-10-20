# linkydink

A hackathon project at the Internet Archive.

## What it does

linkydink turns the Internet Archive's [Live Music Archive](https://archive.org/details/etree)
into something you can wander through. Its pages place live recordings on
maps and in time, follow one song from night to night, and let you gather
tracks into a playlist (a "seedlist") of your own. Every note you hear
streams straight from archive.org.

## What these projects represent

The Live Music Archive holds over 300,000 concert recordings from more than
9,000 bands, mostly made by fans and shared with the bands' blessing. It is
a huge, open record of live music. But it's organized the way an archive is,
one recording at a time, each with its own catalog page. linkydink tries out
other ways in, using the Grateful Dead's 1971 shows as a test case:

- **By place and time.** The maps show a year of touring: where the band
  played, in what order, and how often. Click a city or a date to hear that
  night.
- **By song.** The Casey Jones page follows one song through the 72 nights
  the band played it in 1971, the year with the most recordings of it in the
  Archive. Listen in order and you hear it change from night to night.
- **By listener.** A seedlist is a short, shareable list of songs, each one
  pointing to an exact track in an exact recording. The seedlist builder makes
  one from the map, and the player plays it.

A few ideas run through all of them:

- **Link, don't copy.** Nothing here hosts audio. The pages and data files
  only record which archive.org item and which file to play, and your browser
  streams it from the Archive. The Archive stays the source, and the pages link
  back to each recording's page on archive.org, where the taper is credited.
- **Small, static, and open.** Each page is a plain HTML file (some with a
  small JSON file beside it), with no build step and no server of our own, published with GitHub Pages. Anyone can read
  the source and try a new idea in a new folder.
- **Connecting the archive to the wider web of music data.** Recordings are
  more useful when you can tie them to who was on stage. [DATASOURCES.md](DATASOURCES.md)
  works out how to join the Live Music Archive's band collections to
  Wikidata, MusicBrainz and Discogs, which are the sources for band members,
  instruments and side projects. That's the natural next step.

## See it live

Everything on `main` is published with GitHub Pages; each folder is its own page.

- [Casey Jones, 1971](https://internetarchivecanada.github.io/linkydink/casey-jones-1971/): map and timetable of the 72 dates the Grateful Dead played Casey Jones in 1971. Play any night's version, or play through the year.
- [Grateful Dead 1971 map](https://internetarchivecanada.github.io/linkydink/gd1971-map/): 81 show dates across 44 cities, one recording per date. Click a city or a date to play the show, starting at Casey Jones when it was played.
- [Seedlist builder](https://internetarchivecanada.github.io/linkydink/seedlist-builder/): pick songs from the 1971 shows on a map, put them in order, and save them as `seedlist.json` or play them in the player.
- [Player](https://internetarchivecanada.github.io/linkydink/player/): plays a seedlist. On its own, it plays five songs by five different bands from across the Live Music Archive.

Every page shares a menu bar from [nav.js](nav.js); add new pages to its list.

Pushes to `main` show up here within a minute or so.

## How it fits together

| Folder | Data it carries | What it fetches from archive.org |
|---|---|---|
| `casey-jones-1971/` | One entry per date: venue, city, location, recording count, best recording and its Casey Jones file | That night's Casey Jones MP3 |
| `gd1971-map/` | One entry per date, with the recording to play and its Casey Jones track | The recording's track list and MP3s |
| `seedlist-builder/` | `shows.json`, a copy of the `gd1971-map` data | Track lists and MP3s for the shows you open |
| `player/` | `seedlist.json`: title, artist, date, venue, archive.org identifier and file for each song | The MP3s |

A seedlist is plain JSON. Each track names an archive.org `identifier` and a
`file`, so `https://archive.org/download/<identifier>/<file>` plays it. The
builder hands its list to the player through the browser's local storage
(`player/?seedlist=local`).

## Team

- Brewster Kahle (brewster@archive.org)
- Dan Visel (danvisel@archive.org)
- Brian Eggert (brian.eggert@archive.org)
- mojomonger (mojomonger@archive.org)
- Connie Moon Sehat (connie.moon.sehat@archive.org)
- _add yourself here_

## Getting started

```bash
git clone https://github.com/internetarchivecanada/linkydink.git
cd linkydink
```

There's nothing to install. The pages load their data with `fetch`, so serve
the repo over HTTP instead of opening the files directly:

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000/seedlist-builder/ (or any other folder). If
port 8000 is taken, use another number.

Working in this repo alongside others: see [CONTRIBUTING.md](CONTRIBUTING.md).

## Status

Hackathon prototype: expect rough edges.
