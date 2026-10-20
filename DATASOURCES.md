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

## Recommendation

1. **Wikidata** for the entity graph and cross-source IDs — CC0, no key, no
   rate limit, and it links out to everything else.
2. **MusicBrainz** when we need instruments, original-member flags, or more
   precise tenure dates. Mind the CC0 / CC BY-NC-SA split.
3. **Discogs** only to enrich side projects and affiliations. Do not rely on it
   for membership dates; it has none.

For anything beyond a few thousand lookups, use the bulk dumps rather than the
APIs — all three publish them, and the per-request limits above make live
crawling impractical at scale.
