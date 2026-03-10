# Frontend — GitHub Spark App

The web UI for the URL Summary Agent built with [GitHub Spark](https://github.com/features/spark), React 19, and Tailwind CSS 4.

The Azure Web App is configured with a **Node 22 LTS** runtime. During deployment the workflow runs `npm install` and `npm run build`, passing `VITE_API_URL` so the frontend knows where the backend API lives.

## Local development

```bash
cd frontend
npm install
VITE_API_URL=http://localhost:8000 npm run dev
```

## Environment variables

| Variable | Set at | Purpose |
|---|---|---|
| `VITE_API_URL` | Build time | Backend API base URL (e.g. `https://websummariser-api.azurewebsites.net`) |
