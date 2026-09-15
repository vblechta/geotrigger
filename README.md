# GeoTrigger

Track time people spend at named sites. A Flask web app (UI + JSON API) stores accounts, locations, and presence sessions. An Android client signs in with a username, password, and the server’s public URL, then sends a heartbeat only while the device is inside a location radius.

## How it works

Administrators define locations in the web UI: a name, GPS coordinates, and a radius in meters. Field users sign in on Android, grant location permission, and leave tracking running. Every **5 minutes** (configurable globally by an admin) the phone:

1. Loads the location list and ping interval from `GET /api/config`
2. Reads the current GPS fix
3. If the device is inside one or more site radii, posts `POST /api/presence`

The server opens or extends a **presence session** for each matching site. Time on site is estimated as:

`last_ping − first_ping + ping_interval`

A gap longer than two intervals closes the session. The next heartbeat starts a new visit.

Default ping interval is **300 seconds**. Admins change it under **Settings**; clients pick up the new value on the next config refresh.

## Server

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python wsgi.py
```

Open http://127.0.0.1:5000. If the port is taken, run `python wsgi.py` after setting `app.run(..., port=5055)` or:

```bash
PYTHONPATH=. flask --app geotrigger run --debug --host 0.0.0.0 --port 5055
```

The first start creates an administrator:

- username: `admin`
- password: `changeme` (or `ADMIN_USERNAME` / `ADMIN_PASSWORD` env vars)

Change that password before exposing the server. Create field users under **Users**. Only administrators can add locations, change the ping interval, or set the map tile API key (Settings).

### Docker

From the repository root:

```bash
docker compose up --build
```

### Tests

```bash
cd server
pip install -r requirements-dev.txt
pytest
```

### CLI

```bash
cd server
PYTHONPATH=. flask --app geotrigger create-user --username field1 --admin
PYTHONPATH=. flask --app geotrigger set-interval 180
```

## Android client

You do not need to use Android Studio. From the repository root:

```bash
chmod +x android/build.sh
./android/build.sh
```

The first run downloads a JDK (if your system does not have Java 17–21), Gradle, and libraries. When it finishes, the installable file is:

`android/dist/GeoTrigger-debug.apk`

Copy that APK to the phone and open it (allow “Install unknown apps” for the file manager). Or plug the phone in with USB debugging enabled and run:

```bash
./android/build.sh --install
```

Sign-in fields:

- **Server URL** — public base URL, e.g. `https://geotrigger.example.com` (no path). For a phone on the same LAN as your laptop, use `http://192.168.x.x:5000`, not `http://127.0.0.1:5000`.
- **Username / password** — an account from the web app.

After sign-in the app requests location (and notification) permission and starts a foreground service. Heartbeats are sent only while the GPS position falls inside a defined radius. Time totals are shown on the home screen and in the web dashboard.

## HTTP API

Authenticate with `Authorization: Bearer <token>` after login.

| Method | Path | Notes |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness, no auth |
| `POST` | `/api/auth/login` | `{"username","password"}` → `{token,user,ping_interval_seconds}` |
| `POST` | `/api/auth/logout` | Revokes the current token |
| `GET` | `/api/me` | Current user |
| `GET` | `/api/config` | `ping_interval_seconds` + location list (used by the Android client) |
| `GET` | `/api/locations` | Same sites without the interval |
| `POST` | `/api/presence` | `{"latitude","longitude","accuracy_meters?","recorded_at?"}` |
| `GET` | `/api/summary` | Optional `from` / `to` ISO-8601 query params |

Example:

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:5000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"changeme"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["token"])')

curl -s http://127.0.0.1:5000/api/config -H "Authorization: Bearer $TOKEN"
```

## Configuration

Environment variables (see `server/.env.example`):

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Flask secret; generated and stored in `instance/secret_key` if unset |
| `DATABASE_URL` | Default SQLite file in the instance folder |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Bootstrap admin when the database is empty |
| `TZ` | IANA timezone for server-side timestamps and report day bounds (default `Europe/Prague` in Docker). The web UI also converts times in the browser. |

Ping interval bounds: 30–3600 seconds.
