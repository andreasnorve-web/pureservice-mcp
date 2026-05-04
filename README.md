# Pureservice MCP

MCP-server for Pureservice IT service management. Køyrer både lokalt
(stdio for Claude Desktop) og over HTTP (Railway, Ayfie).

Default er **read-only**. Skrive-tools blir berre eksponert når
`PURESERVICE_READ_ONLY=false`.

## Innhald

- 7 read-tools: list/søk/hent tickets, list/hent users, statistikk
- 4 write-tools (når aktivert): create/update/assign tickets

## Lokal køyring (Claude Desktop)

```bash
pip install -e .
cp .env.example .env
# fyll inn PURESERVICE_TENANT og PURESERVICE_API_KEY
pureservice-mcp
```

I `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pureservice": {
      "command": "pureservice-mcp",
      "env": {
        "PURESERVICE_TENANT": "vanylven",
        "PURESERVICE_API_KEY": "din-nøkkel",
        "PURESERVICE_API_BASE_PATH": "/agent/api",
        "PURESERVICE_READ_ONLY": "true"
      }
    }
  }
}
```

## Deploy til Railway

Same mønster som SSB MCP:

1. **Push prosjektet til GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial Pureservice MCP"
   git remote add origin git@github.com:<din-bruker>/pureservice-mcp.git
   git push -u origin main
   ```

2. **Railway → New Project → Deploy from GitHub** og vel repoet

3. **Sett miljøvariablar** under Variables:

   | Variabel                       | Verdi                              |
   |--------------------------------|------------------------------------|
   | `PURESERVICE_TENANT`           | `vanylven`                         |
   | `PURESERVICE_API_KEY`          | `<din-nøkkel>`                     |
   | `PURESERVICE_API_BASE_PATH`    | `/agent/api`                       |
   | `PURESERVICE_READ_ONLY`        | `true`                             |

4. Railway les `railway.json` og `Procfile`, byggjer med Nixpacks (Python 3.11),
   og startar HTTP-serveren på `$PORT`.

5. **Generate Domain** under Settings → Networking. MCP-endepunktet blir då:
   ```
   https://<ditt-prosjekt>.up.railway.app/mcp
   ```

## Aktivere skrive-tools

Sett `PURESERVICE_READ_ONLY=false` i Railway og redeploy. Då blir
`create_ticket`, `update_ticket`, `update_ticket_status` og `assign_ticket`
tilgjengelege.

⚠️ Skrive-tools mutterer ekte data. Test alltid med ein test-tenant først,
eller bruk filter på agent-rolle/avdeling for å avgrense skadeområdet.

## Autentisering på Railway-endepunktet

Du sa du veit korleis – så det er ditt val (Cloudflare Access, gateway-token i
miljøvariabel + middleware, eller IP-allowlist på Ayfie-sida).

## Tilgjengelege tools

Read:
- `list_tickets(filter_expr, sort, include, limit)` – søk og filtrer ticketsane
- `get_ticket(ticket_id, include)` – hent ein enkelt ticket
- `search_tickets(query, limit)` – fritekstsøk i emne
- `list_users(filter_expr, role, limit)` – list brukarar
- `get_user(user_id)` – hent ein brukar
- `count_tickets_by_status()` – dashboard-tal
- `list_statuses()` – alle ticket-statusar

Write (krev `READ_ONLY=false`):
- `create_ticket(...)` – lag ny ticket
- `update_ticket(ticket_id, ...)` – oppdater felt
- `update_ticket_status(ticket_id, status_id)` – berre status
- `assign_ticket(ticket_id, agent_user_id)` – tildel til agent

## Filteruttrykk

Pureservice støttar:
- `status.name == "Open"`
- `priorityId == 3 AND assignedUserId == 42`
- `subject.Contains("nettverk")`
- `created > "2025-01-01"`

## Tests

```bash
pip install -e ".[dev]"
pytest
```

## Standalone smoke test

`test_pureservice_local.py` køyrer mot ekte Pureservice utan å installere MCP-en.
Bra for å verifisere at API-nøkkelen er rett:

```bash
$env:PURESERVICE_API_KEY = 'din-nøkkel'
py test_pureservice_local.py
```
