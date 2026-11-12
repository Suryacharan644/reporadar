# Security policy

## Reporting a vulnerability

Please **do not** open a public issue for security problems. Use GitHub's private vulnerability
reporting on this repository (Security tab → Report a vulnerability). We aim to acknowledge reports
within 5 working days.

## Scope

In scope: the backend API, the Next.js app and its proxy, the GitHub Action runner, and the
Supabase schema. Out of scope: GitHub itself, and denial-of-service attempts against shared
infrastructure.

## Design notes

- Secrets live only in server-side environment variables and are never returned by any endpoint.
- Only public GitHub data is requested and stored.
- Input is validated before any outbound request; search qualifiers are sanitised.
- Shared reports are stored with row-level security and no public access policies.
