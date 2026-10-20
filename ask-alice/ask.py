#!/usr/bin/env python3
"""Ask questions about Alice's Adventures in Wonderland, answered by an LLM on BCDC.

The book (~36k tokens) is about the size of the models' 40k context, so instead
of pasting it all in:

  * once, the model writes a short summary of each chapter (cached in summaries.json)
  * per question, BM25 picks the passages that best match the question, and the
    model answers from the chapter summaries plus those passages, citing chapters

Stdlib only. Needs the IA VPN to reach the endpoint.

  python3 ask.py "Who does Alice meet at the tea party?"
  python3 ask.py            # interactive: one question per line
  python3 ask.py --show-passages "What does the Caterpillar ask Alice?"

LLM_BASE_URL and LLM_MODEL override the defaults.
"""
import argparse
import json
import math
import os
import re
import sys
import time
import urllib.request
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
BOOK = os.path.join(HERE, "alice.txt")   # archive.org/details/alicesadventures00011gut, alice30.txt
SUMMARIES = os.path.join(HERE, "summaries.json")
BASE = os.environ.get("LLM_BASE_URL", "https://llm-anon.p01.ca-west-1a.archive.org/v1").rstrip("/")
MODEL = os.environ.get("LLM_MODEL", "gemma-4-26B-A4B-it-AWQ-4bit")

PASSAGE_WORDS = 300   # passage size, with a 60-word overlap so an answer isn't split in two
OVERLAP = 60
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]
STOP = set("""a an and are as at be but by for from had has have he her his i in is it its
of on or she so that the their them then there they this to was were what when where which
who whom why with you your did does do not no said alice""".split())


def load_chapters():
    """Return [(number, title, text)] for the 12 chapters, Gutenberg header and footer removed."""
    raw = open(BOOK, encoding="latin-1").read()
    body = raw[raw.index("CHAPTER I\n"):raw.index("THE END")]
    parts = re.split(r"^\s*CHAPTER ([IVX]+)\s*$", body, flags=re.M)
    chapters = []
    for num, text in zip(parts[1::2], parts[2::2]):
        lines = [l.strip() for l in text.strip().splitlines()]
        title = lines[0]
        chapters.append((ROMAN.index(num) + 1, title, " ".join(" ".join(lines[1:]).split())))
    return chapters


def passages(chapters):
    out = []
    for num, title, text in chapters:
        words = text.split()
        step = PASSAGE_WORDS - OVERLAP
        for i in range(0, max(1, len(words) - OVERLAP), step):
            out.append({"ch": num, "title": title, "text": " ".join(words[i:i + PASSAGE_WORDS])})
    return out


def stem(w):
    """Crude suffix stripping so 'riddles', 'riddle' and 'riddling' match."""
    for suf in ("ing", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[:-len(suf)].rstrip("e")
    return w.rstrip("e") if len(w) > 3 else w


def tokens(s):
    return [stem(w) for w in re.findall(r"[a-z]+", s.lower()) if w not in STOP and len(w) > 1]


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.tf = [Counter(tokens(d)) for d in docs]
        self.len = [sum(t.values()) for t in self.tf]
        self.avg = sum(self.len) / len(self.len)
        df = Counter(w for t in self.tf for w in t)
        n = len(docs)
        self.idf = {w: math.log(1 + (n - c + .5) / (c + .5)) for w, c in df.items()}
        self.k1, self.b = k1, b

    def top(self, query, k):
        q = tokens(query)
        scores = []
        for i, tf in enumerate(self.tf):
            s = 0.0
            for w in q:
                if w in tf:
                    f = tf[w]
                    s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.len[i] / self.avg))
            scores.append((s, i))
        return [i for s, i in sorted(scores, reverse=True)[:k] if s > 0]


def chat(messages, max_tokens=800, retries=3):
    body = json.dumps({
        "model": MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0.2,
        "chat_template_kwargs": {"enable_thinking": False},
    }).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(f"{BASE}/chat/completions", body, {"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as r:
                msg = json.load(r)["choices"][0]["message"]
            return (msg.get("content") or "").strip()
        except Exception as e:
            if attempt == retries - 1:
                raise SystemExit(f"LLM call to {BASE} ({MODEL}) failed: {e}\nAre you on the IA VPN?")
            time.sleep(2 * (attempt + 1))


def chapter_summaries(chapters):
    if os.path.exists(SUMMARIES):
        return json.load(open(SUMMARIES))
    out = []
    for num, title, text in chapters:
        print(f"  summarizing chapter {num}: {title}", file=sys.stderr)
        s = chat([{"role": "user", "content":
                   f"Summarize this chapter of Alice's Adventures in Wonderland in 4-6 sentences. "
                   f"Name every character who appears and the key events in order.\n\n"
                   f"Chapter {num}: {title}\n\n{text}"}], max_tokens=400)
        out.append({"ch": num, "title": title, "summary": s})
    json.dump(out, open(SUMMARIES, "w"), indent=1)
    return out


def answer(question, summaries, psgs, index, k=8, show=False):
    hits = sorted(index.top(question, k), key=lambda i: i)   # book order reads better than score order
    if show:
        for i in hits:
            print(f"--- ch {psgs[i]['ch']}: {psgs[i]['text'][:160]}...", file=sys.stderr)
    outline = "\n".join(f"Chapter {s['ch']} ({s['title']}): {s['summary']}" for s in summaries)
    excerpts = "\n\n".join(f"[Chapter {psgs[i]['ch']}] {psgs[i]['text']}" for i in hits)
    return chat([
        {"role": "system", "content":
         "You answer questions about Lewis Carroll's Alice's Adventures in Wonderland. "
         "Use only the chapter summaries and excerpts given. Cite chapters like (ch. 7). "
         "Quote the excerpts briefly when it helps. If the material doesn't answer the question, say so."},
        {"role": "user", "content":
         f"CHAPTER SUMMARIES\n{outline}\n\nEXCERPTS\n{excerpts}\n\nQUESTION: {question}"},
    ])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("question", nargs="*")
    ap.add_argument("-k", type=int, default=8, help="passages to retrieve (default 8)")
    ap.add_argument("--show-passages", action="store_true", help="print the retrieved passages to stderr")
    args = ap.parse_args()

    chapters = load_chapters()
    psgs = passages(chapters)
    index = BM25([p["text"] for p in psgs])
    summaries = chapter_summaries(chapters)

    if args.question:
        print(answer(" ".join(args.question), summaries, psgs, index, args.k, args.show_passages))
        return
    print(f"Alice's Adventures in Wonderland: {len(chapters)} chapters, {len(psgs)} passages, model {MODEL}.")
    print("Ask a question (Ctrl-D to quit).")
    for line in sys.stdin:
        if line.strip():
            print(answer(line.strip(), summaries, psgs, index, args.k, args.show_passages), "\n")


if __name__ == "__main__":
    main()
