# Data sources for bands and band members

Evaluation of where to pull structured band/membership data from. Every claim
below was tested against the live APIs on 2026-10-20, not taken from docs.

**Short version:** use **Wikidata** or **MusicBrainz** as the primary source and
**Discogs** to fill in side projects. Join them on IDs that Wikidata already
carries. Note that *Wikipedia* itself is the wrong target — see below.

## Comparison

| | Wikidata | MusicBrainz | Discogs |
|---|---|---|---|
| Membership dates | yes, start + end | yes, finer-grained | **no** — only `active` true/false |
| Instruments | no | yes | no |
| "Original member" flag | no | yes | no |
| Auth required | no | no (User-Agent required) | no (token raises limits) |
| Rate limit | none enforced | ~1 req/sec | 25/min anon, 60/min with token |
| License | CC0 | core CC0, rest CC BY-NC-SA 3.0 | dumps CC0; API data partly restricted |
| Bulk dumps | yes | yes | yes, monthly |

Members returned for The Beatles: Wikidata 8, MusicBrainz 9, Discogs 6.

## Wikidata (not Wikipedia)

Wikipedia articles are prose under CC BY-SA, and scraping them means parsing
infoboxes. **Wikidata** is Wikipedia's structured arm, it is CC0, and it answers
this query directly. Prefer it.

No API key. Membership lives on the band's `P527` ("has part") statements, with
`P580`/`P582` qualifiers for start and end of tenure:

```sparql
SELECT ?memberLabel ?start ?end WHERE {
  wd:Q1299 p:P527 ?stmt .          # Q1299 = The Beatles
  ?stmt ps:P527 ?member .
  OPTIONAL { ?stmt pq:P580 ?start }
  OPTIONAL { ?stmt pq:P582 ?end }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
}
```

POST/GET to `https://query.wikidata.org/sparql` with
`Accept: application/sparql-results+json`. Returns all eight Beatles including
obscure early members (Chas Newby, Tommy Moore) with dated tenures.

## MusicBrainz

The richest source for this specific question, and purpose-built for music.

```
https://musicbrainz.org/ws/2/artist/<MBID>?inc=artist-rels&fmt=json
```

Filter `relations` for `type == "member of band"`. Each gives `begin`, `end`,
and an `attributes` list carrying instruments and an `original` flag:

```
John Lennon      1960     1969-09    ['guitar', 'lead vocals', 'original']
Pete Best        1960-08-12  1962-08-16  ['drums (drum set)']
```

Send a descriptive `User-Agent` with contact details or you will be blocked.
Rate limit is about one request per second — for anything bulk, take the
database dump instead of hammering the API.

**Licensing caveat:** core data (artists, releases, relationships) is CC0, but
annotations, tags, ratings and edit history are CC BY-NC-SA 3.0 and
non-commercial only. If we use a full dump we have to keep the two apart.

## Discogs

Works unauthenticated and returned HTTP 200 in testing, with
`x-discogs-ratelimit: 25` confirming 25 requests/minute anonymously (a token
raises it to 60).

**Weakest for membership.** `GET /artists/82730` returns a `members` array with
only `name`, `id` and `active` — **no dates at all** — and names are
inconsistent with the other sources ("Richard Starkey", not Ringo Starr). It
returned 6 members where MusicBrainz returned 9.

**Where it wins:** the reverse direction. `GET /artists/35301` (a person)
returns a `groups` array — 21 entries for Paul McCartney, including side
projects like The Fireman and The Smokin' Mojo Filters that the other two
cover less well. Use it for breadth of affiliations, not for tenure.

**Licensing caveat:** the monthly data dumps are CC0, but the API also serves
"restricted data" governed by the Discogs API Terms of Use. The CC0 grant
covers the dumps, not everything the API returns.

## Joining the three

Wikidata already stores the foreign keys, so use it as the join table rather
than matching on names (which, per the Ringo example, will not work):

- `P434` → MusicBrainz artist ID
- `P1953` → Discogs artist ID

```sparql
SELECT ?bandLabel ?mbid ?discogs WHERE {
  VALUES ?band { wd:Q1299 wd:Q15862 wd:Q1203 }
  OPTIONAL { ?band wdt:P434 ?mbid }
  OPTIONAL { ?band wdt:P1953 ?discogs }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
}
```

Verified: this returns `b10bbbfc-…` and `82730` for The Beatles, matching the
IDs used in the direct API calls above.

## Internet Archive Live Music Archive (LMA / etree)

Tested 2026-10-20. The collection is `etree`: **305,507 items** across
**9,329 band collections**. The `ia` CLI (5.12.0) is already installed locally.

### The join key is the band sub-collection, not `creator`

Every item's `collection` field contains a per-band collection alongside
`etree`:

```
identifier  01-track-01_20200827
creator     Ween
collection  Ween, etree, fav-chocolate_mike
```

That `Ween` entry is LMA's normalized band identifier. Use it as the key.
The `creator` field is free text and varies between uploaders.

> Note for `player/seedlist.json`: it currently keys on free-text `artist`
> ("Grateful Dead", "Jack Johnson"). Adding the band collection id to each
> track would make it joinable to the sources above.

### There is no ready-made link to Wikidata

I searched Wikidata's property list for both "Live Music Archive" and
"etree" — **no property exists**. So there is no off-the-shelf join; we have
to build it.

MusicBrainz *does* carry the link, as a `download for free` URL relation:

```
https://musicbrainz.org/ws/2/artist/<MBID>?inc=url-rels&fmt=json
→ [download for free] https://archive.org/details/GratefulDead
```

But it is **sparse**. In a sample of 8 LMA bands, 7 were in MusicBrainz and
only **2** had the archive.org relation — Phish and Ween, both major LMA
artists, did not. Treat it as a high-confidence seed, not as coverage.

### Collection IDs are derivable from band names

The identifiers are the band title with punctuation stripped
(`Grateful Dead` → `GratefulDead`). Measured over 1,000 real band
collections, normalizing to lowercase, mapping `&`/`+` to `and`, and
stripping non-alphanumerics:

| Result | Count | Share |
|---|---|---|
| Exact match | 914 | 91.4% |
| Prefix match | 76 | 7.6% |
| No match | 10 | 1.0% |

So ~99% resolve programmatically. The 1% that fail are parentheticals
(`Adamsson, Gianfriddo & Sutka (AGS)`), leading articles (`The Authority` →
`AuthorityBand`), diacritics (`Axon Zaëda`) and plain typos
(`BabyCalender` vs `Baby Calendar`).

**Suggested approach:** normalize-and-match as the primary join, using the
MusicBrainz `download for free` relations as ground truth to validate the
matcher, then hand-review the residue.

### Useful endpoints

```bash
# count items in a collection
curl 'https://archive.org/advancedsearch.php?q=collection%3Aetree&rows=0&output=json'

# bulk export (note: count has a minimum of 100)
curl 'https://archive.org/services/search/v1/scrape?q=collection%3Aetree&fields=identifier,creator,date,collection&count=100'

# full metadata for one item
curl 'https://archive.org/metadata/<identifier>'
```

### Caveat: per-item metadata is inconsistent

Fields vary by uploader. The Ween item above had `venue` and `date` but no
`source`, `lineage`, `taper` or `licenseurl` at all. Anything built on
show-level fields needs to tolerate them being absent rather than assume the
schema. Rights also sit per item, so don't infer a blanket license for the
collection from any one example.

## Recommendation

0. **LMA band collection id** as the local key for anything Live Music
   Archive, joined outward by name normalization and validated against
   MusicBrainz's `download for free` links.
1. **Wikidata** for the entity graph and cross-source IDs — CC0, no key, no
   rate limit, and it links out to everything else.
2. **MusicBrainz** when we need instruments, original-member flags, or more
   precise tenure dates. Mind the CC0 / CC BY-NC-SA split.
3. **Discogs** only to enrich side projects and affiliations. Do not rely on it
   for membership dates; it has none.

For anything beyond a few thousand lookups, use the bulk dumps rather than the
APIs — all three publish them, and the per-request limits above make live
crawling impractical at scale.
