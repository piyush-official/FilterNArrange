# filternarrange-analysis-chart-suggest

Schema-driven Vega-Lite chart suggestion. Walks each pair of columns and
proposes a chart based on the pair's type tags:

| Left | Right | Suggestion | Score |
|---|---|---|---|
| temporal | numeric | line | 0.95 |
| categorical | numeric | bar | 0.85 |
| numeric | numeric | scatter (`point`) | 0.7 |

Returns a `charts` payload sorted by descending score.
