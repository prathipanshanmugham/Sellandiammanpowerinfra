# Deploying Sellandiamman Power Infra

The stack runs on the same Hostinger VPS as sellandiammantraders.com and sellandiammanestates.com (`srv1413501`, Ubuntu 24.04), behind the nginx that is already there. It uses its own containers, its own MongoDB and its own local port, so the other sites aren't touched.

| Container | Does | Port |
| --- | --- | --- |
| `mongo` | MongoDB 7, own data volume | not exposed |
| `backend` | FastAPI on 8001 (inside Docker only), runs the reminder scheduler | not exposed |
| `web` | Caddy: the built website/ERP/portals, forwards `/api` to the backend, asks the backend for page titles and descriptions (SEO) | `127.0.0.1:8090` |
| `backup` | nightly database dump and uploaded files into `./backups`, 30 days | none |

Ports already used on the server and left alone: 8000, 8001 (host), 3001, 8088/8443 (Estates).

## 1. DNS

At the domain registrar, point `sellandiammanpowerinfra.com` (A record) to the server's IPv4 `76.13.246.159`, and `www` (CNAME) to the bare domain. Wait until `dig +short sellandiammanpowerinfra.com` shows the IP.

## 2. Code and settings

```bash
sudo mkdir -p /opt/sellandiammanpowerinfra && cd /opt/sellandiammanpowerinfra
# read-only deploy key: ssh-keygen -t ed25519 -f /root/.ssh/powerinfra_deploy, add the .pub under GitHub repo -> Settings -> Deploy keys
git clone git@github.com:prathipanshanmugham/Sellandiammanpowerinfra.git .
git config core.sshCommand "ssh -i /root/.ssh/powerinfra_deploy"

cp .env.example .env                       # SITE_ADDRESS=:80, HTTP_BIND=127.0.0.1:8090
cp backend/.env.example backend/.env
chmod 600 .env backend/.env
nano backend/.env
```

In `backend/.env` set at least:

```bash
JWT_SECRET=$(openssl rand -hex 32)
VAULT_KEY=$(openssl rand -base64 32)       # keep a copy somewhere safe off the server; never change it later
ADMIN_EMAIL=you@sellandiammanpowerinfra.com
ADMIN_PASSWORD=a-long-temporary-password
SITE_URL=https://www.sellandiammanpowerinfra.com
CORS_ORIGINS=https://www.sellandiammanpowerinfra.com,https://sellandiammanpowerinfra.com
COOKIE_SECURE=true
SEED_DEMO=false
```

## 3. Start

```bash
docker compose up -d --build
docker compose ps
curl -s http://127.0.0.1:8090/api/health        # {"ok":true,"db":"ok","version":"2026.10.1"}
```

## 4. nginx and HTTPS

```bash
sudo cp deploy/nginx-powerinfra.conf /etc/nginx/sites-available/sellandiammanpowerinfra
sudo ln -s /etc/nginx/sites-available/sellandiammanpowerinfra /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d sellandiammanpowerinfra.com -d www.sellandiammanpowerinfra.com
```

Until certbot adds the HTTPS block, nginx answers `https://` for this name with whichever site has the first certificate; that's expected during setup.

## 5. First sign-in

1. Open `https://www.sellandiammanpowerinfra.com/erp/login` and sign in with `ADMIN_EMAIL` / `ADMIN_PASSWORD`.
2. Profile → set up 2-step sign-in.
3. Remove `ADMIN_PASSWORD` from `backend/.env`, then `docker compose up -d backend`.
4. Users & roles → add the team (each gets a 7-day link to set a password).
5. Company settings → numbering, approval limits, first-reply target, UPI ID and bank details, lead routing by town.
6. Website editor → real phone numbers, licence and GSTIN, the numbers under the hero; publish.

## Day to day

```bash
cd /opt/sellandiammanpowerinfra
git pull && docker compose up -d --build         # update
docker compose logs --tail 200 backend           # logs
./scripts/backup-now.sh                          # extra backup before a big change
./scripts/restore.sh backups/db-<date>.gz backups/uploads-<date>.tgz
```

Copy `backups/` off the server regularly (the nightly job keeps 30 days on the server only).

## Optional connections

All in `backend/.env`; restart the backend after changing them.

- **Email** (`SMTP_*`): set-password links, notifications, enquiry acknowledgements.
- **WhatsApp Business Cloud API** (`WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID`, `WHATSAPP_VERIFY_TOKEN`): acknowledgements, breakdown alerts, approval codes for clients. Webhook URL: `https://www.sellandiammanpowerinfra.com/api/hooks/whatsapp`.
- **Lead webhooks** (`LEAD_WEBHOOK_KEY`): IndiaMART pull/push, JustDial, Meta lead ads, Google Ads lead forms, email forwarders and missed-call services post to `https://www.sellandiammanpowerinfra.com/api/hooks/leads/<indiamart|justdial|meta_ads|google_ads|email|missed_call>?key=<LEAD_WEBHOOK_KEY>`.
- **Spam protection** (`TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET`) and **Google Analytics** (`GA4_ID`).
- **Google Search Console**: add the domain and submit `/sitemap.xml`.
