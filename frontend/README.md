# Frontend — GitHub Spark App

Place your GitHub Spark application files in this directory.

The Azure Web App is configured with a **Node 20 LTS** runtime. During deployment the workflow runs `npm install` and `npm run build` (if a build script exists in `package.json`).

## Expected structure

```
frontend/
├── package.json
├── index.html       (or public/index.html)
├── src/
│   └── ...          your Spark app source files
└── ...
```

## Environment variables

The frontend Web App has the following app setting injected by the Bicep infrastructure:

| Variable | Value |
|---|---|
| `API_BASE_URL` | `https://<baseName>-api.azurewebsites.net` |

Use this to point API calls at the backend.
