# Self-hosted GitHub Actions runner (GCP VM) — one-time setup

CI/CD deploys by running a **self-hosted runner on the VM itself**. The `Deploy to GCP VM`
workflow (`.github/workflows/deploy.yml`) fires on every push to `master` that touches
`backend/**`, `frontend/**`, `docker-compose.yml`, or the deploy script, fast-forwards the
repo on the VM to that commit, and runs `scripts/deploy.sh` — which rebuilds **only the
changed service(s)** and restarts them behind the existing nginx entrypoint.

No SSH keys or cloud secrets are involved: the job runs locally on the box.

## Prerequisites on the VM (already provisioned)

- Docker + `docker compose` v2, `git`, `curl`.
- The repo cloned at a stable path with a working `git fetch origin` (deploy key or
  cached HTTPS token if the repo is private).
- `.env` and `infra/.env` filled in; `backend/data/` present (bind-mounted DB + blobs).
- The infra stack has been started at least once (`make infra-up-d`).

The workflow defaults `DEPLOY_DIR` to `/home/meomeocoj/big-flag-advanced-rag` (this VM's
clone path). Override with a repo variable if it moves: **GitHub → Settings → Secrets and
variables → Actions → Variables → New** → `DEPLOY_DIR = /your/path/big-flag-advanced-rag`.

## 1. Install & register the runner

From **GitHub → Settings → Actions → Runners → New self-hosted runner** copy the token,
then on the VM (run as the *deploy user*, not root):

```bash
mkdir -p ~/actions-runner && cd ~/actions-runner
# Use the download URL/version GitHub shows on that page:
curl -o runner.tar.gz -L https://github.com/actions/runner/releases/download/v2.XXX.X/actions-runner-linux-x64-2.XXX.X.tar.gz
tar xzf runner.tar.gz

# Register against THIS repo. --labels self-hosted is implicit; keep default.
./config.sh --url https://github.com/BigFlag-Ai-For-Vietnam/big-flag-advanced-rag --token <RUNNER_TOKEN>
```

## 2. Grant the runner Docker access

The runner user must run docker without sudo:

```bash
sudo usermod -aG docker "$USER"
# log out/in (or `newgrp docker`) so the group takes effect before starting the runner
```

## 3. Run the runner as a service (survives reboot)

```bash
cd ~/actions-runner
sudo ./svc.sh install "$USER"   # install systemd unit as the deploy user
sudo ./svc.sh start
sudo ./svc.sh status
```

## 4. Verify

- **GitHub → Settings → Actions → Runners** shows the runner **Idle / green**.
- Push a trivial change under `backend/` or `frontend/` to `master`, or use
  **Actions → Deploy to GCP VM → Run workflow** (manual dispatch rebuilds both services).
- Watch the run; the final step health-checks `http://localhost/api/health` and fails
  loudly (with `docker compose ps` + backend logs) if the app didn't come up.

## Manual deploy on the VM (no CI)

```bash
cd "$DEPLOY_DIR"
git pull
./scripts/deploy.sh                 # auto-detect via DEPLOY_BEFORE/AFTER, else rebuild both
./scripts/deploy.sh backend         # force just backend (+ retrieval-mcp)
./scripts/deploy.sh frontend
```

## Notes

- **Concurrency**: overlapping deploys are serialized (`concurrency: deploy-master`).
- **Disk**: each deploy runs `docker image prune -f` to drop dangling images.
- **Infra untouched**: the deploy only rebuilds `backend` / `retrieval-mcp` / `frontend`;
  qdrant/mlflow/rustfs/postgres/nginx keep running. It runs `infra up -d` (no `--build`)
  only to ensure they're alive.
- **Data safety**: SQLite DB + PDFs live in the bind-mounted `backend/data/` on the VM and
  are never touched by `git reset --hard` (they're gitignored) or by image rebuilds.
