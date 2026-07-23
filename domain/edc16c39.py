"""EDC16C39 profile and programming plan.

Ranges are half-open in Python.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple


@dataclass(frozen=True)
class Edc16Area:
    index: int
    name: str
    start: int
    end: int

    @property
    def size(self) -> int:
        return self.end - self.start


PA_ERASE = Edc16Area(4, "protected-area erase", 0x010000, 0x030000)
PA_DESTINATION = Edc16Area(4, "protected area", 0x010000, 0x02FF00)
CODE_ERASE = Edc16Area(3, "code erase", 0x030000, 0x150000)
CODE_DESTINATION = Edc16Area(3, "code", 0x030000, 0x150000)
DATA_VARIANT_ERASE = Edc16Area(2, "data and variant erase", 0x150000, 0x200000)
VARIANT_DESTINATION = Edc16Area(6, "variant data", 0x150000, 0x1C0000)
DATA_DESTINATION = Edc16Area(2, "calibration data", 0x1C0000, 0x1FE000)


class Edc16PhaseKind(str, Enum):
    CONNECT = "connect"
    SECURITY = "security"
    START_PROGRAMMING_SESSION = "start-programming-session"
    ERASE = "erase"
    PROGRAM = "program"
    VERIFY = "verify"
    RESET = "reset"
    WAIT_RECONNECT = "wait-reconnect"


@dataclass(frozen=True)
class Edc16ProgrammingPhase:
    kind: Edc16PhaseKind
    area: Edc16Area | None = None


EDC16C39_FULL_PROGRAMMING_PLAN: Tuple[Edc16ProgrammingPhase, ...] = (
    Edc16ProgrammingPhase(Edc16PhaseKind.CONNECT),
    Edc16ProgrammingPhase(Edc16PhaseKind.SECURITY),
    Edc16ProgrammingPhase(Edc16PhaseKind.START_PROGRAMMING_SESSION),
    Edc16ProgrammingPhase(Edc16PhaseKind.ERASE, PA_ERASE),
    Edc16ProgrammingPhase(Edc16PhaseKind.PROGRAM, PA_DESTINATION),
    Edc16ProgrammingPhase(Edc16PhaseKind.VERIFY, PA_DESTINATION),
    Edc16ProgrammingPhase(Edc16PhaseKind.RESET),
    Edc16ProgrammingPhase(Edc16PhaseKind.WAIT_RECONNECT),
    Edc16ProgrammingPhase(Edc16PhaseKind.SECURITY),
    Edc16ProgrammingPhase(Edc16PhaseKind.START_PROGRAMMING_SESSION),
    Edc16ProgrammingPhase(Edc16PhaseKind.ERASE, CODE_ERASE),
    Edc16ProgrammingPhase(Edc16PhaseKind.ERASE, DATA_VARIANT_ERASE),
    Edc16ProgrammingPhase(Edc16PhaseKind.PROGRAM, CODE_DESTINATION),
    Edc16ProgrammingPhase(Edc16PhaseKind.VERIFY, CODE_DESTINATION),
    Edc16ProgrammingPhase(Edc16PhaseKind.PROGRAM, DATA_DESTINATION),
    Edc16ProgrammingPhase(Edc16PhaseKind.VERIFY, DATA_DESTINATION),
    Edc16ProgrammingPhase(Edc16PhaseKind.PROGRAM, VARIANT_DESTINATION),
    Edc16ProgrammingPhase(Edc16PhaseKind.VERIFY, VARIANT_DESTINATION),
    Edc16ProgrammingPhase(Edc16PhaseKind.RESET),
)

