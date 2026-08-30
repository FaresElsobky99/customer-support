# Customer Support Frontend

A small Angular frontend for the project's existing FastAPI customer-support API.

## Start locally

Start the FastAPI backend from the repository root:

```bash
uv run uvicorn backend.app.api_main:app --reload
```

Then start Angular in another terminal:

```bash
cd frontend
npm install
npm start
```

Open `http://localhost:4200`. The frontend expects the API at
`http://localhost:8000`.

## Configuration

The API base URL is kept in one place:

```text
src/environments/environment.ts
```

Change that value when the backend is hosted somewhere else.

## Routes

- `/login` — account login
- `/dashboard` — navigation and API health status
- `/profile` — authenticated customer profile
- `/tickets` — role-aware ticket list, create-ticket form, and admin status actions
- `/customers` — admin-only customer list

## Build

```bash
npm run build
```

The production files are written to `dist/frontend/`.
