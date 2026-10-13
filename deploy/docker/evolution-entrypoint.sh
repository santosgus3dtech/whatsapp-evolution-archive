#!/bin/bash
# Upstream's deploy_database.sh echoes the complete database URI. Do not use it.
set -euo pipefail
cd /evolution
export DATABASE_URL="$DATABASE_CONNECTION_URI"
if ! npm run db:deploy >/dev/null 2>&1; then
  printf '%s\n' 'Evolution database migration failed; no credentials were logged.' >&2
  exit 1
fi
if ! npm run db:generate >/dev/null 2>&1; then
  printf '%s\n' 'Evolution Prisma generation failed; no credentials were logged.' >&2
  exit 1
fi
exec npm run start:prod
