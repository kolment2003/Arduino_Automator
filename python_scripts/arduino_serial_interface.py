# general libraries
import logging as logger
from datetime import datetime
# custom libraries
from tools.config_logger import config_logger
from tools.arduino_resources import Interface, InterfaceType, Arduino


def main():
    config_logger(use_stream_handler=True)
    logger.info(f"Config Settings via serial com interface\n")
    # dt_obj = datetime(2021, 3, 31, 20, 4, 45)
    dt_obj = None
    alarm_ssrx_time_list = [datetime(1971, 1, 1, 10, 0, 0),
                            datetime(1971, 1, 1, 10, 30, 0),
                            datetime(1971, 1, 1, 13, 0, 0),
                            datetime(1971, 1, 1, 13, 30, 0),
                            datetime(1971, 1, 1, 15, 30, 0),
                            datetime(1971, 1, 1, 15, 0, 0),
                            datetime(1971, 1, 1, 14, 30, 0),
                            datetime(1971, 1, 1, 14, 0, 0)]

    # open serial com interface
    serial_com = Interface(InterfaceType.Serial)
    Arduino.get_wifi_status(serial_com)
    Arduino.get_wifi_ip_address(serial_com)
    Arduino.get_wifi_rssi(serial_com)
    # Config RTC and System time
    Arduino.config_rtc_time(serial_com, dt_obj=dt_obj)
    Arduino.get_rtc_time(serial_com)
    Arduino.get_rtc_config_flag(serial_com)
    Arduino.get_rtc_parse_flag(serial_com)
    Arduino.get_system_time(serial_com)
    # Read inputs
    Arduino.get_io_state(serial_com, "push_button", 1)
    Arduino.get_io_state(serial_com, "push_button", 2)
    Arduino.get_analog_reading(serial_com, input_num=1)
    Arduino.get_analog_reading(serial_com, input_num=2)
    Arduino.get_number_probes(serial_com)
    Arduino.get_probe_recognition(serial_com, input_num=1)
    Arduino.get_probe_reading(serial_com, input_num=1)
    Arduino.get_probe_recognition(serial_com, input_num=2)
    Arduino.get_probe_reading(serial_com, input_num=2)
    Arduino.get_probe_recognition(serial_com, input_num=3)
    Arduino.get_probe_reading(serial_com, input_num=3)
    Arduino.get_probe_recognition(serial_com, input_num=4)
    Arduino.get_probe_reading(serial_com, input_num=4)
    # Get loop through all IOs
    for x in range(1, 5):
        Arduino.get_io_state(serial_com, "ssr", x)
    for x in range(1, 5):
        Arduino.get_io_state(serial_com, "opto", x)
    for x in range(1, 5):
        Arduino.get_io_state(serial_com, "ssr", x)
    for x in range(1, 5):
        Arduino.get_io_state(serial_com, "opto", x)
    # Config SSR Alarms
    for x in range(1, 5):
        Arduino.config_output_alarm(serial_com, "ssr", x, True, True, alarm_ssrx_time_list[x - 1])
    for x in range(1, 5):
        Arduino.config_output_alarm(serial_com, "ssr", x, False, True, alarm_ssrx_time_list[x + 4 - 1])
    # Config Master Alarm
    Arduino.config_master_alarm_enable(serial_com, master_alarm_enable=True)
    # Config Expected Alarm States
    Arduino.config_expected_io_state(serial_com, output_type="ssr", output_num=1)
    Arduino.config_expected_io_state(serial_com, output_type="ssr", output_num=2)
    Arduino.config_expected_io_state(serial_com, output_type="ssr", output_num=3)
    Arduino.config_expected_io_state(serial_com, output_type="ssr", output_num=4)

    # close serial com interface
    serial_com.interface.close()


if __name__ == "__main__":
    # get_com_ports()
    main()
