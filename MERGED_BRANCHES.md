# Merged branches — safe to delete

These remote branches have been **squash-merged into `main`** and are kept on
the remote only as a historical reference. Once their context is no longer
needed they can be removed safely.

| Branch | PR | Merge commit | Merged on |
|---|---|---|---|
| `feat/plan-a-foundation` | [#1](https://github.com/piyush-official/FilterNArrange/pull/1) | `8767015` | 2026-06-07 |
| `feat/plan-b-walking-skeleton` | [#2](https://github.com/piyush-official/FilterNArrange/pull/2) | `0d49f20` | 2026-06-07 |
| `feat/plan-c-plugin-breadth`   | [#3](https://github.com/piyush-official/FilterNArrange/pull/3) | `a5827dc` | 2026-06-07 |
| `feat/plan-c-gateway-openapi-frontend` | [#4](https://github.com/piyush-official/FilterNArrange/pull/4) | `0a39f5f` | 2026-06-07 |
| `feat/plan-c-frontend`         | [#5](https://github.com/piyush-official/FilterNArrange/pull/5) | `2e76923` | 2026-06-07 |
| `feat/plan-d-async-path`       | [#6](https://github.com/piyush-official/FilterNArrange/pull/6) | `93ec852` | 2026-06-07 |
| `feat/plan-d-gateway-async`    | [#7](https://github.com/piyush-official/FilterNArrange/pull/7) | `b902500` | 2026-06-07 |
| `feat/plan-d-worker-frontend-integration` | [#8](https://github.com/piyush-official/FilterNArrange/pull/8) | `7487e3c` | 2026-06-07 |
| `feat/plan-e-ai-foundation` | [#9](https://github.com/piyush-official/FilterNArrange/pull/9) | `4c1af4b` | 2026-06-07 |
| `feat/plan-e-gateway-ai` | [#10](https://github.com/piyush-official/FilterNArrange/pull/10) | `f3e0888` | 2026-06-08 |
| `feat/plan-e-frontend-ai` | [#11](https://github.com/piyush-official/FilterNArrange/pull/11) | `3ae8d2e` | 2026-06-08 |
| `feat/plan-f-foundation` | [#12](https://github.com/piyush-official/FilterNArrange/pull/12) | `ba19982` | 2026-06-08 |
| `feat/plan-f-features` | [#13](https://github.com/piyush-official/FilterNArrange/pull/13) | `9b34cc5` | 2026-06-08 |
| `feat/plan-f-frontend` | [#14](https://github.com/piyush-official/FilterNArrange/pull/14) | `2bbe05e` | 2026-06-08 |
| `feat/plan-g-auth` | [#15](https://github.com/piyush-official/FilterNArrange/pull/15) | `413adf8` | 2026-06-08 |
| `feat/plan-g-observability` | [#16](https://github.com/piyush-official/FilterNArrange/pull/16) | `f3f41c2` | 2026-06-08 |
| `feat/plan-g-hardening` | [#17](https://github.com/piyush-official/FilterNArrange/pull/17) | `c58f38f` | 2026-06-08 |

## How to delete them

When you're ready (e.g. once a later plan is well underway and nothing
references these branch names anymore — see `clean_up_dev`):

```sh
# Delete remote
git push origin --delete feat/plan-a-foundation
git push origin --delete feat/plan-b-walking-skeleton
git push origin --delete feat/plan-c-plugin-breadth
git push origin --delete feat/plan-c-gateway-openapi-frontend
git push origin --delete feat/plan-c-frontend
git push origin --delete feat/plan-d-async-path
git push origin --delete feat/plan-d-gateway-async
git push origin --delete feat/plan-d-worker-frontend-integration
git push origin --delete feat/plan-e-ai-foundation
git push origin --delete feat/plan-e-gateway-ai
git push origin --delete feat/plan-e-frontend-ai
git push origin --delete feat/plan-f-foundation
git push origin --delete feat/plan-f-features

# Delete local copies
git branch -D feat/plan-a-foundation
git branch -D feat/plan-b-walking-skeleton
git branch -D feat/plan-c-plugin-breadth
git branch -D feat/plan-c-gateway-openapi-frontend
git branch -D feat/plan-c-frontend
git branch -D feat/plan-d-async-path
git branch -D feat/plan-d-gateway-async
git branch -D feat/plan-d-worker-frontend-integration
git branch -D feat/plan-e-ai-foundation
git branch -D feat/plan-e-gateway-ai
git branch -D feat/plan-e-frontend-ai
git branch -D feat/plan-f-foundation
git branch -D feat/plan-f-features

# Drop this file once every branch in the table is gone
git rm MERGED_BRANCHES.md
git commit -m "chore: remove merged Plan A/B/C branches"
```

> Squash-merge collapses each branch into a single commit on `main`; the
> per-commit history lives only on the feature branch. If you want to dig
> into the granular Plan A or Plan B commits later, do it **before** deleting.
