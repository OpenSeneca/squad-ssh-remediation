# Squad Dashboard

A lightweight HTTP dashboard for monitoring squad agent status and activity across multiple OpenClaw agents.

## Overview

The Squad Dashboard provides:
- **Real-time status monitoring** for all 5 squad agents (Seneca, Marcus, Galen, Archimedes, Argus)
- **Status API endpoint** at `/api/status` returning JSON data
- **Auto-refreshing HTML frontend** displaying agent cards with status indicators
- **Beacon-based architecture** - agents push status via cron every 5 minutes
- **Zero dependencies** - uses only Node.js built-in modules

## How It Works

1. **Status Beacons**: Each agent runs `status-beacon-v2.sh` via cron every 5 minutes
2. **Data Collection**: Beacons push JSON status to `~/.openclaw/dashboard-data/beacons/`
3. **Server Service**: The dashboard server reads beacon files and serves them via API
4. **Frontend Display**: HTML page auto-refreshes every 60 seconds showing current status

**Note**: The beacon script has been upgraded to V2 with improved OpenClaw detection. See [STATUS-BEACON-V2.md](STATUS-BEACON-V2.md) for details.

## Installation & Deployment

### Local Testing

```bash
# Install
cd ~/.openclaw/workspace/tools/squad-dashboard
npm install  # No dependencies needed - creates package.json

# Run locally
node server.js
# Or on a different port:
PORT=3001 node server.js
```

### Deploy to Forge

Using squad-deployer:

```bash
# Test deployment first with dry-run simulator
cd ~/.openclaw/workspace/tools/squad-deployer
./dry-run-simulator.py squad-dashboard --port 3000

# Deploy to forge
./squad-deployer.py deploy squad-dashboard --port 3000
```

Or using the provided deploy script:

```bash
cd ~/.openclaw/workspace/tools/squad-dashboard
./deploy.sh
```

## API Endpoints

### `/api/status` (GET)
Returns complete status summary and beacon data:

```json
{
  "summary": {
    "total": 5,
    "active": 3,
    "idle": 1,
    "down": 1,
    "last_updated": "2026-04-29T16:55:30Z",
    "stale_seconds": 0
  },
  "beacons": [
    {
      "agent": "Archimedes",
      "type": "Engineering",
      "host": "archimedes-squad",
      "status": "active",
      "last_activity_hours": 0,
      "today_output_count": 521,
      "last_output": "status-beacon.sh",
      ...
    },
    ...
  ],
  "timestamp": "2026-04-29T16:55:30Z"
}
```

### `/health` (GET)
Health check endpoint for monitoring systems:

```json
{
  "status": "ok",
  "timestamp": "2026-04-29T16:55:30Z"
}
```

### `/api/beacon/{agentName}` (GET)
Get detailed status for a specific agent:

```bash
curl http://forge:3000/api/beacon/Archimedes
```

## Beacon Data

Beacon files are JSON documents stored in `~/.openclaw/dashboard-data/beacons/{AgentName}.json`.

**See Also**: [STATUS-BEACON-V2.md](STATUS-BEACON-V2.md) for the improved beacon script documentation.

```json
{
  "timestamp": "2026-04-29T16:55:01Z",
  "agent": "Archimedes",
  "type": "Engineering",
  "host": "archimedes-squad",
  "status": "active",
  "openclaw_status": "active",
  "last_learning": "seed-squad-tools-ideas.md",
  "last_memory": "2026-04-29.md",
  "last_code_file": "/home/.../status-beacon.sh",
  "last_output": "status-beacon.sh",
  "last_activity_source": "code",
  "last_activity_hours": 0,
  "today_output_count": 521
}
```

## Status Indicators

- **GREEN (active)**: Agent has produced output within last 2 hours
- **YELLOW (idle)**: Agent has produced output within last 6 hours but not 2 hours
- **RED (down)**: No activity in 6+ hours or OpenClaw definitively down

**Note**: Status is activity-based (see [STATUS-BEACON-V2.md](STATUS-BEACON-V2.md) for details)

## Systemd Service

The dashboard runs as a systemd service:

```bash
sudo systemctl status squad-dashboard
sudo journalctl -u squad-dashboard -f
```

## Configuration

Environment variables:
- `PORT`: Server port (default: 3000)
- `BEACONS_DIR`: Directory containing beacon JSON files (default: `~/.openclaw/dashboard-data/beacons/`)
- `NODE_ENV`: Set to `production` for production deployments

## Maintenance

- Beacons are refreshed automatically every 30 seconds
- Frontend auto-refreshes every 60 seconds
- Old beacon files are overwritten on each cron run
- No database required - file-based storage

## Troubleshooting

### Dashboard not showing agent data
- Check that the agent's cron job for status-beacon-v2.sh is running
- Verify beacon files exist in `~/.openclaw/dashboard-data/beacons/`
- Check file permissions on beacons directory
- Test beacon script: `~/.openclaw/status-beacon-v2.sh`

### Port already in use
```bash
sudo lsof -i :3000
sudo systemctl stop squad-dashboard
```

### Beacon files not updating
- Check cron entries: `crontab -l`
- Test beacon script manually: `~/.openclaw/status-beacon-v2.sh`
- Check file permissions on beacon directory
- See [STATUS-BEACON-V2.md](STATUS-BEACON-V2.md) for troubleshooting

## Files

- `server.js` - Main HTTP server
- `status-beacon-v2.sh` - Improved beacon script for agents to run via cron
- `STATUS-BEACON-V2.md` - Documentation for the V2 beacon script
- `package.json` - Node.js package manifest
- `squad-dashboard.service` - Systemd service file
- `deploy.sh` - Deployment script for forge
- `deploy-local.sh` - Local deployment script
- `integration-tests.sh` - Test suite

## License

MIT
