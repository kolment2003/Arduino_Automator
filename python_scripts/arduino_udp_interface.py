# general libraries
import logging as logger
from datetime import datetime
# custom libraries
from tools.config_logger import config_logger
from tools.arduino_resources import Interface, InterfaceType, Arduino


def main():
    config_logger(use_stream_handler=True)
    logger.info(f"Config Settings via upd com interface\n")
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

    # open udp interface
    wifi_sock = Interface(InterfaceType.Wifi, timeout=0.2)
    Arduino.get_wifi_status(wifi_sock)
    Arduino.get_wifi_ip_address(wifi_sock)
    Arduino.get_wifi_rssi(wifi_sock)
    # Config RTC and System time
    Arduino.config_rtc_time(wifi_sock, dt_obj=dt_obj)
    Arduino.get_rtc_time(wifi_sock)
    Arduino.get_rtc_config_flag(wifi_sock)
    Arduino.get_rtc_parse_flag(wifi_sock)
    Arduino.get_system_time(wifi_sock)
    # Read inputs
    Arduino.get_io_state(wifi_sock, "push_button", 1)
    Arduino.get_io_state(wifi_sock, "push_button", 2)
    Arduino.get_analog_reading(wifi_sock, input_num=1)
    Arduino.get_analog_reading(wifi_sock, input_num=2)
    Arduino.get_number_probes(wifi_sock)
    Arduino.get_probe_recognition(wifi_sock, input_num=1)
    Arduino.get_probe_reading(wifi_sock, input_num=1)
    Arduino.get_probe_recognition(wifi_sock, input_num=2)
    Arduino.get_probe_reading(wifi_sock, input_num=2)
    Arduino.get_probe_recognition(wifi_sock, input_num=3)
    Arduino.get_probe_reading(wifi_sock, input_num=3)
    Arduino.get_probe_recognition(wifi_sock, input_num=4)
    Arduino.get_probe_reading(wifi_sock, input_num=4)
    # Get loop through all IOs
    for x in range(1, 5):
        Arduino.get_io_state(wifi_sock, "ssr", x)
    for x in range(1, 5):
        Arduino.get_io_state(wifi_sock, "opto", x)
    for x in range(1, 5):
        Arduino.get_io_state(wifi_sock, "ssr", x)
    for x in range(1, 5):
        Arduino.get_io_state(wifi_sock, "opto", x)
    # Config SSR Alarms
    for x in range(1, 5):
        Arduino.config_output_alarm(wifi_sock, "ssr", x, True, True, alarm_ssrx_time_list[x - 1])
    for x in range(1, 5):
        Arduino.config_output_alarm(wifi_sock, "ssr", x, False, True, alarm_ssrx_time_list[x + 4 - 1])
    # Config Master Alarm
    Arduino.config_master_alarm_enable(wifi_sock, master_alarm_enable=True)
    # Config Expected Alarm States
    Arduino.config_expected_io_state(wifi_sock, output_type="ssr", output_num=1)
    Arduino.config_expected_io_state(wifi_sock, output_type="ssr", output_num=2)
    Arduino.config_expected_io_state(wifi_sock, output_type="ssr", output_num=3)
    Arduino.config_expected_io_state(wifi_sock, output_type="ssr", output_num=4)


if __name__ == "__main__":
    main()
