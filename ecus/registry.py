"""
ECU Registry & Dynamic Discovery Engine.

Auto-discovers ECU modules in the :mod:`ecus` package.  A module is registered
if it defines a class that inherits from :class:`BaseECU` and is not
abstract.  The registry key is the lowercase class name by default; ECU
classes can override this by setting a ``REGISTRY_KEY`` class attribute.
"""

import importlib
import inspect
import pkgutil
import threading
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Type
from domain.memory_map import AddressRange
from ecus.base_ecu import BaseECU
from logger import app_logger


@dataclass(frozen=True)
class DiscoveryFailure:
    module: str
    error_type: str
    message: str


@dataclass(frozen=True)
class DiscoveryReport:
    discovered_keys: Tuple[str, ...]
    failures: Tuple[DiscoveryFailure, ...]


class EcuRegistry:
    """Registry for discovering, listing, and instantiating ECU modules."""

    _registry: Dict[str, Type[BaseECU]] = {}
    _discovered: bool = False
    _failures: List[DiscoveryFailure] = []
    _lock = threading.RLock()

    @classmethod
    def _discover(cls) -> None:
        """Import all submodules of :mod:`ecus` and register BaseECU subclasses."""
        with cls._lock:
            if cls._discovered:
                return

            import ecus as ecus_pkg
            modules = sorted(pkgutil.iter_modules(ecus_pkg.__path__, prefix="ecus."), key=lambda item: item.name)
            for mod_info in modules:
                cls._discover_module(mod_info.name)
            cls._discovered = True

    @classmethod
    def _discover_module(cls, mod_name: str) -> None:
        if mod_name.startswith("ecus.base") or mod_name.startswith("ecus.registry"):
            return
        try:
            mod = importlib.import_module(mod_name)
        except Exception as exc:
            failure = DiscoveryFailure(mod_name, type(exc).__name__, str(exc))
            cls._failures.append(failure)
            app_logger.error("ECU discovery failed for %s: %s: %s", mod_name, failure.error_type, failure.message)
            return

        for _name, obj in inspect.getmembers(mod, inspect.isclass):
            if not issubclass(obj, BaseECU) or obj is BaseECU:
                continue
            if inspect.isabstract(obj):
                continue
            if not getattr(obj, "REGISTER_ECU", True):
                continue
            key = getattr(obj, "REGISTRY_KEY", obj.__name__.lower())
            if key in cls._registry and cls._registry[key] is not obj:
                raise ValueError(f"Duplicate ECU key: {key}")
            cls._validate_definition(key, obj)
            cls._registry[key] = obj
            app_logger.info(f"[EcuRegistry] Discovered ECU: {obj.NAME} (key: {key})")

    @classmethod
    def register(cls, key: str, ecu_cls: Type[BaseECU]) -> None:
        """Manually register a new ECU module class."""
        key = key.lower().strip()
        with cls._lock:
            if key in cls._registry:
                raise ValueError(f"Duplicate ECU key: {key}")
            cls._validate_definition(key, ecu_cls)
            cls._registry[key] = ecu_cls
        app_logger.info(f"[EcuRegistry] Registered ECU: {ecu_cls.NAME} (key: {key})")

    @classmethod
    def get_all(cls) -> Dict[str, Type[BaseECU]]:
        cls._discover()
        return dict(cls._registry)

    @classmethod
    def list_ecus(cls) -> List[Tuple[str, str]]:
        cls._discover()
        return [(k, cls._registry[k].NAME) for k in sorted(cls._registry)]

    @classmethod
    def get(cls, key: str) -> Optional[Type[BaseECU]]:
        cls._discover()
        return cls._registry.get(key.lower().strip())

    @classmethod
    def discovery_report(cls) -> DiscoveryReport:
        cls._discover()
        with cls._lock:
            return DiscoveryReport(tuple(sorted(cls._registry)), tuple(cls._failures))

    @classmethod
    def instantiate(cls, key: str) -> BaseECU:
        cls._discover()
        ecu_cls = cls.get(key)
        if not ecu_cls:
            available = ", ".join(cls._registry.keys())
            raise ValueError(f"Unknown ECU key '{key}'. Available: {available}")
        return ecu_cls()

    @staticmethod
    def _validate_definition(key: str, ecu_cls: Type[BaseECU]) -> None:
        ecu = ecu_cls()
        if not key or not ecu.NAME.strip():
            raise ValueError("ECU registry key and display name are required")
        metadata = ecu.protocol_metadata
        if metadata.request_can_id != ecu.CAN_ID_TX or metadata.response_can_id != ecu.CAN_ID_RX:
            raise ValueError(f"{key}: protocol metadata CAN IDs disagree with the ECU definition")
        flash_ranges = ecu.get_flash_addresses()
        if not flash_ranges or any(not isinstance(item, AddressRange) for item in flash_ranges):
            raise ValueError(f"{key}: flash addresses must use validated AddressRange values")
        for item in flash_ranges:
            if item.end_exclusive > ecu.TOTAL_FLASH_SIZE:
                raise ValueError(f"{key}: flash address range exceeds the device boundary")
        for name, (start, end, _filename) in ecu.get_flash_regions().items():
            if not (0 <= start < end <= ecu.TOTAL_FLASH_SIZE):
                raise ValueError(f"{key}: invalid read region {name}: 0x{start:X}-0x{end:X}")
        capabilities = ecu.CAPABILITIES
        if capabilities.supports_full_write or capabilities.supports_calibration_write:
            if not ecu.get_write_regions():
                raise ValueError(f"{key}: write capability declared without write regions")
            if not ecu.PROGRAMMING_STRATEGY or not ecu.CHECKSUM_STRATEGY:
                raise ValueError(f"{key}: write capability requires programming and checksum strategies")
            if not ecu.PHYSICAL_PROGRAMMING_IMPLEMENTED:
                raise ValueError(f"{key}: write capability declared without a physical programming implementation")
            if not ecu.RECOVERY_STRATEGY or not capabilities.supports_recovery:
                raise ValueError(f"{key}: write capability requires a released recovery strategy")
            if ecu_cls.is_identity_compatible is BaseECU.is_identity_compatible:
                raise ValueError(f"{key}: write capability requires a live identity compatibility policy")
            if not capabilities.evidence_reference:
                raise ValueError(f"{key}: write capability requires an evidence reference")
