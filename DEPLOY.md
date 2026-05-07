# Deploy to Streamlit Cloud

The repo is ready to deploy. Follow these steps to get a public URL.

## 1. Push to GitHub

```bash
cd ~/Downloads/Personal/sentinel-fleet-ops

git init
git add .
git commit -m "Initial commit: Sentinel Fleet Ops demo"
git branch -M main

# Create a new repo on GitHub first (e.g. sentinel-fleet-ops, public),
# then add the remote and push:
git remote add origin git@github.com:ravi-rajpurohit-gh/sentinel-fleet-ops.git
git push -u origin main
```

## 2. Deploy on Streamlit Cloud

1. Go to https://share.streamlit.io/
2. Click **"New app"**
3. Repository: `ravi-rajpurohit-gh/sentinel-fleet-ops`
4. Branch: `main`
5. Main file path: `streamlit_app.py`
6. Click **"Deploy"**

Streamlit Cloud reads `requirements.txt` and installs only the runtime deps
(streamlit, duckdb, pandas, plotly). dbt is **not** installed at runtime —
the compiled DuckDB file (`data/sentinel.duckdb`) is checked into git, and the
app reads from it directly.

The first deploy takes ~2 minutes. Subsequent deploys are fast (under a minute).

## 3. After deploy

- Add the live URL to `README.md` (replace the `_(deploy URL added...)_` placeholder).
- Drop the URL into your conversation with Justin during the 3 PM call.
- Optionally: add a project card on the portfolio at
  `~/Downloads/Personal/portfolio/src/data/projects.ts` — but only after you've
  used it in the call and decided it's worth featuring.

## 4. Re-deploying after data tweaks

If you change the generator or add models:

```bash
.venv/bin/python scripts/generate_data.py
cd dbt && DBT_PROFILES_DIR=. ../.venv/bin/dbt build && cd ..
git add data/sentinel.duckdb dbt/target/run_results.json dbt/target/manifest.json data/raw/
git commit -m "Refresh data + dbt build"
git push
```

Streamlit Cloud auto-redeploys on push.
