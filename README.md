# ntl-mcp

Independent MCP server for **NTULearn** (NTU Singapore’s Blackboard Learn instance). It talks to the public Blackboard REST API over your own session cookie.


## What it does

- List enrolled courses
- Walk / search a course content tree
- Read announcements, calendar due dates, and gradebook columns
- Download files under a folder you choose
- Inline-read small text/PDF/Office files (large decks must be downloaded)

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- A logged-in NTULearn session

On **Windows**, Chrome and Edge cookies cannot be read (App-Bound Encryption). Use Firefox, or paste `BbRouter` once into the OS credential store.

## Install

```bash
uv sync
```

Save a cookie (DevTools → Application → Cookies → `ntulearn.ntu.edu.sg` → `BbRouter`):

```bash
uv run ntl-save-cookie "expires:...."
```

Do not commit that value. Do not put it in GitHub.

## Cursor

User MCP config (`~/.cursor/mcp.json` on Windows: `%USERPROFILE%\.cursor\mcp.json`).

After `uv sync`, the Windows entry that this machine uses:

```json
{
  "mcpServers": {
    "ntl": {
      "command": "F:/ntulearn/.venv/Scripts/ntl-mcp.exe",
      "env": {
        "NTULEARN_DOWNLOAD_DIR": "F:/ntulearn/courses"
      }
    }
  }
}
```

Portable form (any OS), if `uv` is on PATH:

```json
{
  "mcpServers": {
    "ntl": {
      "command": "uv",
      "args": ["--directory", "/path/to/ntl-mcp", "run", "ntl-mcp"],
      "env": {
        "NTULEARN_DOWNLOAD_DIR": "/path/to/courses"
      }
    }
  }
}
```

Restart Cursor (or toggle the MCP server) after saving. Do **not** put `NTULEARN_COOKIE` in this file; use `uv run ntl-save-cookie` instead.

Optional env:

| Variable | Purpose |
|---|---|
| `NTULEARN_COOKIE` | Fallback if the credential store is empty |
| `NTULEARN_DOWNLOAD_DIR` | Default download root (otherwise `~/NTULearn/courses`) |
| `NTULEARN_BASE_URL` | Unused by most students; API host is NTULearn |

## Tools

`ntl_list_courses`, `ntl_get_course_contents`, `ntl_search_course_content`, `ntl_get_announcements`, `ntl_get_upcoming`, `ntl_get_gradebook`, `ntl_download_file`, `ntl_read_file_content`.

Suggested download layout:

`NTULEARN_DOWNLOAD_DIR/<courseCode>/<folder>/`

## Responsible use

- You are using your own LMS account. Check NTU IT policy before you rely on this.
- The cookie stays on your machine and is sent only to `ntulearn.ntu.edu.sg`.
- Tool results go to your MCP host (for example Cursor) and may be sent to that host’s model provider.
- Do not share `BbRouter` values.
