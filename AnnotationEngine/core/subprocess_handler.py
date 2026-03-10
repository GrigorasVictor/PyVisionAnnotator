"""
core/subprocess_handler.py — Secure subprocess execution

Provides ``SubprocessHandler`` for launching external processes, and
``ManagedProcess`` — a killable wrapper around ``subprocess.Popen`` that
can be safely cancelled from another thread without crashing the app.
"""
import subprocess
import json
import os
import shutil
from typing import List, Optional, Dict, Any, Tuple

class ManagedProcess:
    """Wraps ``subprocess.Popen`` so it can be waited on **or** killed
    from another thread without crashing the application."""

    def __init__(self, proc: subprocess.Popen, timeout: int) -> None:
        self._proc = proc
        self._timeout = timeout
        self._killed = False

    def wait(self) -> Tuple[bool, Any, str]:
        """Block until the process exits (or timeout / kill).

        Returns ``(success, data, error_message)``.
        """
        try:
            stdout, stderr = self._proc.communicate(timeout=self._timeout)
        except subprocess.TimeoutExpired:
            self.kill()
            try:
                stdout, stderr = self._proc.communicate(timeout=5)
            except Exception:
                stdout, stderr = "", ""
            return False, None, f"Execution timed out after {self._timeout}s"

        stdout = str(stdout or "").strip()
        stderr = str(stderr or "").strip()

        if self._killed:
            return False, None, "Process was cancelled."

        if self._proc.returncode != 0:
            return (
                False,
                stdout,
                stderr or f"Exited with code {self._proc.returncode}",
            )

        data = SubprocessHandler.parse_json_output(stdout)
        return True, data, stderr

    def kill(self) -> None:
        """Terminate the child process immediately (safe from any thread)."""
        self._killed = True
        try:
            self._proc.kill()
        except OSError:
            pass

    @property
    def killed(self) -> bool:
        return self._killed

class SubprocessHandler:
    """
    Handles secure execution of external subprocesses.
    Prevents shell injection by strictly using argument lists.
    """

    @staticmethod
    def _build_command(
        executable: str,
        script: Optional[str] = None,
        args: Optional[List[str]] = None,
    ) -> Tuple[Optional[List[str]], str]:
        """Return ``(cmd_list, error)``.  *cmd_list* is None on failure."""
        if os.path.isabs(executable):
            if not os.path.exists(executable):
                return None, f"Executable path not found: {executable}"
            cmd_executable = executable
        else:
            cmd_executable = shutil.which(executable)
            if not cmd_executable:
                return None, f"Command not found in PATH: {executable}"

        command: List[str] = [cmd_executable]
        if script:
            if not os.path.exists(script):
                return None, f"Script file not found: {script}"
            command.append(script)
        if args:
            command.extend([str(a) for a in args])
        return command, ""

    @staticmethod
    def parse_json_output(stdout: str) -> Any:
        """Best-effort JSON extraction from stdout."""
        json_start = stdout.find("{")
        json_end = stdout.rfind("}")
        if json_start != -1 and json_end >= json_start:
            try:
                return json.loads(stdout[json_start : json_end + 1])
            except json.JSONDecodeError:
                pass
        try:
            return json.loads(stdout)
        except (json.JSONDecodeError, ValueError):
            pass
        return stdout

    @staticmethod
    def start_process(
        executable: str,
        script: Optional[str] = None,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        timeout: int = 60,
        env: Optional[Dict[str, str]] = None,
    ) -> Tuple[Optional[ManagedProcess], str]:
        """Launch a subprocess via Popen and return a killable ManagedProcess.

        Returns ``(ManagedProcess | None, error_string)``.
        """
        command, err = SubprocessHandler._build_command(executable, script, args)
        if command is None:
            return None, err

        process_env = os.environ.copy()
        if env:
            process_env.update(env)

        try:
            proc = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd,
                env=process_env,
                shell=False,
            )
        except Exception as e:
            return None, f"System error: {e}"

        return ManagedProcess(proc, timeout), ""

    @staticmethod
    def run_command(
        executable: str,
        script: Optional[str] = None,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        timeout: int = 60,
        env: Optional[Dict[str, str]] = None,
    ) -> Tuple[bool, Any, str]:
        """Blocking convenience wrapper: start_process + wait."""
        managed, err = SubprocessHandler.start_process(
            executable, script, args, cwd, timeout, env,
        )
        if managed is None:
            return False, None, err
        return managed.wait()
