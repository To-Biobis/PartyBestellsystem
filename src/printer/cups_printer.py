"""CUPS-based printer backend for network printing.

Sends print jobs to a CUPS server via the ``lp`` command.
The device class implements the same ``text()``/``cut()`` interface
that the existing PrintQueueManager expects, so no changes to the
queue layer are required.
"""

import logging
import os
import subprocess
import tempfile
from threading import Lock

logger = logging.getLogger(__name__)


class CupsPrinterDevice:
    """A virtual printer device that buffers text and flushes it via CUPS.

    The interface mirrors the subset of python-escpos that the
    :class:`PrintQueueManager` uses (``text()`` and ``cut()``), so the
    existing queue machinery works without modification.
    """

    def __init__(self, server: str, port: int = 631, printer_name: str = ""):
        self._server = server
        self._port = port
        self._printer_name = printer_name
        self._buffer: list[str] = []

    # ------------------------------------------------------------------
    # escpos-compatible interface
    # ------------------------------------------------------------------

    def text(self, content: str) -> None:
        """Append *content* to the internal print buffer."""
        self._buffer.append(content)

    def cut(self) -> None:
        """Flush the buffer and send the job to the CUPS server."""
        content = "".join(self._buffer)
        self._buffer = []
        self._send_to_cups(content)

    def close(self) -> None:
        """No-op – kept for interface compatibility."""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _send_to_cups(self, content: str) -> bool:
        """Write *content* to a temporary file and submit it with ``lp``."""
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".txt",
                delete=False,
                encoding="utf-8",
            ) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            cmd = ["lp", "-h", f"{self._server}:{self._port}"]
            if self._printer_name:
                cmd.extend(["-d", self._printer_name])
            cmd.append(tmp_path)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                logger.info(
                    "Druckauftrag an CUPS-Server %s gesendet", self._server
                )
                return True

            logger.error(
                "CUPS-Druck fehlgeschlagen (rc=%d): %s",
                result.returncode,
                result.stderr.strip(),
            )
            return False

        except FileNotFoundError:
            logger.error(
                "Befehl 'lp' nicht gefunden – ist CUPS installiert?"
            )
            return False
        except subprocess.TimeoutExpired:
            logger.error("Timeout beim Senden an CUPS-Server %s", self._server)
            return False
        except Exception as exc:
            logger.error("Fehler beim CUPS-Druck: %s", exc)
            return False
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass


class CupsPrinterManager:
    """Drop-in replacement for :class:`PrinterManager` that uses CUPS.

    The :class:`PrintQueueManager` calls ``get_printer()`` and
    ``test_connection()`` on the manager.  This class satisfies that
    contract without touching the USB stack.
    """

    _lock = Lock()

    def __init__(
        self,
        server: str = "192.168.178.182",
        port: int = 631,
        printer_name: str = "",
    ):
        self._server = server
        self._port = port
        self._printer_name = printer_name

    # ------------------------------------------------------------------
    # PrinterManager-compatible interface
    # ------------------------------------------------------------------

    def get_printer(self) -> CupsPrinterDevice:
        """Return a fresh :class:`CupsPrinterDevice` for each job."""
        return CupsPrinterDevice(self._server, self._port, self._printer_name)

    def test_connection(self) -> bool:
        """Return *True* when the CUPS server is reachable."""
        try:
            cmd = ["lpstat", "-h", f"{self._server}:{self._port}", "-a"]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10
            )
            reachable = result.returncode == 0
            if reachable:
                logger.info(
                    "CUPS-Server %s:%d erreichbar", self._server, self._port
                )
            else:
                logger.warning(
                    "CUPS-Server %s:%d nicht erreichbar (rc=%d): %s",
                    self._server,
                    self._port,
                    result.returncode,
                    result.stderr.strip(),
                )
            return reachable
        except FileNotFoundError:
            logger.warning(
                "Befehl 'lpstat' nicht gefunden – CUPS-Verbindungstest übersprungen"
            )
            # Treat as available so the app can still start when lpstat is missing
            return True
        except subprocess.TimeoutExpired:
            logger.warning(
                "Timeout beim Testen der CUPS-Verbindung zu %s", self._server
            )
            return False
        except Exception as exc:
            logger.warning("CUPS-Verbindungstest fehlgeschlagen: %s", exc)
            return False

    def release_printer(self) -> None:
        """No-op – kept for interface compatibility."""
