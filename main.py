#!/usr/bin/env python3
"""
Squad SSH Remediation Workflow
Tracks SSH deployment issues, generates checklists, monitors progress.
For Seneca/Clutch to resolve SSH key deployment across squad agents.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Squad agent configs
AGENTS = {
    "seneca": {"host": "100.104.11.21", "port": 22},
    "galen": {"host": "100.101.11.80", "port": 22},
    "argus": {"host": "100.119.129.154", "port": 22},
    "marcus": {"host": "100.103.231.173", "port": 22},
}

STATE_FILE = Path.home() / ".openclaw" / "workspace" / "tools" / "squad-ssh-remediation" / "state.json"
OUTPUT_DIR = Path.home() / ".openclaw" / "workspace" / "outputs"


class SSHRemediation:
    def __init__(self):
        self.state = self._load_state()
        self.state.setdefault("checks", {})
        self.state.setdefault("issues", {})
        self.state.setdefault("resolved", {})
        self.state.setdefault("last_check", None)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            with open(STATE_FILE) as f:
                return json.load(f)
        return {}

    def _save_state(self):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=2, default=str)

    def _run_ssh(self, agent: str, cmd: str, timeout: int = 5) -> tuple:
        """Run SSH command, return (success, output)"""
        config = AGENTS.get(agent)
        if not config:
            return False, f"Unknown agent: {agent}"

        ssh_cmd = [
            "ssh",
            "-o", "ConnectTimeout=5",
            "-o", "StrictHostKeyChecking=no",
            "-p", str(config["port"]),
            f"ubuntu@{config['host']}",
            cmd,
        ]

        try:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "Connection timeout"
        except Exception as e:
            return False, str(e)

    def check_connectivity(self, agent: str) -> dict:
        """Check if agent host is reachable"""
        config = AGENTS.get(agent)
        if not config:
            return {"agent": agent, "reachable": False, "error": "Unknown agent"}

        ping_cmd = ["ping", "-c", "1", "-W", "3", config["host"]]
        try:
            subprocess.run(ping_cmd, capture_output=True, timeout=5)
            return {"agent": agent, "reachable": True}
        except subprocess.TimeoutExpired:
            return {"agent": agent, "reachable": False, "error": "Host unreachable"}
        except Exception as e:
            return {"agent": agent, "reachable": False, "error": str(e)}

    def check_ssh_auth(self, agent: str) -> dict:
        """Check SSH authentication status"""
        success, output = self._run_ssh(agent, "echo 'auth-ok'", timeout=5)
        return {
            "agent": agent,
            "auth": "ok" if success and "auth-ok" in output else "fail",
            "error": output if not success else None,
        }

    def check_authorized_keys(self, agent: str) -> dict:
        """Check if public key is in authorized_keys"""
        success, output = self._run_ssh(
            agent, "cat ~/.ssh/authorized_keys 2>/dev/null || echo 'not-found'", timeout=5
        )
        if not success:
            return {"agent": agent, "has_key": "unknown", "error": output}

        # Check for typical SSH key pattern
        has_key = "ssh-rsa" in output or "ssh-ed25519" in output
        return {"agent": agent, "has_key": has_key}

    def full_check(self) -> dict:
        """Run full diagnostics on all agents"""
        results = {}
        for agent in AGENTS.keys():
            conn = self.check_connectivity(agent)
            auth = self.check_ssh_auth(agent) if conn["reachable"] else {"agent": agent, "auth": "skipped", "error": "Host unreachable"}
            keys = self.check_authorized_keys(agent) if conn["reachable"] else {"agent": agent, "has_key": "skipped"}

            results[agent] = {
                "connectivity": conn,
                "auth": auth,
                "keys": keys,
            }

            # Update state
            self.state["checks"][agent] = results[agent]
            self.state["last_check"] = datetime.utcnow().isoformat()

        self._save_state()
        return results

    def generate_checklist(self) -> str:
        """Generate actionable checklist for resolving issues"""
        lines = ["# Squad SSH Remediation Checklist\n"]
        lines.append(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n")

        for agent in AGENTS.keys():
            check = self.state.get("checks", {}).get(agent, {})
            conn = check.get("connectivity", {})
            auth = check.get("auth", {})
            keys = check.get("keys", {})

            lines.append(f"\n## {agent.capitalize()} ({AGENTS[agent]['host']}:{AGENTS[agent]['port']})\n")

            if not conn.get("reachable"):
                lines.append(f"⚠️  **BLOCKER**: Host unreachable - requires physical access\n")
                lines.append("   - [ ] Verify Forge machine is powered on\n")
                lines.append("   - [ ] Check network connectivity at Forge location\n")
                lines.append("   - [ ] Verify Tailscale daemon is running\n")
                continue

            if auth.get("auth") != "ok":
                lines.append("❌ **SSH Authentication Failed**\n")
                lines.append("   - [ ] Confirm public key was deployed to agent\n")
                lines.append("   - [ ] Check `~/.ssh/authorized_keys` on agent contains your public key\n")
                lines.append("   - [ ] Verify SSH key permissions: `chmod 600 ~/.ssh/id_rsa*`\n")
                lines.append("   - [ ] Try manual SSH: `ssh -v ubuntu@{host}`\n")
            elif not keys.get("has_key"):
                lines.append("⚠️  **Key not in authorized_keys**\n")
                lines.append("   - [ ] Append public key to `~/.ssh/authorized_keys`\n")
                lines.append("   - [ ] Run: `ssh-copy-id -i ~/.ssh/id_rsa.pub ubuntu@{host}`\n")
            else:
                lines.append("✅ **SSH Working**\n")
                lines.append("   - [x] Connectivity verified\n")
                lines.append("   - [x] Authentication working\n")
                lines.append("   - [x] Public key deployed\n")

        return "\n".join(lines)

    def save_checklist(self):
        """Save checklist to output file"""
        checklist = self.generate_checklist()
        today = datetime.utcnow().strftime("%Y-%m-%d")
        output_file = OUTPUT_DIR / f"ssh-remediation-{today}.md"
        with open(output_file, "w") as f:
            f.write(checklist)
        print(f"✅ Checklist saved to {output_file}")

    def print_status(self):
        """Print current status summary"""
        print("\n🔧 Squad SSH Remediation Status\n")
        print(f"Last check: {self.state.get('last_check', 'Never')}\n")

        for agent in AGENTS.keys():
            check = self.state.get("checks", {}).get(agent, {})
            conn = check.get("connectivity", {})
            auth = check.get("auth", {})

            status = "✅ OK" if conn.get("reachable") and auth.get("auth") == "ok" else "⚠️  ISSUE"
            print(f"{agent:8} {status} - {conn.get('host', 'N/A')}:{conn.get('port', 'N/A')}")
            if not conn.get("reachable"):
                print(f"         └─ Host unreachable")
            elif auth.get("auth") != "ok":
                print(f"         └─ SSH auth failed: {auth.get('error', 'Unknown')}")

    def export_json(self, output_file: Optional[str] = None):
        """Export state as JSON for automation"""
        if not output_file:
            today = datetime.utcnow().strftime("%Y-%m-%d")
            output_file = OUTPUT_DIR / f"ssh-remediation-{today}.json"

        with open(output_file, "w") as f:
            json.dump(self.state, f, indent=2, default=str)
        print(f"✅ State exported to {output_file}")


def main():
    remediation = SSHRemediation()

    if len(sys.argv) < 2:
        print("Usage: squad-ssh-remediation <command>")
        print("Commands:")
        print("  check      - Run full diagnostics on all agents")
        print("  status     - Print current status summary")
        print("  checklist  - Generate remediation checklist")
        print("  export     - Export state as JSON")
        print("  dashboard  - Output JSON for squad-dashboard integration")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "check":
        remediation.full_check()
        remediation.print_status()
        remediation.save_checklist()

    elif command == "status":
        remediation.print_status()

    elif command == "checklist":
        remediation.save_checklist()
        print("\n--- Checklist Preview ---")
        print(remediation.generate_checklist())

    elif command == "export":
        remediation.export_json()

    elif command == "dashboard":
        # Output JSON for squad-dashboard integration
        status = remediation.dashboard_status()
        print(json.dumps(status, indent=2))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()