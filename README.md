# Log Filter Service

A small FastAPI service for ingesting and filtering log entries — built as
the base application for a hands-on DevOps skill-building project covering
CI/CD, Docker, Kubernetes, and AWS.

## API docs (Swagger UI)

FastAPI auto-generates interactive API docs from the route definitions —
no extra setup needed. Once the app is running:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc** (alternate docs UI): http://localhost:8000/redoc
- **Raw OpenAPI schema:** http://localhost:8000/openapi.json

The bare root path `/` redirects to `/docs` for convenience.

To disable docs in a real production deployment (common for internal
services you don't want publicly documented), set `docs_url=None` and
`redoc_url=None` in the `FastAPI(...)` constructor in `app/main.py`.

## Endpoints

| Method | Path          | Description                                  |
|--------|---------------|-----------------------------------------------|
| GET    | `/health`     | Liveness/readiness check                       |
| POST   | `/logs`       | Ingest a single log entry                      |
| GET    | `/logs`       | List logs, optionally filtered by `level`/`source` |
| GET    | `/logs/{id}`  | Fetch a single log entry                       |
| DELETE | `/logs/{id}`  | Delete a single log entry                      |

## Running locally (dev)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

uvicorn app.main:app --reload
```

Visit http://localhost:8000/docs — `--reload` is dev-only, don't use it
in production (it's slower and not meant for concurrent traffic).

## Running tests

```bash
pytest -v
```

Tests include checks that Swagger UI (`/docs`) and the OpenAPI schema
(`/openapi.json`) are actually being served, not just that the business
logic endpoints work.

## Running with Docker (production-style)

```bash
docker build -t log-filter-service .
docker run -p 8000:8000 log-filter-service
```

The Dockerfile runs the app with **Gunicorn managing Uvicorn workers**
(`gunicorn app.main:app -k uvicorn.workers.UvicornWorker`), which is the
standard production setup — Gunicorn handles worker process management
and restarts, which plain `uvicorn` running alone doesn't do for you.
Worker count is controlled by the `WEB_CONCURRENCY` env var (default 2):

```bash
docker run -p 8000:8000 -e WEB_CONCURRENCY=4 log-filter-service
```

## Deploying

This app is container-first, so any platform that runs a Docker image
works:

- **AWS (ECS/EKS/App Runner):** push the built image to ECR, deploy from
  there. This is the path this project's broader DevOps plan builds
  toward (see roadmap below).
- **Simple PaaS (Render, Railway, Fly.io, Heroku-style platforms):** a
  `Procfile` is included (`web: gunicorn app.main:app -k
  uvicorn.workers.UvicornWorker ...`) for platforms that use that
  convention instead of a Dockerfile directly. Most of these platforms
  also auto-detect and build the Dockerfile if you'd rather use that.
- **Kubernetes:** see the project roadmap below — this is Phase 2 of the
  broader plan.

Whichever platform you use, the app reads `PORT` from the environment in
the Procfile (defaulting to 8000) — make sure that matches what the
platform expects, and confirm `/health` is reachable post-deploy before
pointing real traffic at it.

## Secrets scanning (gitleaks)

Install locally: `brew install gitleaks` (macOS), or grab a binary from the
[gitleaks releases page](https://github.com/gitleaks/gitleaks/releases), or
run via Docker:

```bash
docker run -v $(pwd):/repo zricethezav/gitleaks:latest detect -s /repo
```

Run a scan: `gitleaks detect --source . --verbose`

CI runs this automatically via the `secrets-scan` job on every push/PR to
`development`, `stable`, or `main`.

## CI/CD

`.github/workflows/ci.yml` runs the test suite and a gitleaks secrets scan
on every push/PR to `development`, `stable`, or `main`.

**Branch flow:** `development` → `stable` → `main`

| Branch        | What happens on merge                                                |
|---------------|-----------------------------------------------------------------------|
| `development` | Tests + secrets scan run. No image build. Day-to-day work lands here. |
| `stable`      | Tests + secrets scan run, then the image is built and pushed tagged `stable-<sha>` — a known-good pre-release artifact. |
| `main`        | Tests + secrets scan run, then the image is built and pushed tagged `<sha>` and `latest` — this is the production release. |

**Suggested branch protection rules** (Settings → Branches in GitHub):
- Require the `test` and `secrets-scan` jobs to pass before merging
- Require PR review before merging into `stable` and `main`
- Restrict who can push directly to `main` (merges only, via PR)

## Project roadmap (DevOps skill-building plan)

- [x] Phase 1: Containerize app, build CI/CD pipeline
- [x] Add Gitleaks (secrets scanning) as a required CI gate
- [ ] Add Trivy (vulnerability scanning) as a required CI gate
- [ ] Phase 2: Deploy to Kubernetes (Minikube/kind), implement canary
      rollout with Argo Rollouts or Flagger
- [ ] Phase 3: Deploy to AWS (EKS/ECS), IAM least-privilege audit,
      Secrets Manager integration
- [ ] Phase 4: SBOM generation (Syft), image signing (cosign/Sigstore),
      SLSA provenance, OPA policy gates
