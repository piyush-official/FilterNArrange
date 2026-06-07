# Merged branches — safe to delete

These remote branches have been **squash-merged into `main`** and are kept on
the remote only as a historical reference. Once their context is no longer
needed they can be removed safely.

| Branch | PR | Merge commit | Merged on |
|---|---|---|---|
| `feat/plan-a-foundation` | [#1](https://github.com/piyush-official/FilterNArrange/pull/1) | `8767015` | 2026-06-07 |
| `feat/plan-b-walking-skeleton` | [#2](https://github.com/piyush-official/FilterNArrange/pull/2) | `0d49f20` | 2026-06-07 |

## How to delete them

When you're ready (e.g. once Plan C is well underway and nothing references
these branch names anymore):

```sh
# Delete remote
git push origin --delete feat/plan-a-foundation
git push origin --delete feat/plan-b-walking-skeleton

# Delete local copies
git branch -D feat/plan-a-foundation
git branch -D feat/plan-b-walking-skeleton

# Drop this file once both branches are gone
git rm MERGED_BRANCHES.md
git commit -m "chore: remove merged Plan A/B branches"
```

> Squash-merge collapses each branch into a single commit on `main`; the
> per-commit history lives only on the feature branch. If you want to dig
> into the granular Plan A or Plan B commits later, do it **before** deleting.
