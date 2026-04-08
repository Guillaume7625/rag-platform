# Deploying on an OVH VPS

Step-by-step guide to deploy the RAG platform on a fresh **OVH VPS-1**
(4 vCPU / 8 Go RAM / 75 Go SSD / Ubuntu 25.04) at
**`rag.marinenationale.cloud`**.

The architecture is sized for this VPS:
- Generation: **Anthropic Messages API** (Claude Haiku / Sonnet)
- Embeddings: **Voyage AI** (`voyage-3` + `rerank-2-lite`)
- No ML model runs in the compose, so the whole stack fits in ~5 Go RAM.

---

## 0. Prerequisites

| Item | What you need |
|---|---|
| **OVH VPS** | VPS-1 (or larger), Ubuntu 24.04 / 25.04, root SSH access |
| **DNS** | Permission to add an A record on `marinenationale.cloud` |
| **Anthropic API key** | https://console.anthropic.com → Workspace → API keys |
| **Voyage API key** | https://www.voyageai.com → Sign up → API keys (free tier covers small workloads) |
| **Domain email** | An address to register with Let's Encrypt (any valid mailbox) |

---

## 1. Point the sub-domain at the VPS

In your DNS provider for `marinenationale.cloud`, add:

| Type | Name | Value | TTL |
|---|---|---|---|
| `A` | `rag` | `141.94.33.31` | 300 |

(Optional `AAAA` for IPv6: `2001:41d0:20a:900::1166`.)

Wait until `dig +short rag.marinenationale.cloud` returns the VPS IP before
moving on. Caddy will fail to obtain a certificate otherwise.

---

## 2. Bootstrap the VPS

SSH in as `root` (or any user that can `sudo`):

```bash
ssh root@141.94.33.31
```

Install git and clone the repo into `/opt/rag-platform`:

```bash
apt-get update && apt-get install -y git
git clone https://github.com/Guillaume7625/rag-platform.git /opt/rag-platform
```

Run the first-setup script:

```bash
sudo bash /opt/rag-platform/infra/prod/scripts/first-setup.sh
```

It does, idempotently:

- updates apt and applies security upgrades
- installs Docker CE + the compose plugin, ufw, fail2ban, unattended-upgrades
- locks the firewall down to ports 22 / 80 / 443
- creates `/etc/rag-platform/secrets.env` from the template

The first run prints the path to the secrets file and **exits**, so you can
fill it in before deploying.

---

## 3. Fill in the secrets

```bash
sudo nano /etc/rag-platform/secrets.env
```

You need to replace every `REPLACE_ME`:

| Variable | How to generate / where to get |
|---|---|
| `POSTGRES_PASSWORD` | `openssl rand -base64 32` |
| `MINIO_ROOT_PASSWORD` | `openssl rand -base64 32` |
| `JWT_SECRET` | `openssl rand -hex 64` |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com |
| `VOYAGE_API_KEY` | https://www.voyageai.com |
| `ACME_EMAIL` | A real address (Let's Encrypt sends expiry warnings) |

Make sure `DOMAIN=rag.marinenationale.cloud` is correct.

Lock the file:

```bash
sudo chmod 600 /etc/rag-platform/secrets.env
sudo chown root:root /etc/rag-platform/secrets.env
```

Re-run the first-setup script — this time it installs the systemd unit and
finishes:

```bash
sudo bash /opt/rag-platform/infra/prod/scripts/first-setup.sh
```

---

## 4. Deploy

```bash
sudo bash /opt/rag-platform/infra/prod/scripts/deploy.sh
```

This:

1. `git pull` (fast-forward to `origin/main`)
2. builds api / worker / web images locally
3. starts postgres / redis / qdrant / minio and waits for postgres to be
   healthy
4. runs `alembic upgrade head` against the fresh DB
5. starts api / worker / web / caddy
6. prunes dangling images

Caddy will **automatically obtain a Let's Encrypt certificate** for
`rag.marinenationale.cloud` on first start. This typically takes 30-60
seconds. Watch with:

```bash
docker compose -f /opt/rag-platform/infra/prod/docker-compose.prod.yml \
               --env-file /etc/rag-platform/secrets.env \
               logs -f caddy
```

---

## 5. Seed and verify

Create the demo tenant + user:

```bash
docker compose -f /opt/rag-platform/infra/prod/docker-compose.prod.yml \
               --env-file /etc/rag-platform/secrets.env \
               exec api python -m app.scripts.seed
```

You should now be able to:

- open https://rag.marinenationale.cloud
- log in as `demo@rag.local` / `demo1234`
- upload a small `.md` or `.pdf`, watch it transition to `indexed`
- ask a question and get an answer with citations

Health check from anywhere:

```bash
curl -i https://rag.marinenationale.cloud/health
# 200 OK { "status": "ok" }
```

---

## 6. Backups

The platform ships with a backup script that dumps Postgres, snapshots
Qdrant, and mirrors MinIO into `/var/backups/rag-platform/<timestamp>/`.

Add to root's crontab (`sudo crontab -e`):

```cron
15 3 * * * /opt/rag-platform/infra/prod/scripts/backup.sh >> /var/log/rag-backup.log 2>&1
```

Retention is 14 days by default; tune `RETENTION_DAYS` in the script or via
environment.

In addition, **enable OVH's automated VPS snapshot** in the Manager — it
gives you a free disaster-recovery layer.

To restore:

```bash
sudo bash /opt/rag-platform/infra/prod/scripts/restore.sh \
  /var/backups/rag-platform/20260408-031500
```

---

## 7. Updates

To deploy a new version:

```bash
sudo bash /opt/rag-platform/infra/prod/scripts/deploy.sh
```

The script `git pull`s, rebuilds, runs migrations and restarts. It is safe
to run while the platform is serving users — only api/worker/web are
restarted; postgres/qdrant/minio stay up.

---

## 8. Operate

| Action | Command |
|---|---|
| Status | `docker compose -f /opt/rag-platform/infra/prod/docker-compose.prod.yml --env-file /etc/rag-platform/secrets.env ps` |
| Tail logs | `… logs -f --tail=100` |
| Tail one service | `… logs -f --tail=100 api` |
| Shell into api | `… exec api bash` |
| Run alembic | `… exec api alembic upgrade head` |
| Stop everything | `sudo systemctl stop rag-platform` |
| Start at boot | `sudo systemctl enable rag-platform` |

---

## 9. Resource budget recap

| Service | Memory limit | Notes |
|---|---|---|
| postgres | 768 Mo | metadata + ACL + conversations |
| redis | 192 Mo | celery broker / result + cache |
| qdrant | 1.5 Go | vector store |
| minio | 512 Mo | raw documents |
| api | 512 Mo | FastAPI, 2 uvicorn workers |
| worker | 768 Mo | Celery, 2 concurrency, OCR libs |
| web | 512 Mo | Next.js standalone |
| caddy | 128 Mo | TLS reverse proxy |
| **Total** | **~4.9 Go** | leaves ~3 Go headroom on 8 Go RAM |

If you outgrow the VPS-1, the upgrade path is straightforward:
- VPS-2 (8 vCPU / 16 Go) for more concurrent users
- Move Postgres to OVH Managed PostgreSQL when you cross ~50 Go data
- Add a CDN in front of Caddy if you serve large doc previews
