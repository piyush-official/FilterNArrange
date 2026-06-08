# Secrets — production

Plan H §T9. Where every secret lives, what generates it, and how to rotate.

## Repository secrets (Settings → Secrets and variables → Actions → Secrets)

Used by the deploy workflow (Plan H §T7). All but the SSH key are encrypted at rest.

- `DEPLOY_SSH_KEY` — ED25519 private key authorized on the prod VM as ``filternarrange``
- `DEPLOY_HOST` — public hostname of the prod VM (``filternarrange.example.com``)
- `GHCR_PAT` — PAT with ``read:packages`` (only if the GHCR package is private)

## Repository variables (non-secret)

- `FNA_PUBLIC_HOST` — public host the deploy workflow targets
- `FNA_ACME_EMAIL` — email used by Caddy's ACME

## On-VM (`/etc/filternarrange/prod.env`, mode 0600)

These are runtime secrets the stack reads on every boot.

- `JWT_SECRET` — HMAC secret for spring-jwt. Generate: ``openssl rand -base64 48``
- `POSTGRES_PASSWORD` — DB password for the ``filternarrange`` user
- `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` — MinIO root credentials
- `ACME_EMAIL` — email Caddy registers with Let's Encrypt

## Rotation

| Secret | Cadence | Procedure |
|---|---|---|
| `JWT_SECRET` | 90 days | Add new secret as ``JWT_SECRET_NEW``; gateway accepts both during overlap; flip primary; remove old. (Helper TBD in Plan H follow-up) |
| `POSTGRES_PASSWORD` | Annual or on suspected compromise | ``ALTER USER ... PASSWORD``, update prod.env, ``systemctl restart filternarrange`` |
| `MINIO_*` | Annual | Add a new MinIO service account, update env, redeploy, retire old account |
| `DEPLOY_SSH_KEY` | On staff change | Generate new key, add to ``filternarrange``'s ``authorized_keys``, remove old, update GitHub secret |

## Anti-patterns

- **Never** commit a populated ``prod.env``. ``.gitignore`` ignores ``prod.env``; the only file in the repo is ``prod.env.example``.
- **Never** echo a secret into a workflow log. Mask via ``::add-mask::`` if you must reference one inline.
- **Never** put a secret in a Dockerfile ``ENV`` instruction. Pass via ``--env`` / compose env at run time.
- **Never** reuse an env between staging and prod. Each environment gets its own ``prod.env``.
