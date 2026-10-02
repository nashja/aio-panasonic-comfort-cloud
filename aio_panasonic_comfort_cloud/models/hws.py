import logging

from .. import constants

_LOGGER = logging.getLogger(__name__)


def read_enum(json, key, type, default_value):
    if not json or key not in json or json[key] is None:
        return default_value
    try:
        return type(json[key])
    except Exception as ex:
        _LOGGER.warning("Error reading HWS property '%s' with value '%s'", key, json[key], exc_info=ex)
    return default_value


def read_value(json, key, default_value):
    if not json:
        return default_value
    value = json.get(key, default_value)
    return default_value if value is None else value


class HwsTemperatureSettingLimits:
    """Temperature set limits for the HWS tank"""

    def __init__(self, json=None) -> None:
        self._set1_end_temperature: int | None = None
        self._set2_start_temperature_min: int | None = None       
        self._set2_start_temperature_max: int | None = None 
        self._set2_end_temperature_min: int | None = None       
        self._set2_end_temperature_max: int | None = None                                    
        self.load(json)

    @property
    def has_changed(self):
        return self._has_changed

    @property
    def set1_end_temperature(self):
        return  self._set1_end_temperature

    @property
    def set2_start_temperature_min(self):
        return self._set2_start_temperature_min

    @property
    def set2_start_temperature_max(self):
        return self._set2_start_temperature_max

    @property
    def set2_end_temperature_min(self):
        return self._set2_end_temperature_min

    @property
    def set2_end_temperature_max(self):
        return self._set2_end_temperature_max    
    
    def load(self, json) -> bool:
        if not json:
            return False
        self._has_changed = False
        self._set1_end_temperature = read_value(json, 'set1EndTemperature', self._set1_end_temperature)
        self._set2_start_temperature_min = read_value(json, 'set2StartTemperatureMin', self._set2_start_temperature_min)
        self._set2_start_temperature_max = read_value(json, 'set2StartTemperatureMax', self._set2_start_temperature_max)
        self._set2_end_temperature_min = read_value(json, 'set2EndTemperatureMin', self._set2_end_temperature_min)
        self._set2_end_temperature_max = read_value(json, 'set2EndTemperatureMax', self._set2_end_temperature_max)
        self._has_changed = True
        return self._has_changed

class HwsParameters:
    """Temperature set limits for the HWS tank"""

    def __init__(self, json=None) -> None:
        self._hpu_operation_status = constants.AquareaOperationStatus.Off
        self._operation_mode = constants.AquareaOperationMode.Off
        self._boost_mode = constants.AquareaOperationStatus.Off
        self._tank_temperature: float | None = None
        self._outdoor_temperature: float | None = None    
        self.load(json)

    @property
    def has_changed(self):
        return self._has_changed


    @property
    def hpu_operation_status(self):
        return self._hpu_operation_status
    @hpu_operation_status.setter
    def hpu_operation_status(self, value):
        if self._hpu_operation_status == value:
            return
        self._hpu_operation_status = value
        self._has_changed = True

    @property
    def operation_mode(self):
        return self._operation_mode
    @operation_mode.setter
    def operation_mode(self, value):
        if self._operation_mode == value:
            return
        self._operation_mode = value
        self._has_changed = True

    @property
    def boost_mode(self):
        return self._boost_mode
    @boost_mode.setter
    def boost_mode(self, value):
        if self._boost_mode == value:
            return
        self._boost_mode = value
        self._has_changed = True

    @property
    def tank_temperature(self):
        return self._tank_temperature
    @tank_temperature.setter
    def tank_temperature(self, value):
        if self._tank_temperature == value:
            return
        self._tank_temperature = value
        self._has_changed = True
    
    @property
    def outdoor_temperature(self):
        return self._outdoor_temperature
    @outdoor_temperature.setter
    def outdoor_temperature(self, value):
        if self._outdoor_temperature == value:
            return
        self._outdoor_temperature = value
        self._has_changed = True    
    
    def load(self, json) -> bool:
        if not json:
            return False
        self._has_changed = False

        self._hpu_operation_status = read_enum(json, 'hpuOperationStatus', constants.AquareaOperationStatus, self._hpu_operation_status)
        self._operation_mode = read_enum(json, 'operationMode', constants.AquareaOperationStatus,self._operation_mode)
        self._boost_mode = read_enum(json, 'boostMode', constants.AquareaOperationStatus, self._boost_mode)
        self._tank_temperature = read_value(json, 'tankTemperature', self._tank_temperature)
        self._outdoor_temperature = read_value(json, 'outdoorTemperature', self._outdoor_temperature)

        self._has_changed = True
        return self._has_changed
    
class HwsDeviceParameters:
    """Live status of a standalone Heat Pump Hot Water tank unit
    (deviceType "11", e.g. HE-UM40CR).

    Parsed directly from the ``parameters`` object already present in the
    ``/device/group`` response — unlike air conditioners, this device class
    doesn't support a per-device ``deviceStatus`` refresh call (it 403s), so
    there's nothing more to fetch beyond what the group listing already
    contains.

    The exact meaning of ``operation_mode`` (and whether
    ``hpu_operation_status`` is a user-controllable power switch or just a
    read-only "is it actively heating right now" indicator, analogous to
    Aquarea's ``direction``/``pump_duty``) hasn't been confirmed yet — only
    ``tank_temperature`` and ``boost_mode`` have been verified against a real
    device.
    """

    def __init__(self, json=None) -> None:
        self._permission: int | None = None
        self._weekly_mode: bool | None = None
        self._pv_mode: bool | None = None
        self._holiday_mode: bool | None = None

        self._parameters: HwsParameters | None = None
        self._limits: HwsTemperatureSettingLimits | None = None
        self._has_changed = False
        self.load(json)

    @property
    def has_changed(self):
        return self._has_changed


    def load(self, json) -> bool:
        if not json:
            return False
        self._has_changed = False

        self._permission = read_value(json, 'permission', self._permission)
        self._weekly_mode = read_value(json, 'weeklyMode', self._weekly_mode)
        self._pv_mode = read_value(json, 'pvMode', self._pv_mode)
        self._holiday_mode = read_value(json, 'holidayMode', self._holiday_mode)


        self._load_parameters(json)
        self._load_temperature_setting_limits(json)
        
        has_changed = self._has_changed
        self._has_changed = False
        return has_changed

    def _load_temperature_setting_limits(self, json):
        limits_json = json.get('temperatureSettingLimits')
        if not limits_json:
            self._has_limits = False
            return
        self._has_limits = True
        if not self._limits:
            self._limits = HwsTemperatureSettingLimits(limits_json)
        else:
            self._limits.load(limits_json)
        self._has_changed = True

    def _load_parameters(self, json):
        parameters_json = json.get('parameters')
        if not parameters_json:
            self._has_parameters = False
            return
        self._has_parameters = True
        if not self._parameters:
            self._parameters = HwsParameters(parameters_json)
        else:
            self._parameters.load(parameters_json)
        self._has_changed = True
