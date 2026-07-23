"""Named GMLAN/KWP service-ID and subfunction constants.

The T8 stock and alternate-bootloader clients previously spelled these out
as raw byte literals (``b"\\xA5\\x01"``) at each call site. That's easy to
typo silently — a wrong nibble is still a valid-looking byte string — so
this module gives the well-known ones names. It documents wire bytes; it
does not send anything itself.
"""

from __future__ import annotations

# Service IDs (first byte of a request).
SID_DIAGNOSTIC_SESSION = 0x10
SID_RETURN_TO_NORMAL_MODE = 0x20
SID_SECURITY_ACCESS = 0x27
SID_DISABLE_NORMAL_COMMUNICATION = 0x28
SID_REQUEST_DOWNLOAD = 0x34
SID_TRANSFER_DATA = 0x36
SID_TESTER_PRESENT = 0x3E
SID_READ_DATA_BY_IDENTIFIER = 0x1A
SID_REPORT_PROGRAMMED_STATE = 0xA2
SID_PROGRAMMING_MODE = 0xA5

# Positive response SIDs (request SID + 0x40, except where GMLAN uses its
# own fixed response byte instead of the +0x40 convention).
POSITIVE_DIAGNOSTIC_SESSION = 0x50
POSITIVE_RETURN_TO_NORMAL_MODE = 0x60
POSITIVE_SECURITY_ACCESS = 0x67
POSITIVE_DISABLE_NORMAL_COMMUNICATION = 0x68
POSITIVE_REQUEST_DOWNLOAD = 0x74
POSITIVE_TRANSFER_DATA = 0x76
POSITIVE_TESTER_PRESENT = 0x7E
POSITIVE_READ_DATA_BY_IDENTIFIER = 0x5A
POSITIVE_REPORT_PROGRAMMED_STATE = 0xE2
POSITIVE_PROGRAMMING_MODE = 0xE5

# DiagnosticSession / ProgrammingMode subfunctions used by the Trionic 8 flow.
SUBFUNCTION_PROGRAMMING_SESSION = 0x02
SUBFUNCTION_PROGRAMMING_MODE_REQUEST = 0x01
SUBFUNCTION_PROGRAMMING_MODE_ENABLE = 0x03

# Negative response marker (0x7F, echoed SID, NRC).
NEGATIVE_RESPONSE_SID = 0x7F
NRC_PENDING = 0x78
