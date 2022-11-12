import asyncio
import platform
import re
from datetime import datetime
from enum import Enum
from typing import Dict, List, Union
from uuid import UUID

from bleak import BLEDevice, BleakClient, BleakScanner
from bleak.exc import BleakError

from . import const

MAC_REGEX = re.compile('([0-9A-F]{2}:){5}[0-9A-F]{2}')
UUID_REGEX = re.compile('^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')


class Weekday(Enum):
    MONDAY = 1,
    TUESDAY = 2,
    WEDNESDAY = 3,
    THURSDAY = 4,
    FRIDAY = 5,
    SATURDAY = 6,
    SUNDAY = 7


WEEKDAY = {
    Weekday.MONDAY: const.CHARACTERISTIC_MONDAY,
    Weekday.TUESDAY: const.CHARACTERISTIC_TUESDAY,
    Weekday.WEDNESDAY: const.CHARACTERISTIC_WEDNESDAY,
    Weekday.THURSDAY: const.CHARACTERISTIC_THURSDAY,
    Weekday.FRIDAY: const.CHARACTERISTIC_FRIDAY,
    Weekday.SATURDAY: const.CHARACTERISTIC_SATURDAY,
    Weekday.SUNDAY: const.CHARACTERISTIC_SUNDAY
}

HOLIDAY = {
    1: const.CHARACTERISTIC_HOLIDAY_1,
    2: const.CHARACTERISTIC_HOLIDAY_2,
    3: const.CHARACTERISTIC_HOLIDAY_3,
    4: const.CHARACTERISTIC_HOLIDAY_4,
    5: const.CHARACTERISTIC_HOLIDAY_5,
    6: const.CHARACTERISTIC_HOLIDAY_6,
    7: const.CHARACTERISTIC_HOLIDAY_7,
    8: const.CHARACTERISTIC_HOLIDAY_8,
}


class AsyncCometBlue:
    """Asynchronous adapter for Eurotronic Comet Blue (and rebranded) bluetooth TRV."""

    device: Union[BLEDevice, str]
    connected: bool
    pin: bytearray
    timeout: int
    client: BleakClient

    def __init__(self, device: Union[BLEDevice, str], pin=0, timeout=2):
        if isinstance(device, str):
            if bool(MAC_REGEX.match(device)) is False and platform.system() != "Darwin":
                raise ValueError(
                    "device must be a valid Bluetooth Address in the format XX:XX:XX:XX:XX:XX or a bleak.BLEDevice."
                )
            if bool(UUID_REGEX.match(device)) is False and platform.system() == "Darwin":
                raise ValueError(
                    "device must be a valid UUID in the format XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX or bleak.BLEDevice."
                )
        if 0 > pin >= 100000000:
            raise ValueError("pin can only consist of digits. Up to 8 digits allowed.")

        self.device = device
        self.pin = self.transform_pin(pin)
        self.timeout = timeout
        self.connected = False

    async def __read_value(self, characteristic: UUID) -> bytearray:
        """
        Reads a characteristic and provides the data as a bytearray. Disconnects afterwards.

        :param characteristic: UUID of the characteristic to read
        :return: bytearray containing the read values
        """
        value = await self.client.read_gatt_char(characteristic)
        return value

    async def __write_value(self, characteristic: UUID, new_value: bytearray):
        """
        Writes a bytearray to the specified characteristic. Disconnects afterwards to apply written changes.

        :param characteristic: UUID of the characteristic to write
        :param new_value: bytearray containing the new values
        :return:
        """
        await self.client.write_gatt_char(characteristic, new_value, response=True)

    @staticmethod
    def transform_pin(pin: int):
        """
        Transforms the pin a bytearray required by the Comet Blue device.

        :param pin: the pin to use
        :return: bytearray representing the pin
        """
        return bytearray(pin.to_bytes(4, 'little', signed=False))

    @staticmethod
    def __to_time_str(value: int) -> str:
        """
        Transforms a Comet Blue time representation to a human-readable time-string.

        :param value:
        :return:
        """
        hour = int(value / 6)
        minutes = int(value % 6) * 10
        return str.format("{0:02d}:{1:02d}", hour, minutes)

    @staticmethod
    def __from_time_string(value: str) -> int:
        """
        Transforms a time-string to the Comet Blue byte representation.

        :param value: time-string in format HH:mm
        :returns int: the Comet Blue representation of the given time, or 0 if invalid
        :rtype: int
        """
        split = value.split(":")
        hour = int(split[0]) * 6
        minutes = int(int(split[1]) / 10)

        if hour not in range(0, 24) or minutes not in range(0, 60):
            return 0

        return hour + minutes

    @staticmethod
    def __transform_temperature_response(value: bytearray) -> dict:
        """
        Transforms a temperature response to a dictionary containing the values.

        :param value: bytearray retrieved from the device
        :return: dict containing the values
        """
        result = dict()
        result["currentTemp"] = value[0] / 2
        result["manualTemp"] = value[1] / 2
        result["targetTempLow"] = value[2] / 2
        result["targetTempHigh"] = value[3] / 2
        result["tempOffset"] = value[4] / 2
        result["windowOpen"] = value[5] == 0xF0
        result["windowOpenMinutes"] = value[6]

        return result

    @staticmethod
    def __transform_temperature_request(values: Dict[str, float]) -> bytearray:
        """
        Transforms a temperature dictionary to a bytearray to be transferred to the device.
        Valid dictionary entries are [manualTemp, targetTempLow, targetTempHigh, tempOffset].

        :param values: a dict[str, float] containing the values
        :return: the transformed bytearray
        """
        new_value = bytearray(7)
        new_value[0] = const.UNCHANGED_VALUE

        if values.get("manualTemp") is not None:
            new_value[1] = int(values.get("manualTemp") * 2)
        else:
            new_value[2] = const.UNCHANGED_VALUE

        if values.get("targetTempLow") is not None:
            new_value[2] = int(values.get("targetTempLow") * 2)
        else:
            new_value[2] = const.UNCHANGED_VALUE

        if values.get("targetTempHigh") is not None:
            new_value[3] = int(values.get("targetTempHigh") * 2)
        else:
            new_value[3] = const.UNCHANGED_VALUE

        if values.get("tempOffset") is not None:
            new_value[4] = int(values.get("tempOffset") * 2)
        else:
            new_value[4] = const.UNCHANGED_VALUE

        new_value[5] = const.UNCHANGED_VALUE
        new_value[6] = const.UNCHANGED_VALUE
        return new_value

    @staticmethod
    def __transform_datetime_response(value: bytearray) -> datetime:
        """
        Transforms a date response to a datetime object.

        :param value: the retrieved bytearray
        :return: the transformed datetime
        """
        minute = value[0]
        hour = value[1]
        day = value[2]
        month = value[3]
        year = value[4] + 2000
        dt = datetime(year, month, day, hour, minute)
        return dt

    @staticmethod
    def __transform_datetime_request(value: datetime) -> bytearray:
        """
        Transforms a datetime object to a bytearray to be transferred to the device.

        :param value: the datetime to be transferred
        :return: bytearray representation of the datetime
        """
        new_value = bytearray(5)
        new_value[0] = value.minute
        new_value[1] = value.hour
        new_value[2] = value.day
        new_value[3] = value.month
        new_value[4] = value.year % 100
        return new_value

    def __transform_weekday_response(self, value: bytearray) -> dict:
        """
        Transforms a weekday response to a dictionary containing all four start and end times.

        :param value: bytearray retrieved from the device
        :return: dict containing start1-4 and end1-4 times
        """
        result = dict()
        result["start1"] = self.__to_time_str(value[0])
        result["end1"] = self.__to_time_str(value[1])
        result["start2"] = self.__to_time_str(value[2])
        result["end2"] = self.__to_time_str(value[3])
        result["start3"] = self.__to_time_str(value[4])
        result["end3"] = self.__to_time_str(value[5])
        result["start4"] = self.__to_time_str(value[6])
        result["end4"] = self.__to_time_str(value[7])
        return result

    def __transform_weekday_request(self, values: dict) -> bytearray:
        """
        Transforms a dictionary containing start1-4 and end1-4 times to a bytearray used by the device.

        :param values: dict with start# and end# values. # = 1-4. Pattern "HH:mm"
        :return: bytearray to be transferred to the device
        """
        start1 = self.__from_time_string(values["start1"])
        end1 = self.__from_time_string(values["end1"])
        start2 = self.__from_time_string(values["start2"])
        end2 = self.__from_time_string(values["end2"])
        start3 = self.__from_time_string(values["start3"])
        end3 = self.__from_time_string(values["end3"])
        start4 = self.__from_time_string(values["start4"])
        end4 = self.__from_time_string(values["end4"])

        values = []
        if start1 is not None and end1 is not None and start1 != end1:
            values.append(start1)
            values.append(end1)
        if start2 is not None and end2 is not None and start2 != end2:
            values.append(start2)
            values.append(end2)
        if start3 is not None and end3 is not None and start3 != end3:
            values.append(start3)
            values.append(end3)
        if start4 is not None and end4 is not None and start4 != end4:
            values.append(start4)
            values.append(end4)

        new_value = bytearray(8)
        for i in range(len(values)):
            new_value[i] = values[i]

        return new_value

    @staticmethod
    def __transform_holiday_response(values: bytearray) -> dict:
        """
        Transforms a retrieved holiday response to a dictionary containing start and end `datetime`s as well as the set
        temperature.

        :param values: bytearray retrieved from the device
        :return: dictionary containing start: datetime, end: datetime and temperature: float or empty if bytearray is
        malformed
        """
        # validate values
        if values[3] not in range(0, 100) or \
                values[2] not in range(1, 13) or \
                values[1] not in range(1, 31) or \
                values[0] not in range(0, 25) or \
                values[7] not in range(0, 100) or \
                values[6] not in range(1, 13) or \
                values[5] not in range(1, 31) or \
                values[4] not in range(0, 25):
            return dict()

        start = datetime(values[3] + 2000, values[2], values[1], values[0])
        end = datetime(values[7] + 2000, values[6], values[5], values[4])
        temperature = values[8] / 2
        result = {"start": start, "end": end, "temperature": temperature}

        return result

    @staticmethod
    def __transform_holiday_request(values: dict) -> bytearray:
        """
        Transforms a dictionary containing start: datetime, end: datetime as well as temperature: float to a bytearray
        to be transferred to the device.

        :param values: dictionary containing start: datetime, end: datetime, temperature: float
        :return: bytearray to be transferred to the device
        """
        if not values.__contains__("start") or not values.__contains__("end") or not values.__contains__("temperature"):
            print("Nope")
            return bytearray(9)

        start: datetime = values["start"]
        end: datetime = values["end"]
        temperature = float(values["temperature"])

        new_value = bytearray(9)
        if start != end and 29 > temperature >= 8:
            new_value[0] = start.hour
            new_value[1] = start.day
            new_value[2] = start.month
            new_value[3] = start.year % 100
            new_value[4] = end.hour
            new_value[5] = end.day
            new_value[6] = end.month
            new_value[7] = end.year % 100
            new_value[8] = int(temperature * 2)

        return new_value

    async def connect_async(self):
        """
        Connects to the device. Increases connection-timeout if connection could not be established up to twice the
        initial timeout. Max 10 retries.

        :return:
        """
        timeout = self.timeout
        tries = 0
        while not self.connected and tries < 10:
            try:
                self.client = BleakClient(self.device)
                await self.client.connect()
                await self.__write_value(const.CHARACTERISTIC_PIN, self.pin)
                self.connected = True
            except BleakError:
                timeout += 2
                timeout = min(timeout, 2 * self.timeout)

    async def disconnect_async(self):
        """
        Disconnects the device.

        :return:
        """
        if self.connected:
            await self.client.disconnect()
            self.connected = False

    async def get_temperature_async(self) -> dict:
        """Retrieves the temperature configurations from the device.

        :return: dict of the retrieved values
        """
        value = await self.__read_value(const.CHARACTERISTIC_TEMPERATURE)
        return self.__transform_temperature_response(value)

    async def set_temperature_async(self, values: Dict[str, float]):
        """Sets the time from the device.
        Allowed values for updates are:
           - manualTemp: temperature for the manual mode
           - targetTempLow: lower bound for the automatic mode
           - targetTempHigh: upper bound for the automatic mode
           - tempOffset: offset for the measured temperature

        All temperatures are in 0.5°C steps

        :param values: Dictionary containing the new values.
        """
        if values is None:
            return

        new_value = self.__transform_temperature_request(values)
        await self.__write_value(const.CHARACTERISTIC_TEMPERATURE, new_value)

    async def get_battery_async(self):
        """
        Retrieves the battery level in percent from the device

        :return: battery level in percent
        """
        return (await self.__read_value(const.CHARACTERISTIC_BATTERY))[0]

    async def get_datetime_async(self) -> datetime:
        """
        Retrieve the current set date and time of the device - used for schedules

        :return: the retrieved datetime
        """
        result = await self.__read_value(const.CHARACTERISTIC_DATETIME)
        return self.__transform_datetime_response(result)

    async def set_datetime_async(self, date: datetime = datetime.now()):
        """
        Sets the date and time of the device - used for schedules

        :param date: a datetime object, defaults to now
        """
        new_value = self.__transform_datetime_request(date)
        await self.__write_value(const.CHARACTERISTIC_DATETIME, new_value)

    async def get_weekday_async(self, weekday: Weekday) -> dict:
        """
        Retrieves the start and end times of all programed heating periods for the given day.

        :param weekday: the day to query
        :return: dict with start# and end# values. # = 1-4
        """
        uuid = WEEKDAY.get(weekday)
        value = await self.__read_value(uuid)
        return self.__transform_weekday_response(value)

    async def set_weekday_async(self, weekday: Weekday, values: dict):
        """
        Sets the start and end times for programed heating periods for the given day.

        :param weekday: the day to set
        :param values: dict with start# and end# values. # = 1-4. Pattern "HH:mm"
        """

        new_value = self.__transform_weekday_request(values)
        await self.__write_value(WEEKDAY.get(weekday), new_value)

    async def get_holiday_async(self, number: int) -> dict:
        """
        Retrieves the configured holiday 1-8.

        :param number: the number of the holiday season. Values 1-8 allowed
        :return: dict { start: datetime, end: datetime, temperature: float }
        """
        if number not in range(1, 9):
            return {}

        values = await self.__read_value(HOLIDAY[number])
        return self.__transform_holiday_response(values)

    async def set_holiday_async(self, number: int, values: dict):
        """
        Sets the configured holiday 1-8.

        :param number: the number of the holiday season. Values 1-8 allowed
        :param values: start: datetime, end: datetime, temperature: float (0.5 degree steps)
        """
        new_value = self.__transform_holiday_request(values)
        await self.__write_value(HOLIDAY[number], new_value)

    async def get_manual_mode_async(self) -> bool:
        """
        Retrieves if manual mode is enabled
        :return: True - if manual mode is enabled, False if not
        """
        mode = await self.__read_value(const.CHARACTERISTIC_SETTINGS)
        return bool(mode[0] & 0x01)

    async def set_manual_mode_async(self, value: bool):
        """
        Enables/Disables the manual mode.

        :param value: True - if manual mode should be enabled, False if not
        :return:
        """
        mode = bytearray(3)
        if value:
            mode[0] = 0x01

        mode[1] = const.UNCHANGED_VALUE
        mode[2] = const.UNCHANGED_VALUE
        await self.__write_value(const.CHARACTERISTIC_SETTINGS, mode)

    def _prepare_get_multiples(self, values: List[str]) -> dict:
        """
        Generate dictionary for get_multiples().

        :param values: List of information to be retrieved. Valid entries are ['temperature', 'battery', 'datetime',
        'holiday#' # = 1-8 or 'holidays' (retrieves holiday1-8), 'monday', 'tuesday', etc..., 'weekdays' (retrieves all
        weekdays), 'manual']
        :return: dictionary of type {key: (func_name, parameter)}.
        """
        result = dict()

        if len(values) == 0:
            return result

        switcher_holidays = {
            str.format("holiday{}", day): ("get_holiday", day) for day in HOLIDAY
        }
        switcher_weekdays = {
            "monday": ("get_weekday", Weekday.MONDAY),
            "tuesday": ("get_weekday", Weekday.TUESDAY),
            "wednesday": ("get_weekday", Weekday.WEDNESDAY),
            "thursday": ("get_weekday", Weekday.THURSDAY),
            "friday": ("get_weekday", Weekday.FRIDAY),
            "saturday": ("get_weekday", Weekday.SATURDAY),
            "sunday": ("get_weekday", Weekday.SUNDAY),
        }

        switcher = {
            "temperature": ("get_temperature", None),
            "battery": ("get_battery", None),
            "datetime": ("get_datetime", None),
            **switcher_holidays,
            "holidays": switcher_holidays,
            **switcher_weekdays,
            "weekdays": switcher_weekdays,
            "manual": ("get_manual_mode", None),
        }

        for v in values:
            tmp = switcher.get(v)
            if isinstance(tmp, dict):
                result.update(tmp)
            else:
                result[v] = tmp

        return result

    async def get_multiple_async(self, values: List[str]) -> dict:
        """
        Retrieve multiple information at once. More performant than calling them by themselves - only one connection is
        used.

        :param values: List of information to be retrieved. Valid entries are ['temperature', 'battery', 'datetime',
        'holiday#' # = 1-8 or 'holidays' (retrieves holiday1-8), 'monday', 'tuesday', etc..., 'weekdays' (retrieves all
        weekdays), 'manual']
        :return: dictionary containing all requested information.
        """
        result = {
            k: await getattr(self, f"{v[0]}_async")(v[1]) if v[1] else await getattr(self, f"{v[0]}_async")()
            for k, v in self._prepare_get_multiples(values).items()
        }
        return result

    async def __aenter__(self):
        await self.connect_async()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect_async()

    @classmethod
    async def discover_async(cls, timeout=5) -> List[BLEDevice]:
        """
        Discovers available CometBlue devices.

        :param timeout: Duration of Bluetooth scan.
        :return: List of CometBlue BLEDevices.
        """
        devices = await BleakScanner.discover(timeout, return_adv=True)
        cometblue_devices = [
            d[0] for d in devices.values() if const.SERVICE in d[1].service_uuids
        ]
        return cometblue_devices


class CometBlue(AsyncCometBlue):
    """Synchronous adapter for Eurotronic Comet Blue (and rebranded) bluetooth TRV.

    If possible, use the async AsyncCometBlue."""

    _loop: asyncio.AbstractEventLoop

    def __run_in_loop(self, main):
        """
        Helper to run async functions synchronized.

        :param main: function with all parameters, e.g. self.get_weekday_async(1)
        :return: return value of main
        """
        if not hasattr(self, "_loop") or not self._loop:
            self._loop = asyncio.new_event_loop()

        return self._loop.run_until_complete(main)

    def connect(self):
        """
        Connects to the device. Increases connection-timeout if connection could not be established up to twice the
        initial timeout. Max 10 retries.

        :return:
        """
        self.__run_in_loop(self.connect_async())

    def disconnect(self):
        """
        Disconnects the device.

        :return:
        """
        self.__run_in_loop(self.disconnect_async())

    def get_temperature(self) -> dict:
        """Retrieves the temperature configurations from the device.

        :return: dict of the retrieved values
        """
        return self.__run_in_loop(self.get_temperature_async())

    def set_temperature(self, values: Dict[str, float]):
        """Sets the time from the device.
        Allowed values for updates are:
           - manualTemp: temperature for the manual mode
           - targetTempLow: lower bound for the automatic mode
           - targetTempHigh: upper bound for the automatic mode
           - tempOffset: offset for the measured temperature

        All temperatures are in 0.5°C steps

        :param values: Dictionary containing the new values.
        """
        self.__run_in_loop(self.set_temperature_async(values))

    def get_battery(self):
        """
        Retrieves the battery level in percent from the device

        :return: battery level in percent
        """
        return self.__run_in_loop(self.get_battery_async())

    def get_datetime(self) -> datetime:
        """
        Retrieve the current set date and time of the device - used for schedules

        :return: the retrieved datetime
        """
        return self.__run_in_loop(self.get_datetime_async())

    def set_datetime(self, date: datetime = datetime.now()):
        """
        Sets the date and time of the device - used for schedules

        :param date: a datetime object, defaults to now
        """
        self.__run_in_loop(self.set_datetime_async(date))

    def get_weekday(self, weekday: Weekday) -> dict:
        """
        Retrieves the start and end times of all programed heating periods for the given day.

        :param weekday: the day to query
        :return: dict with start# and end# values. # = 1-4
        """
        return self.__run_in_loop(self.get_weekday_async(weekday))
    def set_weekday(self, weekday: Weekday, values: dict):
        """
        Sets the start and end times for programed heating periods for the given day.

        :param weekday: the day to set
        :param values: dict with start# and end# values. # = 1-4. Pattern "HH:mm"
        """
        self.__run_in_loop(self.set_weekday_async(weekday, values))

    def get_holiday(self, number: int) -> dict:
        """
        Retrieves the configured holiday 1-8.

        :param number: the number of the holiday season. Values 1-8 allowed
        :return: dict { start: datetime, end: datetime, temperature: float }
        """
        return self.__run_in_loop(self.get_holiday_async(number))

    def set_holiday(self, number: int, values: dict):
        """
        Set the configured holiday 1-8.

        :param number: the number of the holiday season. Values 1-8 allowed
        :param values: start: datetime, end: datetime, temperature: float (0.5 degree steps)
        """
        self.__run_in_loop(self.set_holiday_async(number, values))

    def get_manual_mode(self) -> bool:
        """
        Retrieves if manual mode is enabled

        :return: True - if manual mode is enabled, False if not
        """
        return self.__run_in_loop(self.get_manual_mode_async())

    def set_manual_mode(self, value: bool):
        """
        Enables/Disables the manual mode.

        :param value: True - if manual mode should be enabled, False if not
        :return:
        """
        return self.__run_in_loop(self.set_manual_mode_async(value))

    def get_multiple(self, values: List[str]) -> dict:
        """
        Retrieve multiple information at once. More performant than calling them by themselves - only one connection is
        used.

        :param values: List of information to be retrieved. Valid entries are ['temperature', 'battery', 'datetime',
        'holiday#' # = 1-8 or 'holidays' (retrieves holiday1-8), 'monday', 'tuesday', etc..., 'weekdays' (retrieves all
        weekdays), 'manual']
        :return: dictionary containing all requested information.
        """
        result = {
            k: getattr(self, v[0])(v[1]) if v[1] else getattr(self, v[0])()
            for k, v in self._prepare_get_multiples(values).items()
        }
        return result

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        self._loop.close()
        self._loop = None

    @classmethod
    def discover(cls, timeout=5) -> list:
        """
        Discovers available CometBlue devices.

        :param timeout: Duration of Bluetooth scan.
        :return: List of CometBlue device MACs.
        """
        loop = asyncio.new_event_loop()
        cometblue_devices = loop.run_until_complete(cls.discover_async(timeout))
        return [d.address for d in cometblue_devices]
