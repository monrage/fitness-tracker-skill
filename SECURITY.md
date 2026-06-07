# Security Policy

## Reporting a vulnerability
Please **don't** open a public issue for security problems. Use GitHub's private
reporting: **Security → Report a vulnerability** on this repository
(`https://github.com/monrage/fitness-tracker-skill/security/advisories/new`).
We'll respond as soon as we can.

## How your data is handled
This skill is designed to keep your data yours:

- **Credentials** (Notion token / Google OAuth) live only in your local
  `fitness-config.json`, which is **git-ignored** and never committed. The skill
  is told to display this file so *you* save it to your private Claude Project —
  it is not uploaded anywhere by the project.
- **Records** (meals, workouts, bodyweight) are written only to the backend
  **you** chose — your own Notion, your own Google Sheet, or a local JSON file.
- The bundled code makes outbound calls only to the APIs you enable:
  `api.notion.com`, `sheets.googleapis.com` / `oauth2.googleapis.com`, and
  `*.openfoodfacts.org`. Nothing else.
- No telemetry, analytics, or third-party servers.

## Good practice
- Treat your Notion / Google tokens like passwords; don't paste them into issues,
  screenshots, or PRs.
- Use the most restrictive Notion integration access that works (a single page).
- Prefer **Package managers only** + an explicit domain over **All domains** in
  Claude's sandbox settings.
