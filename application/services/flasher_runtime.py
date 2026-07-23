"""UI-independent adapter and ECU lifecycle service."""

from adapters.base_adapter import BaseAdapter
from application.ports.adapter_factory import AdapterFactory
from ecus.base_ecu import BaseECU


class FlasherRuntime:
    """Owns mutable runtime selections without Qt or concrete hardware imports."""

    def __init__(self, adapter_factory: AdapterFactory, initial_ecu: BaseECU):
        self._factory = adapter_factory
        self.adapter_key = "mock"
        self.adapter = self._factory.create(self.adapter_key)
        self.ecu = initial_ecu
        self._configure_adapter()

    @property
    def is_connected(self) -> bool:
        return self.adapter.is_connected()

    def replace_adapter(self, adapter_key: str, dll_path: str = "", port: str = "", interface: str = "") -> None:
        replacement = self._factory.create(adapter_key, dll_path=dll_path, port=port, interface=interface)
        if self.adapter.is_connected():
            self.adapter.disconnect()
        self.adapter = replacement
        self.adapter_key = adapter_key.casefold().strip()
        self._configure_adapter()

    def connect(self, baudrate: int = 500000) -> bool:
        return self.adapter.is_connected() or self.adapter.connect(baudrate=baudrate)

    def disconnect(self) -> None:
        self.adapter.disconnect()

    def select_ecu(self, ecu: BaseECU) -> None:
        self.ecu = ecu
        self._configure_adapter()

    def _configure_adapter(self) -> None:
        self.adapter.configure_for_ecu(
            self.ecu.CAN_ID_TX,
            self.ecu.CAN_ID_RX,
            self.ecu.TOTAL_FLASH_SIZE,
        )
