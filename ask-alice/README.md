# ask-alice

Ask questions about *Alice's Adventures in Wonderland* and get answers from an
LLM running on BCDC, IA's GPU cluster, with chapter citations.

```bash
python3 ask.py "What riddle does the Hatter ask Alice?"
python3 ask.py            # interactive: one question per line, Ctrl-D to quit
```

Needs the IA VPN (Tailscale) to reach the endpoint. Python 3, no packages.

## How it works

The book is about 36k tokens, close to the models' 40k context, so it isn't
sent whole:

- `summaries.json` holds a short summary of each of the 12 chapters, written
  once by the model. Delete it to have them rewritten.
- For each question, keyword search (BM25) picks the 8 passages that match
  best, and the model answers from the summaries plus those passages.

## Files

- `ask.py`: the tool.
- `alice.txt`: the Project Gutenberg text, from
  [archive.org/details/alicesadventures00011gut](https://archive.org/details/alicesadventures00011gut).
- `summaries.json`: cached chapter summaries.

## Options

- `LLM_MODEL` picks the model (default `gemma-4-26B-A4B-it-AWQ-4bit`); any model
  listed at `/v1/models` works.
- `LLM_BASE_URL` overrides the endpoint.
- `-k N` retrieves N passages instead of 8; `--show-passages` prints them.

See the [bcdc repo](https://github.com/internetarchivecanada/bcdc) for the
endpoint and which models are live.

## Limits

- Search matches words, so spell names the way the book does ("Dormouse", not
  "doormouse").
- Questions that need details from across the whole book lean on the chapter
  summaries and can miss minor characters.
- It only knows *Wonderland*, not *Through the Looking-Glass*.
