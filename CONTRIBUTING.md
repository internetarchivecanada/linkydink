# Working together

Several of us push to this repo at once, often touching the same lines. These
few habits keep us from stepping on each other.

## Before you start, and before every push

```bash
git pull --rebase
```

`--rebase` replays your commits on top of everyone else's instead of creating a
merge commit, which keeps the history readable.

## Never force-push `main`

`git push --force` (and `--force-with-lease`) on `main` **erases other people's
commits**. If your push is rejected, it is because someone else pushed first —
that is normal, and the fix is never force:

```bash
git pull --rebase
git push
```

## Push straight to `main`

Everyone commits and pushes directly to `main`; no branches or PRs needed.
Keep commits small and push often so others pick up your changes quickly.

## If you cloned while the repo was empty

An empty clone plus a local commit gives you a history with no ancestor in
common with the remote, and `git pull` refuses with *"refusing to merge
unrelated histories."* Don't reach for `--allow-unrelated-histories`; rebase
instead:

```bash
git pull --rebase origin main
```

## Adding yourself to the README

Add your line to the Team list in [README.md](README.md) and leave the
`_add yourself here_` placeholder in place for the next person.
