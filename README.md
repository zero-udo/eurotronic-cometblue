# CometBlue

eurotronic-cometblue is a library to communicate with your Eurotronic GmbH Comet Blue radiator controllers.

The device supports up to four programmable schedules for each weekday. Longer periods can be set as holidays. There are 8 holiday slots available.

This library depends on [bleak](https://github.com/hbldh/bleak) and runs therefore on Linux, Windows and macOS (thanks to [rikroe](https://github.com/rikroe)).

## Compatible devices

Comet Blue radiator controllers are sold under different names:

| "Manufacturer" | Model      |       Tested       |
|----------------|------------|:------------------:|
| Eurotronic     | Comet Blue | :heavy_check_mark: |
| Sygonix        | HT100 BT   | :heavy_check_mark: |
| Xavax          | Hama       |  :grey_question:   |
| Silvercrest    | RT2000BT   |  :grey_question:   |

This library should work with all listed radiator controllers, but is only tested with a Sygonix HT100BT which is the only one I own.

Thanks to [@FloSchmidt](https://github.com/FloSchmidt) for [checking](https://github.com/zero-udo/eurotronic-cometblue/issues/5) the Eurotronic Comet Blue 

If your device is not listed here but looks similar (or you know it is a rebranded Comet Blue), or if you are able to test this library with another device - let me know your results.
## Installation

Just 
```
pip install eurotronic-cometblue
```

## Usage

Import the library and instantiate an object.

Parameters are the device MAC-Address and the (optional) PIN. Depending on your connection quality you can specify a longer or shorter discovery duration.

| Parameter | required? | default value |
|-----------|:---------:|---------------|
| mac       |    yes    | None          |
| pin       |    no     | 0             |
| timeout   |    no     | 2             |



```python
from cometblue import CometBlue

blue = CometBlue(mac="00:00:00:00:00:00",pin=123456, timeout=2)
```
or 
```python
from cometblue import AsyncCometBlue

blue = AsyncCometBlue(mac="00:00:00:00:00:00",pin=123456, timeout=2)
```
for an asynchronous client.

The following (synchronous) methods are available, for the asynchronous variants add `_async`:

| Method            | Parameter                                                                                                                                                                                                                                                                                                     | Return Value                                                                                                                                                                            |
|-------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `get_temperature` | None                                                                                                                                                                                                                                                                                                          | `dict` with <ul><li>'currentTemp'</li><li>'manualTemp'</li><li>'targetTempLow'</li><li>'targetTempHigh'</li><li>'tempOffset'</li><li>'windowOpen'</li><li>'windowOpenMinutes'</li></ul> |
| `set_temperature` | `dict` with the same values as `get_temperature`. Not all values have to be set.                                                                                                                                                                                                                              | None                                                                                                                                                                                    |
| `get_battery`     | None                                                                                                                                                                                                                                                                                                          | `int` - Battery value in percent                                                                                                                                                        |
| `get_datetime`    | None                                                                                                                                                                                                                                                                                                          | `datetime` - currently set date and time of the device. Used for schedules                                                                                                              |
| `set_datetime`    | An optional `datetime`-object. The current date and time is used if the parameter is omitted.                                                                                                                                                                                                                 | None                                                                                                                                                                                    |
| `get_weekday`     | A `Weekday`-Enum value eg. `Weekday.MONDAY`                                                                                                                                                                                                                                                                   | `dict` with `start#` and `end#` (# = 1-4) keys and the time as HH:mm formatted `str`s as values                                                                                         |
| `set_weekday`     | A `Weekday`-Enum value eg. `Weekday.MONDAY` and a `dict` containing `start#` and `end#` (# = 1-4) as keys and HH:mm formatted `str`s as values                                                                                                                                                                | None                                                                                                                                                                                    |
| `get_holiday`     | `int` 1-8 to select the holiday period                                                                                                                                                                                                                                                                        | `dict` with <ul><li>'start': `datetime`</li><li>'end': `datetime`</li><li>'temperature': `float`</li></ul>                                                                              |
| `set_holiday`     | `dict` with the same values as `get_holiday`s return value.                                                                                                                                                                                                                                                   | None                                                                                                                                                                                    |
| `get_manual_mode` | None                                                                                                                                                                                                                                                                                                          | `True` if manual mode is set. <br>`False` if the schedule is used                                                                                                                       |
| `set_manual_mode` | `boolean` - `True` if manual mode should be used. `False` if the schedule should be used                                                                                                                                                                                                                      | None                                                                                                                                                                                    |
| `get_multiple`    | Retrieves multiple values specified in a `list`. Valid values are: <ul><li>'temperature'</li><li>'battery'</li><li>'datetime'</li><li>'holiday#' # = 1-8 or</li><li>'holidays' (retrieves holiday1-8)</li><li>'monday'</li><li>'tuesday'</li><li>etc...</li><li>'weekdays' (retrieves all weekdays)</li></ul> | The values as a `dict` in the format defined by the appropriate methods                                                                                                                 |
| `discover`        | timeout: `int`, timeout used for discovery                                                                                                                                                                                                                                                                    | MAC-addresses of all discovery Comet Blue devices                                                                                                                                       |

:warning: the device applies set values when the connection is closed, not directly after setting them

## Examples

Use `CometBlueAsync` and `[method_name]_async` for asynchronous handling.

### Instantiating and retrieving the current temperature

```python
from cometblue import CometBlue

blue = CometBlue("00:00:00:00:00:00", 123456)
blue.connect()
temp = blue.get_temperature()
print(temp) 
blue.disconnect()
```

or

```python
from cometblue import CometBlue

with CometBlue("00:00:00:00:00:00", 123456) as blue:
    temp = blue.get_temperature()
    print(temp)
```

results in 

```python
{
    'currentTemp': 24.5, 
    'manualTemp': 16.0, 
    'targetTempLow': 16.0, 
    'targetTempHigh': 20.0, 
    'tempOffset': 0.0, 
    'windowOpen': True, 
    'windowOpenMinutes': 10
}
```

### Setting a new schedule

Setting a new schedule for Mondays with two heating periods:

- Period 1 from 06:00 to 08:00

- Period 2 from 16:00 to 22:00

To use this schedule, make sure to disable manual mode.

```python
blue.set_weekday(Weekday.MONDAY, 
        {"start1": "06:00", "end1": "08:00", 
         "start2": "16:00", "end2": "22:00" })
blue.set_manual_mode(False)
```

### Setting a holiday

Setting a holiday (slot 2) from 26th December 2020 18:00 till 5th January 2021 14:00 and keep the temperature at 16.5 °C

```python
blue.set_holiday(2, {"start": datetime(2020, 12, 26, 18), 
                     "end": datetime(2021, 1, 5, 14),
                     "temperature": 16.5 })
```

## Credits:

* Thorsten Tränker for his reverse engineering work done [here](https://www.torsten-traenkner.de/wissen/smarthome/heizung.php)
* [rikroe](https://github.com/rikroe) for the switch to bleak
