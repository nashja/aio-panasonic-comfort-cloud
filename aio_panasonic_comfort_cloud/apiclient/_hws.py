import logging
from typing import TYPE_CHECKING
from datetime import datetime
from ._timezone import get_current_time_zone

from .. import constants
from ..hwsdevice import HwsDevice
from ..panasonicdevice import PanasonicDeviceInfo
from ..models.hws import HwsConsumption, HwsCustomEncoder,HwsDailySettings
import json

if TYPE_CHECKING:
    from ._protocol import ApiClientCore
else:
    ApiClientCore = object

_LOGGER = logging.getLogger(__name__)


class HwsMixin(ApiClientCore):
    """Status/control for standalone Heat Pump Hot Water Tank (HWS) devices."""

    async def _async_get_hws_status(self, device_info: PanasonicDeviceInfo):
        if device_info.status_data_mode == constants.StatusDataMode.LIVE or (
            device_info.id in self._cache_devices
            and self._cache_devices[device_info.id] <= 0
        ):
            try:
                json_response = await self.execute_get(
                    self._get_hws_device_info_url(device_info.guid),
                    "get_hws_status",
                    200,
                )
                device_info.status_data_mode = constants.StatusDataMode.LIVE
                return json_response
            except Exception as e:  # noqa: BLE001
                _LOGGER.warning(
                    f"Failed to get live status for device {device_info.guid} switching to cached data.{e}"
                )
                device_info.status_data_mode = constants.StatusDataMode.CACHED
                self._cache_devices[device_info.id] = 10  # FIXME??
        json_response = await self.execute_get(
            self._get_hws_device_info_url(device_info.guid), "get_status", 200
        )
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

        HWS devices respond to a few commands sent with the 
        """
        payload = {"deviceGuid": device_info.guid, "parameters": body}
        await self.execute_post(
            self._get_hws_device_status_control_url(), payload, "set_hws_device", 200
        )

    async def set_hws_boost_mode(
        self,
        device_info: PanasonicDeviceInfo,
        new_value: str | constants.HwsBoostModeSettings,
    ):
        """Turn boost mode on/off This is now verified"""
        if isinstance(new_value, str):
            new_value = constants.HwsBoostModeSettings[new_value]
        await self._async_set_hws(device_info, {"boostMode": new_value.value})

    async def set_hws_operation_mode(
        self, device_info: PanasonicDeviceInfo, new_value: constants.HwsOperationModeSettings
    ):
        """Set the raw operation mode value (unverified, see _async_set_hws; the
        meaning of each mode value hasn't been confirmed against a real device)"""
        await self._async_set_hws(device_info, {"operationMode": new_value.value})

    async def set_hws_holiday_mode(
        self, device_info: PanasonicDeviceInfo
    ):
        """Turn on Holiday Mode Set the operation mode value (the
        meaning of each mode value has been confirmed against a real device)"""
        await self._async_set_hws(device_info, {"operationMode": constants.HwsOperationModeSettings.Holiday.value})

    async def set_hws_schedule_mode(
        self, device_info: PanasonicDeviceInfo
    ):
        """Turn on Schedule Mode - the default.  Set the operation mode value (the
        meaning of each mode value has been confirmed against a real device)"""
        await self._async_set_hws(device_info, {"operationMode": constants.HwsOperationModeSettings.Schedule.value})        

    async def async_get_hws_consumption(
        self, device_info: PanasonicDeviceInfo
    ) -> HwsConsumption | None:
        todays_item = await self._async_get_todays_hws_consumption(device_info)
        if todays_item is None:
            return None
        return todays_item

    async def async_try_update_hws_consumption(
        self, device_info: PanasonicDeviceInfo, energy: HwsConsumption
    ) -> bool | None:
        todays_item = await self._async_get_todays_hws_consumption(device_info)
        if not todays_item:
            return False
        else:
            return energy.copy(todays_item)

    async def async_set_hws_weekly_settings(
        self, device_info: PanasonicDeviceInfo, weekly_settings: list[HwsDailySettings]
    ):
        """Set the weekly settings for the HWS device."""
        # first encode the json into a string using a custom encoder to handle the HwsDailySettings objects
        # validted that this works.
        payload = json.dumps({
            "deviceGuid": device_info.guid, 
            "parameters": {"weeklySettingInfo": weekly_settings}
            },cls=HwsCustomEncoder)
        # then convert back into a json object to send to the API
        new_payload = json.loads(payload)

        await self.execute_post(
            self._get_hws_device_status_control_url(), new_payload, "set_hws_weekly_settings", 200
        )

    async def _async_get_todays_hws_consumption(
        self, device_info: PanasonicDeviceInfo
    ) -> HwsConsumption | None:
        device_guid = device_info.guid
        if not device_guid:
            return None
        today = datetime.now().strftime("%Y%m%d")

        payload = {
            "deviceGuid": device_guid,
            "dataMode": constants.HwdDataMode.Month.value,
            "date": today,
            "osTimezone": get_current_time_zone()
        }

        history = await self.execute_post(
            self._get_hws_device_history_url(), payload, "get_todays_hws_energy", 200
        )

        if history is None:
            return None
        if "historyDataList" not in history:
            return None
        history_items = history["historyDataList"]
        todays_item = None
        for item in history_items:
            if "dataTime" not in item:
                continue
            if item["dataTime"] != today:
                continue
            todays_item = HwsConsumption(item)
            break
        return todays_item
