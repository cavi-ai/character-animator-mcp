"""Production MCP tools with a synthetic native adapter; never opens Character Animator.

Only status and inspection native operations are supported. All other native
operations fail closed. File and session validation stay in the production host.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

from cavi_character_animator_mcp import bridge, server
from cavi_character_animator_mcp.animator import CharacterAnimator


class SimulatedCharacterBridge:
    def __init__(self, directory=None):
        pass

    def call(self, operation, parameters=None, expected=None, cancelled=None):
        if operation not in {"status", "inspect"}:
            raise bridge.CharacterRejected("Unsupported simulated native operation")
        return {"version": 1, "ok": True, "operation": operation,
                "state": {"bundle_id": bridge.BUNDLE_ID,
                          "pid": 125, "launch_time": 1.0, "project_roots": [],
                          "fingerprint": "simulated", "windows": [],
                          "accessibility_trusted": True}}


def main():
    with tempfile.TemporaryDirectory(prefix="character-animator-eval-simulated-") as directory:
        root = Path(directory)
        host = CharacterAnimator(root, root / "data", bridge=SimulatedCharacterBridge())
        with (patch.object(server, "client", return_value=host),
              patch.object(server, "NativeBridge", SimulatedCharacterBridge),
              patch.object(server, "data_dir", return_value=root / "data")):
            server.main()


if __name__ == "__main__":
    main()
