# Merged branches — safe to delete

These remote branches have been **squash-merged into `main`** and are kept on
the remote only as a historical reference. Once their context is no longer
needed they can be removed safely.

| Branch | PR | Merge commit | Merged on |
|---|---|---|---|
| `feat/plan-a-foundation` | [#1](https://github.com/piyush-official/FilterNArrange/pull/1) | `8767015` | 2026-06-07 |
| `feat/plan-b-walking-skeleton` | [#2](https://github.com/piyush-official/FilterNArrange/pull/2) | `0d49f20` | 2026-06-07 |
| `feat/plan-c-plugin-breadth`   | [#3](https://github.com/piyush-official/FilterNArrange/pull/3) | `a5827dc` | 2026-06-07 |

## How to delete them

When you're ready (e.g. once a later plan is well underway and nothing
references these branch names anymore — see `clean_up_dev`):

```sh
# Delete remote
git push origin --delete feat/plan-a-foundation
git push origin --delete feat/plan-b-walking-skeleton
git push origin --delete feat/plan-c-plugin-breadth

# Delete local copies
git branch -D feat/plan-a-foundation
git branch -D feat/plan-b-walking-skeleton
git branch -D feat/plan-c-plugin-breadth

# Drop this file once every branch in the table is gone
git rm MERGED_BRANCHES.md
git commit -m "chore: remove merged Plan A/B/C branches"
```

> Squash-merge collapses each branch into a single commit on `main`; the
> per-commit history lives only on the feature branch. If you want to dig
> into the granular Plan A or Plan B commits later, do it **before** deleting.
