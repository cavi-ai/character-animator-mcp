"""Native bridge request identity serialization tests."""

import hashlib
import json
import os
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from cavi_mcp_core import journal

from cavi_character_animator_mcp.bridge import CharacterUnknown, NativeBridge


def _alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


class _InputCapture:
    def __init__(self):
        self.data = bytearray()

    def write(self, value):
        self.data.extend(value)

    def close(self):
        pass


class _CompletedProcess:
    def __init__(self, stdout, operation):
        self.stdin = _InputCapture()
        self.returncode = 0
        self.stdout = stdout
        self.operation = operation

    def poll(self):
        return self.returncode


class CharacterBridgeRequestTests(unittest.TestCase):
    def test_focus_request_carries_identity_needed_for_scoped_native_activation(self):
        expected = {
            "pid": 14318,
            "launch_time": 1793813160.279797,
            "fingerprint": "native-state-fingerprint",
            "bundle_id": "com.adobe.Character-Animator.application",
            "application": "/Applications/Adobe Character Animator 2026/Adobe Character Animator 2026.app",
            "project_roots": ["/workspace/owned-project"],
            "windows": [{"title": "transient and intentionally omitted"}],
        }
        with tempfile.TemporaryDirectory() as directory:
            helper = Path(directory) / "native-helper"
            helper.write_bytes(b"fixture helper")
            process_holder = []

            def popen(_args, *, stdout, **_kwargs):
                process = _CompletedProcess(stdout, "focus")
                process_holder.append(process)
                stdout.write(json.dumps({"version": 1, "operation": "focus", "ok": True,
                                         "state": {}, "result": {}}).encode())
                stdout.flush()
                return process

            with (patch("cavi_character_animator_mcp.bridge.application",
                        return_value=(Path(expected["application"]), {})),
                  patch.object(NativeBridge, "executable", return_value=helper),
                  patch("cavi_character_animator_mcp.bridge.subprocess.Popen", side_effect=popen)):
                NativeBridge(directory).call(
                    "focus", {"kind": "import", "project_root": expected["project_roots"][0]},
                    expected=expected)

        request = json.loads(process_holder[0].stdin.data)
        self.assertEqual(request["expected"], {key: expected[key] for key in (
            "pid", "launch_time", "fingerprint", "bundle_id", "application", "project_roots")})

    def test_continue_chooser_request_carries_identity_for_atomic_activation(self):
        expected = {
            "pid": 58131,
            "launch_time": 1793825743.48212,
            "fingerprint": "background-chooser-fingerprint",
            "bundle_id": "com.adobe.Character-Animator.application",
            "application": "/Applications/Adobe Character Animator 2026/Adobe Character Animator 2026.app",
            "project_roots": ["/workspace/owned-project"],
        }
        with tempfile.TemporaryDirectory() as directory:
            helper = Path(directory) / "native-helper"
            helper.write_bytes(b"fixture helper")
            process_holder = []

            def popen(_args, *, stdout, **_kwargs):
                process = _CompletedProcess(stdout, "continue_chooser")
                process_holder.append(process)
                stdout.write(json.dumps({"version": 1, "operation": "continue_chooser", "ok": True,
                                         "state": {}, "result": {}}).encode())
                stdout.flush()
                return process

            with (patch("cavi_character_animator_mcp.bridge.application",
                        return_value=(Path(expected["application"]), {})),
                  patch.object(NativeBridge, "executable", return_value=helper),
                  patch("cavi_character_animator_mcp.bridge.subprocess.Popen", side_effect=popen)):
                NativeBridge(directory).call(
                    "continue_chooser", {"kind": "import", "operation_id": "a" * 32},
                    expected=expected)

        request = json.loads(process_holder[0].stdin.data)
        self.assertEqual(request["expected"], {key: expected[key] for key in (
            "pid", "launch_time", "fingerprint", "bundle_id", "application", "project_roots")})

    def test_continue_chooser_preserves_structured_submission_context(self):
        response = {"version": 1, "operation": "continue_chooser", "ok": False,
                    "error": {"code": "OUTCOME_UNKNOWN", "outcome": "unknown",
                              "phase": "go_to_sheet_readiness", "submission_may_have_started": False,
                              "targeted_confirmation_may_have_started": True,
                              "targeted_navigation_may_have_started": False,
                              "continuation_diagnostics": {"stage": "go_to_sheet", "last_ready": True,
                                                           "fingerprint_stable": False, "observations": 5},
                              "message": "observed chooser did not settle"}}
        with tempfile.TemporaryDirectory() as directory:
            helper = Path(directory) / "native-helper"
            helper.write_bytes(b"fixture helper")
            process_holder = []

            def popen(_args, *, stdout, **_kwargs):
                process = _CompletedProcess(stdout, "continue_chooser")
                process_holder.append(process)
                stdout.write(json.dumps(response).encode())
                stdout.flush()
                return process

            with (patch("cavi_character_animator_mcp.bridge.application",
                        return_value=(Path("/Applications/Adobe Character Animator 2026.app"), {})),
                  patch.object(NativeBridge, "executable", return_value=helper),
                  patch("cavi_character_animator_mcp.bridge.subprocess.Popen", side_effect=popen),
                  self.assertRaises(CharacterUnknown) as raised):
                NativeBridge(directory).call("continue_chooser", {"kind": "import"})
            context = raised.exception.native_context
            self.assertEqual(context["phase"], "go_to_sheet_readiness")
            self.assertIs(context["submission_may_have_started"], False)
            self.assertIs(context["targeted_confirmation_may_have_started"], True)
            self.assertIs(context["targeted_navigation_may_have_started"], False)
            self.assertEqual(context["continuation_diagnostics"], {
                "stage": "go_to_sheet", "last_ready": True,
                "fingerprint_stable": False, "observations": 5,
            })
            self.assertEqual(len(context["attempt_id"]), 32)
            self.assertEqual(Path(context["progress_path"]).stat().st_mode & 0o777, 0o600)

    @unittest.skipUnless(os.name == "posix", "needs a shell helper and process groups")
    def test_interrupted_attempt_retains_phase_trace_and_stops_what_the_helper_started(self):
        trace = '{"event":"observe_tree_progress","nodes":64}\n'
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "runtime"
            runtime.mkdir()
            child = Path(directory) / "child.pid"
            helper = Path(directory) / "native-helper"
            helper.write_text(f"#!/bin/sh\nprintf '%s\\n' '{trace.strip()}' >&2\n"
                              f"sleep 60 &\necho $! > '{child}'\nwait\n")
            helper.chmod(0o755)

            with (patch("cavi_character_animator_mcp.bridge.application",
                        return_value=(Path("/Applications/Adobe Character Animator 2026.app"), {})),
                  patch.object(NativeBridge, "executable", return_value=helper),
                  self.assertRaises(CharacterUnknown) as raised):
                NativeBridge(runtime, timeout=3).call(
                    "continue_chooser", {"operation_id": "a" * 32, "kind": "import"})
            context = raised.exception.native_context
            self.assertTrue(Path(context["progress_path"]).is_file())
            started = int(child.read_text())
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and _alive(started):
                time.sleep(.05)
            self.assertFalse(_alive(started))

        self.assertEqual(context["phase"], "transport_interrupted")
        self.assertIsNone(context["submission_may_have_started"])
        self.assertEqual(context["progress"], [trace.strip()])

    @unittest.skipUnless(os.name == "posix", "owned execution uses private Unix sockets")
    def test_helper_launch_registers_with_the_configured_process_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            owner = _Owner(root)
            self.addCleanup(owner.close)
            helper = root / "native-helper"
            helper.write_text("#!/bin/sh\ncat >/dev/null\nprintf '%s' "
                              "'{\"version\":1,\"operation\":\"status\",\"ok\":true,\"state\":{},\"result\":{}}'\n")
            helper.chmod(0o755)

            with (patch.dict(os.environ, {"CAVI_MCP_PROCESS_OWNER": str(owner.config)}),
                  patch("cavi_character_animator_mcp.bridge.application",
                        return_value=(Path("/Applications/Adobe Character Animator 2026.app"), {})),
                  patch.object(NativeBridge, "executable", return_value=helper)):
                result = NativeBridge(root / "runtime").call("status")

        self.assertTrue(result["ok"])
        self.assertIsNotNone(owner.request, "the helper launched without registering with its owner")
        self.assertEqual(owner.request["command"], [str(helper)])


class _Owner:
    """A private one-launch process owner speaking the cavi_mcp_core.owned_exec protocol."""

    def __init__(self, root):
        self.records = root / "records"
        self.records.mkdir(mode=0o700)
        self.endpoint = root / "owner.sock"
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.bind(str(self.endpoint))
        self.endpoint.chmod(0o600)
        self.socket.listen(1)
        self.socket.settimeout(0.1)
        self.config = root / "owner.json"
        journal.write_json(self.config, {"version": 1, "attempt": "unit-attempt",
                                         "socket": str(self.endpoint), "records": str(self.records),
                                         "token": "test-capability"})
        self.request = None
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.serve)
        self.thread.start()

    def serve(self):
        while not self.stop.is_set():
            try:
                connection, _ = self.socket.accept()
                break
            except TimeoutError:
                continue
        else:
            return
        with connection, connection.makefile("rb") as stream:
            frame = json.loads(stream.readline(65537))
            if frame["token"] != "test-capability":
                return
            self.request = frame["request"]
            record = self.records / "registered.json"
            journal.write_json(record, {"request": self.request, "birth_identity": "recorded-birth"})
            connection.sendall(_encoded({
                "launch_permitted": True,
                "request_sha256": hashlib.sha256(_encoded(self.request)).hexdigest(),
                "record": "registered.json",
                "record_sha256": hashlib.sha256(record.read_bytes()).hexdigest(),
            }))

    def close(self):
        self.stop.set()
        self.socket.close()
        self.thread.join(timeout=6)


def _encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


if __name__ == "__main__":
    unittest.main()
