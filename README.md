# WhatsNexo

English · [Português (Brasil)](README.pt-BR.md)

A personal archive of messages made available by Evolution API, built with Python/FastAPI, SQLite storage, and a Vue panel.

The panel lets you browse conversations, search messages, track available history imports, and organize your local archive. This distribution includes source code and generic configuration, without messages, credentials, sessions, photos, or data from a real installation.

## Available features

- Paginated conversations and messages, with text and caption search.
- Global search by date range, conversation, message type, and incoming/outgoing direction.
- Favorites, labels, and conversations archived within the panel.
- An indicator for received messages that have not yet been viewed in the archive.
- Webhook capture and periodic reconciliation against messages stored by Evolution API.
- History imports with checkpoints, resumability, and deduplication.
- Panel updates through persisted SSE events.
- Profile photos fetched on demand, when available, with a limited private cache.
- Session login and optional additional accounts with scrypt password hashes.

## Archive limitations

The integration **does not verify or guarantee the complete earlier WhatsApp history**. The History tab shows the earliest and latest available messages, when capture started, and query progress. Completing an Evolution query does not establish that all data from the phone is available.

The service preserves text, captions, and selected message metadata. It does not store the binary content of photos, videos, audio, documents, or stickers sent in conversations, or access the user's collection of saved stickers. Profile photos use a separate, limited cache.

The panel does not send messages. Messages sent by other clients may appear when the integration makes them available. Marking a message as viewed, adding favorites or labels, and archiving conversations affect only the local archive. A conversation's "archived in WhatsApp" state remains unknown when the API does not provide it.

All authenticated users access the same instance and share messages, viewed status, and preferences. There is no per-user data isolation, role-based access, or separation between customers.

## Docker installation

Use Docker with Compose v2 and support for Linux `amd64` containers. Compose includes the archive service, Evolution API 2.3.7, PostgreSQL, and Redis. The Dockerfile builds the panel and installs Python dependencies pinned with hashes. Each service has memory limits; the build process and Docker itself require additional resources.

Run these commands from the repository root:

```powershell
git clone https://github.com/santosgus3dtech/whatsapp-evolution-archive.git
Set-Location whatsapp-evolution-archive
```

Create your private configuration by following the [initial configuration guide (Portuguese)](docs/CONFIGURATION.md#configuração-inicial). The `.env.example` file has empty required fields; the application will not start until they are filled in.

```powershell
docker compose --env-file .env -f deploy/docker/compose.yml config --quiet
docker compose --env-file .env -f deploy/docker/compose.yml up -d --build
docker compose --env-file .env -f deploy/docker/compose.yml ps
Invoke-RestMethod http://127.0.0.1:8097/healthz
```

Open [http://127.0.0.1:8097](http://127.0.0.1:8097) and sign in with the username and password set in `ARCHIVE_USERNAME` and `ARCHIVE_PASSWORD`. By default, the panel is bound to localhost; Compose does not publish ports for the databases or Evolution.

The interface is currently in Portuguese. In the Connection tab (**Conexão**), select **Vincular WhatsApp** (Link WhatsApp) for your chosen instance. For a new instance, the service configures events and a webhook with a secret in its header, without base64 media. If the instance already exists, its configuration is preserved: the service **does not replace the webhook or reset the instance**. Read the [operation guide (Portuguese)](docs/OPERATIONS.md#instância-e-captura) before reusing an instance.

After linking, capture depends on events delivered by the integration. Reconciliation queries messages already stored by Evolution and tries to recover events that did not arrive through the webhook. Use the History tab (**Histórico**) to monitor coverage and request an import of the available history.

Data is stored in named Docker volumes. The published configuration does not use or import data from another installation.

## Development and checks

For development outside the container, use Python 3.12+ and a Node.js version compatible with `apps/panel/package.json` (`>=22.12.0`). The container uses Python 3.12; local verification also used Python 3.13. The commands below use PowerShell and create a local environment:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install --require-hashes -r archive_service/requirements.lock
.venv/Scripts/python.exe -m pip install pytest==8.4.2
.venv/Scripts/python.exe -m pytest -q tests
Set-Location apps/panel
npm ci
npm run build
Set-Location ../..
```

Tests use synthetic data, simulated clients, and temporary directories. They cover ingestion, duplicates, received edits and deletions, authentication, CSRF, events, import resumption, local preferences, and the profile photo cache. They do not pair a phone or prove compatibility with a real WhatsApp installation.

To run the application locally, configure addresses reachable by the Python process, as explained in the [local development guide (Portuguese)](docs/CONFIGURATION.md#desenvolvimento-local). The Python code does not load `.env` automatically.

## Documentation

The detailed guides and third-party notice inventory are currently in Portuguese:

- [Configuration](docs/CONFIGURATION.md): environment variables, secrets, HTTPS access, local execution, and additional users.
- [Architecture](docs/ARCHITECTURE.md): data flow, persistence, events, and core API contracts.
- [Operations](docs/OPERATIONS.md): health checks, coverage, errors, and data preservation.
- [Third-party notices](THIRD_PARTY_NOTICES.md): components, versions, and preserved license texts.

## License and attribution

This application uses **Evolution API 2.3.7** as an external service. See the [official project](https://github.com/evolution-foundation/evolution-api), the [exact license for version 2.3.7](https://github.com/evolution-foundation/evolution-api/blob/2.3.7/LICENSE), including its additional conditions, and the preserved text in [licenses/external/evolution-api-2.3.7-LICENSE.txt](licenses/external/evolution-api-2.3.7-LICENSE.txt).

A reuse license for the original application source is pending the owner's decision. Public availability does not itself grant permission to redistribute, modify, or sublicense that source. See [LICENSE.md](LICENSE.md). Dependencies retain their own licenses and notices; these do not define the license of the original application source.
