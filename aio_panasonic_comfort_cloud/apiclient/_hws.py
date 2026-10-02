import logging
from typing import TYPE_CHECKING

from .. import constants
from ..hwsdevice import HwsDevice
from ..panasonicdevice import PanasonicDeviceInfo

if TYPE_CHECKING:
    from ._protocol import ApiClientCore
else:
    ApiClientCore = object

_LOGGER = logging.getLogger(__name__)

class HwsMixin(ApiClientCore):
    """Status/control for standalone Heat Pump Hot Water Tank (HWS) devices."""

    async def _async_get_hws_status(self, device_info: PanasonicDeviceInfo):
        if (device_info.status_data_mode == constants.StatusDataMode.LIVE
            or (device_info.id in self._cache_devices and self._cache_devices[device_info.id] <= 0)):
            try:
                json_response = await self.execute_get(self._get_hws_device_status_url(device_info.guid), "get_hws_status", 200)
                device_info.status_data_mode = constants.StatusDataMode.LIVE
                return json_response
            except Exception as e:  # noqa: BLE001
                _LOGGER.warning(f"Failed to get live status for device {device_info.guid} switching to cached data.{e}")
                device_info.status_data_mode = constants.StatusDataMode.CACHED
                self._cache_devices[device_info.id] = 10
        json_response = await self.execute_get(self._get_hws_device_status_url(device_info.guid), "get_status", 200)
        self._cache_devices[device_info.id] -= 1
        return json_response

    async def get_hws_device(self, device_info: PanasonicDeviceInfo) -> HwsDevice:
        json_response = await self._async_get_hws_status(device_info)
        return HwsDevice(device_info, json_response)

    async def try_update_hws_device(self, device: HwsDevice) -> bool:
        json_response = await self._async_get_hws_status(device.info)
        return device.load(json_response)

    async def _async_set_hws(self, device_info: PanasonicDeviceInfo, body: dict):
        """Send a partial update to an HWS device.

        HWS devices report their state as a ``parameters`` object under
        ``/device/group`` with the same shape as an air conditioner's
        (``hpuOperationStatus``/``operationMode``/``boostMode``/``tankTemperature``
        instead of AC fields like ``operate``/``operationMode``), so this
        goes through the same ``/deviceStatus/control`` endpoint as
        :meth:`AirConditionerMixin.set_device_raw` rather than the
        ``/device/a2wInfoUpdate`` endpoint previously guessed from an app
        capture, which doesn't actually exist (confirmed 403 "Missing
        Authentication Token" — API Gateway's error for a route that isn't
        registered — against a live account).
        """
        payload = {"deviceGuid": device_info.guid, "parameters": body}
        await self.execute_post(self._get_hws_device_status_control_url(), payload, "set_hws_device", 200)

    async def set_hws_tank_temperature(self, device_info: PanasonicDeviceInfo, temperature: float):
        """ Set the target temperature of the hot water tank (unverified, see _async_set_hws) """
        await self._async_set_hws(device_info, {"tankTemperature": temperature})

    async def set_hws_boost_mode(self, device_info: PanasonicDeviceInfo, new_value: str | constants.AquareaOperationStatus):
        """ Turn boost mode on/off (unverified, see _async_set_hws) """
        if isinstance(new_value, str):
            new_value = constants.AquareaOperationStatus[new_value]
        await self._async_set_hws(device_info, {"boostMode": new_value.value})

    async def set_hws_operation_status(self, device_info: PanasonicDeviceInfo, new_value: str | constants.AquareaOperationStatus):
        """ Turn the heat pump unit on/off (unverified, see _async_set_hws) """
        if isinstance(new_value, str):
            new_value = constants.AquareaOperationStatus[new_value]
        await self._async_set_hws(device_info, {"hpuOperationStatus": new_value.value})

    async def set_hws_operation_mode(self, device_info: PanasonicDeviceInfo, new_value: int):
        """ Set the raw operation mode value (unverified, see _async_set_hws; the
        meaning of each mode value hasn't been confirmed against a real device) """
        await self._async_set_hws(device_info, {"operationMode": new_value})
