# Deploying the dashboard (Streamlit Community Cloud)

**Live demo:** https://blackout-mesh-cqdey6y4jgs9uxarecjpt6.streamlit.app/

Streamlit Community Cloud only runs one process — the app itself — so
it can't also run `backend/run_gateway.py` alongside it the way a
local demo does. For a hosted link, the dashboard has a **standalone
demo mode**: set one environment variable/secret and it runs the
built-in scenario simulator in a background thread inside itself,
cycling through all 5 scenarios automatically. No hardware, no
separate process.

## Steps (for a fresh deploy)

1. Go to **https://share.streamlit.io** and sign in with GitHub (the
   same account this repo lives under).
2. Click **New app** (or **Create app**).
3. Fill in:
   - **Repository**: `raynaagarwal01-rgb/Blackout-Mesh`
   - **Branch**: `main`
   - **Main file path**: `dashboard/app.py`
4. Click **Advanced settings** *before* deploying, and paste this into
   the **Secrets** box (TOML format):
   ```toml
   BLACKOUT_MESH_STANDALONE_DEMO = "true"
   ```
5. Click **Deploy**. The first build takes a minute or two (installing
   `requirements.txt`, including scikit-learn).

That's it — the deployed app is fully self-contained and will cycle
through normal → overload → interruption → intermittent →
connectivity-loss on its own, the same as running
`python backend/run_gateway.py --source simulator --scenario auto`
locally.

## Notes

- Free-tier Streamlit Cloud apps go to sleep after a period of
  inactivity; opening the link again shows a "wake up" button, which
  takes a few seconds.
- Without the `BLACKOUT_MESH_STANDALONE_DEMO` secret set, the deployed
  app will just show "Waiting for telemetry" forever, since nothing is
  feeding it data — that variable is what makes it self-sufficient.
- The live demo above was originally deployed from the PR's feature
  branch. If it's ever still tracking a branch other than `main`
  (check **Manage app → Settings → General → Branch**), point it at
  `main` — Streamlit Cloud only redeploys from whatever branch is
  configured there, so it won't pick up new pushes to `main`
  otherwise.
