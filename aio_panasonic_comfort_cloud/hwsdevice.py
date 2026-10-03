from datetime import datetime, timezone

from .panasonicdevice import PanasonicDeviceInfo
from .models.hws import HwsDeviceParameters, HwsParameters
from .exceptions import DeviceIsNotReadyError


class HwsDevice:
    """A standalone Heat Pump Hot Water tank device (deviceType "11", e.g.
    HE-UM40CR).

    Mirrors :class:`AquareaDevice`/:class:`PanasonicDevice`, but is built
    directly from the ``parameters`` object of a ``/device/group`` entry —
    see :class:`~.models.hws.HwsDeviceParameters` for why this device class
    has no separate per-device status endpoint to call.
    """

    def __init__(self, info: PanasonicDeviceInfo, json=None) -> None:
        self._info = info
        self._deviceParameters: HwsDeviceParameters | None = None
        self._parameters: HwsParameters | None = None
        self._last_update = datetime.now(timezone.utc)
        self._load_device_parameters(json)
        self._load_parameters(json)

    @property
    def id(self) -> str:
        return self.info.id if self.info.id is not None else "-"

    @property
    def info(self) -> PanasonicDeviceInfo:
        return self._info

    @property
    def deviceParameters(self) -> HwsDeviceParameters:
        if self._deviceParameters is None:
            raise DeviceIsNotReadyError
        return self._deviceParameters

    @property
    def parameters(self) -> HwsParameters:
        if self._parameters is None:
            raise DeviceIsNotReadyError
        return self._parameters

    @property
    def last_update(self) -> datetime:
        return self._last_update

    def _load_device_parameters(self, json) -> bool:
        """Load/refresh from a raw ``/device/group`` entry (the dict with
        ``deviceGuid``/``deviceType``/``parameters`` keys — i.e.
        ``PanasonicDeviceInfo.raw`` for this device)."""
        if not json:
            return False

        deviceParameters_json = json
        has_changed = False
        if not self._deviceParameters:
            self._deviceParameters = HwsDeviceParameters(deviceParameters_json)
            has_changed = True
        else:
            has_changed = (
                self._deviceParameters.load(deviceParameters_json) or has_changed
            )

        if has_changed:
            self._last_update = datetime.now(timezone.utc)
        return has_changed

    def _load_parameters(self, json):
        parameters_json = json.get("parameters")
        if not parameters_json:
            self._has_parameters = False
            return
        self._has_parameters = True
        if not self._parameters:
            self._parameters = HwsParameters(parameters_json)
        else:
            self._parameters.load(parameters_json)
        self._has_changed = True
        return

    def load(self, json) -> bool:
        if not json:
            return False
        self._has_changed = False
        self._load_device_parameters(json)
        self._load_parameters(json)
        return True
