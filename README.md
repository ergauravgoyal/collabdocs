# CollabDocs

CollabDocs is an API-only collaborative document backend built with Django
REST Framework and PostgreSQL. It supports users, workspaces, role-based
memberships, versioned documents, threaded comments, tags, and audit logs.

## Requirements

- Docker and Docker Compose (recommended), or
- Python 3.12+, PostgreSQL 16+, and the pinned dependencies in
  [`requirements.txt`](./requirements.txt)

## Run with Docker

```bash
docker compose up --build
```

The API is available at `http://localhost:8002`. The Compose file supplies
the database environment to the API container and starts PostgreSQL on host
port `5434`. Migrations run automatically when the API container starts.

Stop the services with:

```bash
docker compose down
```

Add `-v` to `docker compose down` only when you intentionally want to remove
the PostgreSQL volume and all local database data.

## Run locally

Create a PostgreSQL database, then copy the environment template and update
the values for your local database:

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

On Windows PowerShell, activate the virtual environment with:

```powershell
.\.venv\Scripts\Activate.ps1
```

The local server runs at `http://127.0.0.1:8000` by default. To create or
update migrations after a model change:

```bash
python manage.py makemigrations collabdocs
python manage.py migrate
```

PostgreSQL connection values are read from `.env`. Never commit `.env`; use
[`.env.example`](./.env.example) as the template. The Docker Compose
configuration uses the `postgres` service name as the database host inside
the API container, whereas a local process normally uses `localhost`.

## API documentation and Postman

When running with Docker:

- Swagger UI: `http://localhost:8002/api/docs/`
- OpenAPI schema: `http://localhost:8002/api/schema/`

Import the committed
[Postman collection](./CollabDocs.postman_collection.json) and set its
`base_url` variable to `http://localhost:8002` (or
`http://127.0.0.1:8000` for a local server). Replace the placeholder IDs
after creating the related records. The collection contains 17 requests in
the required folders: Users, Workspaces, Documents, Comments, Tags, and
Audit Logs.

### Endpoint reference

- `POST /api/users/`, `GET /api/users/{id}/`
- `POST /api/workspaces/`, `GET /api/workspaces/{id}/`
- `POST/GET /api/workspaces/{id}/members/`
- `GET /api/workspaces/{id}/summary/`
- `POST /api/documents/`, `PUT /api/documents/{id}/`
- `GET /api/documents/?workspace=&status=&tag=&search=`
- `GET /api/documents/{id}/versions/`
- `GET /api/documents/{id}/stats/`
- `POST /api/documents/{id}/tags/`
- `POST/GET /api/comments/`
- `POST /api/tags/`
- `GET /api/audit-logs/?actor=&from=&to=`

Document lists support `workspace`, `status`, `tag`, `search`,
`updated_after`, and `updated_before` query parameters. Comment lists
support `document`; audit-log lists support `actor`, `from`, and `to`.

## Implementation notes

- All model primary keys are UUIDs.
- Workspace creation and owner membership creation are transactional.
- Document saves create a numbered `DocumentVersion` in the same transaction.
- Document create/update events write `AuditLog` records through a
  `post_save` signal.
- `RequestLoggingMiddleware` prints the HTTP method, path, status, and
  elapsed time for every request. These messages appear in the API container
  or local server console.
- Summary and stats actions use database aggregation, and list endpoints
  use related-object query optimisation.

## Verification and demo

Run the Django checks before using the API:

```bash
python manage.py check
```