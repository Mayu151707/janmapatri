JANMAPATRI V5 — RENDER DEPLOYMENT PACKAGE

Included files:
- index.html: V4.2 premium interface with autocomplete and tabs
- server.py: Render-ready server (0.0.0.0 + Render PORT), API, place search, health endpoint
- engine.py: LibEphemeris-backed calculations (Lahiri sidereal, whole-sign houses)
- requirements.txt: dependencies
- render.yaml: Render Blueprint configuration
- original-mockup-reference.html: original UI reference

Deployment:
1. Extract this ZIP.
2. Upload all files and folders inside janmapatri-v5-render/ to the ROOT of your GitHub repo.
3. Commit the upload to the main branch.
4. In Render, either use New > Blueprint and select the repo (render.yaml), or use the existing web service.
5. For an existing service, Build Command: pip install -r requirements.txt; Start Command: python server.py; Health Check Path: /health.
6. Python runtime should be 3.13 (Render setting or render.yaml).

Place search uses OpenStreetMap Nominatim. Please use the autocomplete responsibly and avoid excessive searches.
This is a prototype calculation platform. Verify calculations and interpretive content before relying on them.
