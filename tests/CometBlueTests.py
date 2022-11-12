import re
import unittest
from datetime import datetime

from cometblue import CometBlue, Weekday


class CometBlueTest(unittest.TestCase):
    MAC = "00:00:00:00:00:00"

    def setUp(self) -> None:
        if self.MAC == "00:00:00:00:00:00":
            raise EnvironmentError("MAC address not set")

    def test_pin_conversion_zero(self):
        pin = CometBlue.transform_pin(0)
        self.assertEqual(bytearray(b'\x00\x00\x00\x00'), pin)

    def test_pin_conversion(self):
        pin = CometBlue.transform_pin(123456)
        self.assertEqual(bytearray(b'\x40\xE2\x01\x00'), pin)

    def test_read_weekday(self):
        with CometBlue(self.MAC) as blue:
            result: dict = blue.get_weekday(Weekday.FRIDAY)
            self.assertRegex(str(result), re.compile(
                r"{(\'start[1-4]\': \'((2[0-3])|([01][0-9])):[0-5][0-9]\'," +
                r" \'end[1-4]\': \'((2[0-3])|([01][0-9])):[0-5][0-9]\'(, )?){4}}"
            ))

    def test_write_read_holiday(self):
        with CometBlue(self.MAC) as blue:
            blue.set_holiday(2, {"start": datetime(2020, 12, 26, 18),
                                 "end": datetime(2021, 1, 5, 14),
                                 "temperature": 16.5})

        with CometBlue(self.MAC) as blue:
            result: dict = blue.get_holiday(2)

        self.assertRegex(str(result), re.compile(
            r"{'start': datetime.datetime\(20[0-9]{2}, [1]?[0-9], [1-3]?[0-9], [12]?[0-9], 0\), " +
            r"'end': datetime.datetime\(20[0-9]{2}, [1]?[0-9], [1-3]?[0-9], [12]?[0-9], 0\), " +
            r"'temperature': [0-9]+\.[05]}"
        ))

    def test_read_temperature(self):
        with CometBlue(self.MAC) as blue:
            result = blue.get_temperature()
            self.assertRegex(str(result), re.compile(
                r"{'currentTemp': [0-9]+\.[05], 'manualTemp': [0-9]+\.[05], 'targetTempLow': [0-9]+\.[05], " +
                r"'targetTempHigh': [0-9]+\.[05], 'tempOffset': [0-9]+\.[05], 'windowOpen': (True|False), " +
                r"'windowOpenMinutes': [0-9]+}"
            ))

    def test_read_write_temperature(self):
        with CometBlue(self.MAC) as blue:
            blue.set_temperature({"manualTemp": 8})

        with CometBlue(self.MAC) as blue:
            result = blue.get_temperature()
            self.assertRegex(str(result), re.compile(
                r"{'currentTemp': [0-9]+\.[05], 'manualTemp': 8.0, 'targetTempLow': [0-9]+\.[05], " +
                r"'targetTempHigh': [0-9]+\.[05], 'tempOffset': [0-9]+\.[05], 'windowOpen': (True|False), " +
                r"'windowOpenMinutes': [0-9]+}"
            ))

    def test_read_all(self):
        """
        For manual verification
        """
        with CometBlue(self.MAC) as blue:
            result: dict = blue.get_multiple(["temperature", "battery", "datetime", "holidays", "weekdays"])
        print(result)

    def test_discovery(self):
        """Test discover"""
        blue = CometBlue(self.MAC)
        devices = blue.discover(30)
        print(devices)
        self.assertGreater(len(devices), 0)


if __name__ == '__main__':
    unittest.main()
