"""
Domain Layer - Structured Exception Hierarchy.

All application exceptions descend from :class:`PythonFlasherError` so that
callers can catch the full family with a single ``except``.

::

    PythonFlasherError
    +-- ConfigurationError
    +-- AdapterError
    |   +-- AdapterNotFoundError
    |   +-- AdapterOpenError
    |   +-- AdapterDisconnectedError
    |   +-- AdapterTimeoutError
    +-- TransportError
    |   +-- IsoTpTimeoutError
    |   +-- IsoTpSequenceError
    |   +-- IsoTpFlowControlError
    +-- DiagnosticError
    |   +-- NegativeResponseError
    |   +-- SessionError
    |   +-- SecurityAccessError
    +-- FirmwareError
    |   +-- FirmwareFormatError
    |   +-- FirmwareCompatibilityError
    |   +-- ChecksumError
    +-- FlashError
    |   +-- EraseError
    |   +-- TransferError
    |   +-- VerificationError
    |   +-- RecoveryRequiredError
    +-- OperationCancelled
    +-- NotConnectedError
"""


class PythonFlasherError(Exception):
    """Root exception for all flasher domain errors."""


class ConfigurationError(PythonFlasherError):
    """Raised when application configuration is invalid or incomplete."""


class AdapterError(PythonFlasherError):
    """Base class for all hardware adapter errors."""

    def __init__(self, message: str, *, vendor_code=None, retry_safe: bool = False):
        self.vendor_code = vendor_code
        self.retry_safe = retry_safe
        super().__init__(message)


class AdapterNotFoundError(AdapterError):
    """The requested adapter hardware was not found on the system."""


class AdapterOpenError(AdapterError):
    """The adapter was found but could not be opened / initialised."""


class AdapterDisconnectedError(AdapterError):
    """The adapter disconnected during an active operation."""


class AdapterTimeoutError(AdapterError):
    """A read or write against the adapter timed out."""


class TransportError(PythonFlasherError):
    """Base class for transport-layer (ISO-TP) errors."""


class IsoTpTimeoutError(TransportError):
    """ISO-TP transfer did not complete within the configured timeout."""


class IsoTpSequenceError(TransportError):
    """An out-of-order or duplicate ISO-TP Consecutive Frame was received."""


class IsoTpFlowControlError(TransportError):
    """Flow Control negotiation failed (timeout or unexpected frame)."""


class DiagnosticError(PythonFlasherError):
    """Base class for diagnostic protocol (UDS/GMLAN/KWP) errors."""


class NegativeResponseError(DiagnosticError):
    """The ECU returned a negative response code."""

    def __init__(self, service_id: int, nrc: int, message: str = ""):
        self.service_id = service_id
        self.nrc = nrc
        self.retry_safe = nrc in (0x21, 0x78)
        self.recovery_advice = _NRC_RECOVERY_ADVICE.get(
            nrc, "Do not retry automatically; preserve the diagnostic state."
        )
        super().__init__(message or f"Negative response: SID=0x{service_id:02X} NRC=0x{nrc:02X}")


class SessionError(DiagnosticError):
    """Session transition failed or the ECU is in an unexpected session."""


class SecurityAccessError(DiagnosticError):
    """SecurityAccess seed-key exchange failed."""

    def __init__(self, message: str, *, level: int = 0, nrc=None, retry_after=None):
        self.level = level
        self.nrc = nrc
        self.retry_after = retry_after
        super().__init__(message)


class FirmwareError(PythonFlasherError):
    """Base class for firmware / calibration file errors."""


class FirmwareFormatError(FirmwareError):
    """The firmware file is malformed, truncated, or unparseable."""


class FirmwareCompatibilityError(FirmwareError):
    """The firmware file is not compatible with the connected ECU."""


class ProgrammingPreflightError(FirmwareCompatibilityError):
    """One or more mandatory programming safety checks failed."""

    def __init__(self, message: str, checks=()):
        self.checks = tuple(checks)
        super().__init__(message)


class ChecksumError(FirmwareError):
    """A checksum or hash validation failed."""


class FlashError(PythonFlasherError):
    """Base class for flash operation errors."""


class EraseError(FlashError):
    """Flash erase failed."""


class TransferError(FlashError):
    """TransferData block write failed."""


class VerificationError(FlashError):
    """Post-flash verification (ECU routine or readback) failed."""


class RecoveryRequiredError(FlashError):
    """The ECU is in a state that requires recovery before further use."""

    def __init__(self, message: str = "ECU requires recovery.", last_known_state: str = ""):
        self.last_known_state = last_known_state
        super().__init__(message)


class OperationCancelled(PythonFlasherError):
    """A long-running operation was cancelled by the user or system."""


class NotConnectedError(PythonFlasherError):
    """An operation was attempted before ``connect()`` was called."""


_NRC_RECOVERY_ADVICE = {
    0x21: "Retry only if the service policy permits a bounded busy retry.",
    0x22: "Restore ECU preconditions before retrying.",
    0x24: "Restart the documented diagnostic sequence from a safe state.",
    0x31: "Verify ECU identity, address, length, and active session.",
    0x33: "Do not repeat security attempts without checking lockout state.",
    0x35: "Invalid key: stop attempts to avoid an ECU lockout.",
    0x36: "Attempt limit exceeded: preserve power and observe the documented lockout period.",
    0x37: "Required delay not expired: observe the ECU-family delay before another attempt.",
    0x72: "General programming failure: treat the ECU as recovery-required.",
    0x73: "Wrong block counter: do not erase or restart automatically.",
    0x78: "Continue waiting within the existing absolute P2* deadline only.",
}
