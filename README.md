# BUX Analysis Migration

This repository now contains two parts:

- `python/`: the original Streamlit app
- `web/`: the new Node + TypeScript + React migration target

The web app is being built as a local-only, file-based workspace. Uploaded CSVs and generated state stay on disk under `web/data/` and are ignored by git.

## Current direction

- Modernized React UI
- Local file persistence instead of a database
- Page-by-page migration from the Python app
- Same portfolio domain logic, rewritten in TypeScript

## Web app

The first migration step lives in `web/` and includes:

- App shell and navigation
- CSV upload endpoint
- Local workspace state storage
- Typed portfolio parsing and summary metrics
- A dashboard starting point for the first pages

To run it locally once Node is installed:

```bash
cd web
npm install
npm run dev
```

## Python app

The Streamlit version remains in `python/` for reference during the migration.
