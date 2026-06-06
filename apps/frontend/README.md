# apps/frontend

Vite + React + TypeScript SPA. Talks only to the gateway (per spec §2 loose-coupling rule 2).

## Layout (feature-sliced — see spec §6)

- `src/app/` — shell, routing, providers
- `src/pages/` — route components
- `src/features/<feature>/{api,ui,state,index.ts}` — features never import each other
- `src/shared/` — `ui/`, `lib/`, `api/client`

## Local run

```bash
npm install
npm run dev   # http://localhost:5173
```

## Tests

```bash
npm test
```
