# Oracle Always-Free provisioning — FilterNArrange v1.0.0

Plan H §T8. A reproducible recipe for bringing a fresh OCI ARM Ampere VM
online and getting FilterNArrange answering on a public hostname.

## 0. Manual rehearsal checklist (do once before tagging v1.0.0)

- [ ] Cloudflare account with the target domain (free plan is fine)
- [ ] An ACME-eligible email
- [ ] GitHub PAT with read access to ghcr.io (only if the repo's package
      visibility is private)

## 1. OCI account & shape

- Sign up at oracle.com/cloud/free
- Create a new VM: **VM.Standard.A1.Flex**, 4 OCPU / 24 GB / Ubuntu 22.04
- Generate an SSH keypair and add it to the instance
- Reserve an "ephemeral" public IPv4 for the instance

## 2. Inbound security list

In the VCN's default security list, allow inbound TCP on:

- `22` from your admin IP (NOT 0.0.0.0/0 long-term)
- `80` from 0.0.0.0/0 (ACME HTTP-01 + HTTPS redirect)
- `443` from 0.0.0.0/0

## 3. DNS (Cloudflare free)

Add an `A` record: `filternarrange.example.com → <oci-ip>`. Set proxy
status to **DNS only** (gray cloud) so Caddy can complete ACME HTTP-01.
Flip to proxied once TLS is healthy.

## 4. Host bootstrap

```sh
scp infra/host/bootstrap.sh ubuntu@<ip>:/tmp/
ssh ubuntu@<ip> 'sudo bash /tmp/bootstrap.sh'
ssh ubuntu@<ip> 'sudo -iu filternarrange git clone https://github.com/piyush-official/FilterNArrange.git'
```

## 5. Production env

```sh
sudo cp /home/filternarrange/FilterNArrange/infra/deploy/prod.env.example /etc/filternarrange/prod.env
sudo nano /etc/filternarrange/prod.env   # fill in every "replace-with-..."
sudo chmod 0600 /etc/filternarrange/prod.env
sudo chown root:root /etc/filternarrange/prod.env
```

## 6. Start the stack

```sh
sudo systemctl start filternarrange
sudo systemctl status filternarrange --no-pager
```

Watch logs:

```sh
sudo -iu filternarrange docker compose \
  -f /home/filternarrange/FilterNArrange/infra/docker-compose/docker-compose.yml \
  -f /home/filternarrange/FilterNArrange/infra/docker-compose/docker-compose.prod.yml \
  logs -f --tail=200
```

## 7. Pull Ollama models

Ollama-init pulls the defaults at startup; first pull on a fresh VM takes
~5 minutes for the 8B llama model. Verify:

```sh
docker exec fna-ollama ollama list
```

## 8. Seed the first admin

```sh
docker exec fna-gateway java -jar app.jar seed-prod-admin \
  --email you@example.com --password "$(openssl rand -base64 24)"
```

> ``seed-prod-admin`` CLI is the deferred Plan H §T5 work; until it lands,
> create the admin manually via psql:
>
> ```sh
> docker exec -it fna-postgres psql -U filternarrange -c \
>   "INSERT INTO users (id, email, password_hash, admin) VALUES (gen_random_uuid(), 'you@example.com', '<bcrypt-of-your-pw>', true);"
> ```

## 9. First-boot smoke

```sh
PUBLIC_URL=https://filternarrange.example.com bash tests/smoke/smoke.sh
```

## 10. Hand off to automation

Once the smoke passes, the tag-triggered deploy workflow (Plan H §T7 —
also deferred) takes over future releases.

## 11. Rollback rehearsal

```sh
# Roll back to v0.9.0:
sudo sed -i 's/^FNA_VERSION=.*/FNA_VERSION=v0.9.0/' /etc/filternarrange/prod.env
sudo systemctl restart filternarrange
PUBLIC_URL=https://filternarrange.example.com bash tests/smoke/smoke.sh
```

Practice the rollback path BEFORE tagging v1.0.0.
