# Deploy

The repository is structured to deploy on Streamlit Community Cloud directly
from GitHub. Runtime dependencies are minimal; the compiled DuckDB file ships
with the repository, so no build step runs at deploy time.

## 1. Push to GitHub

```bash
cd ~/Downloads/Personal/sentinel-fleet-ops

git init
git add .
git commit -m "Initial commit"
git branch -M main

# Create a public repository on GitHub first, then:
git remote add origin git@github.com:ravi-rajpurohit-gh/sentinel-fleet-ops.git
git push -u origin main
```

## 2. Deploy on Streamlit Community Cloud

1. Open https://share.streamlit.io/
2. Click **New app**
3. Repository: `ravi-rajpurohit-gh/sentinel-fleet-ops`
4. Branch: `main`
5. Main file path: `streamlit_app.py`
6. Click **Deploy**

Streamlit Cloud installs only the dependencies in `requirements.txt`
(`streamlit`, `duckdb`, `pandas`, `plotly`). The first deploy takes about
two minutes; subsequent deploys are faster.

## 3. Re-deploy after a data or model change

```bash
.venv/bin/python scripts/generate_data.py
cd dbt && DBT_PROFILES_DIR=. ../.venv/bin/dbt build && cd ..
git add data/sentinel.duckdb dbt/target/run_results.json dbt/target/manifest.json data/raw/
git commit -m "Refresh data and dbt build"
git push
```

Streamlit Cloud auto-redeploys on push to `main`.
