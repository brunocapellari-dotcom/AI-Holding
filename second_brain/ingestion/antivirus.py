from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class ClamAVCommandScanner:
    """ClamAV adapter using a fixed executable path and stdin.

    Return code 0 is clean, 1 is infected, and any other result is an operational
    error. No shell, filename interpolation, or temporary executable file is used.
    """

    binary: str = "clamscan"
    timeout_seconds: float = 30.0

    def scan(self, content: bytes, *, filename: str | None = None) -> bool:
        del filename
        resolved = shutil.which(self.binary)
        if resolved is None:
            raise RuntimeError(f"ClamAV binary is not available: {self.binary}")
        try:
            completed = subprocess.run(  # nosec B603 - fixed resolved executable; shell is never used.
                [resolved, "--no-summary", "-"],
                input=content,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout_seconds,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("ClamAV scan timed out") from exc
        if completed.returncode == 0:
            return True
        if completed.returncode == 1:
            return False
        stderr = completed.stderr.decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"ClamAV scan failed operationally: {stderr}")
