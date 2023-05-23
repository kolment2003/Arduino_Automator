# general libraries
import logging as logger
import json
import struct
from datetime import datetime
from enum import Enum
from serial import Serial, SerialException
import socket
from retry import retry
from crc8 import crc8
# custom libraries
import serial.tools.list_ports as port_list
from tools.OSDetection import OSDetection, OSType

InterfaceType = Enum('InterfaceType', 'Serial Wifi')


class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class UnexpectedIONum(Error):
    """unexpected IO # specified"""
    pass


class UnexpectedIOType(Error):
    """unexpected IO Type specified"""
    pass


class InvalidPulseAmount(Error):
    """invalid amount of pulses specified"""
    pass


class UnexpectedWifiStatus(Error):
    """unexpected wifi status code(int)"""
    pass


class FailedFSM(Error):
    """Comms finite state machine failure"""
    pass


class NakReceived(Error):
    """NAK received instead of ACK"""
    pass


class UnexpectedByte(Error):
    """unexpected byte received"""
    pass


class Settings:
    """
    Class to get settings from json file
    """

    @staticmethod
    def get_json():
        """retrieve settings from json file"""
        json_file_name = "settings.json"
        with open(json_file_name) as f:
            json_settings = json.load(f)
        return json_settings

    @staticmethod
    def write_current_settings(current_settings):
        """
        store current settings to json file
        :param current_settings: dict - current settings to save to file
        """
        with open('current_settings.json', 'w') as fp:
            json.dump(current_settings, fp)

    @staticmethod
    def get_full_ip_address(json_settings):
        """
        generates full ip address as a string
        :param json_settings: dict - settings
        """
        return f"{json_settings['comm_settings']['arduino_ip_1']}.{json_settings['comm_settings']['arduino_ip_2']}." \
               f"{json_settings['comm_settings']['arduino_ip_3']}.{json_settings['comm_settings']['arduino_ip_4']}"


class Interface:
    """
    Class to help abstract which interface (serial com or wifi udp) is being used
    """
    detected_os = OSDetection.get_os_type()

    def __init__(self, interface_type=None, ip_address=None, udp_port=None, baudrate=None, timeout=4,
                 windows_port_name=None, linux_port_name=None, osx_port_name=None):
        """
        :param interface_type: InterfaceType (Enum) - interface used to communicate with arduino
        :param ip_address: str - arduino ip address
        :param udp_port: inr - port for udp socket
        :param baudrate: int - serial comm baud rate
        :param timeout: int - timeout used on interface (sec)
        :param windows_port_name: str - name of windows serial port
        :param osx_port_name: str - name of osx serial port
        :param linux_port_name: str - name of linux serial port
        """
        self.json_setings = Settings.get_json()
        if interface_type:
            self.interface_type = interface_type
        else:
            self.interface_type = self.get_settings_interface()
        detected_os = OSDetection.get_os_type()
        # wifi only variables
        if ip_address:
            self.arduino_ip = ip_address
        else:
            self.arduino_ip = Settings.get_full_ip_address(self.json_setings)
        if udp_port:
            self.udp_port = udp_port
        else:
            self.udp_port = self.json_setings["comm_settings"]["udp_port"]
        if baudrate:
            self.baudrate = baudrate
        else:
            self.baudrate = self.json_setings["comm_settings"]["baud_rate"]
        if timeout:
            self.timeout = timeout
        else:
            self.timeout = self.json_setings["comm_settings"]["timeout"]
        if windows_port_name:
            self.windows_port_name = windows_port_name
        else:
            self.windows_port_name = self.json_setings["comm_settings"]["windows_port_name"]
        if osx_port_name:
            self.osx_port_name = osx_port_name
        else:
            self.osx_port_name = self.json_setings["comm_settings"]["osx_port_name"]
        if linux_port_name:
            self.linux_port_name = linux_port_name
        else:
            self.linux_port_name = self.json_setings["comm_settings"]["linux_port_name"]
        if detected_os == OSType.windows:
            self.port_name = self.windows_port_name
        elif detected_os == OSType.linux:
            self.port_name = self.linux_port_name
        elif detected_os == OSType.osx:
            self.port_name = self.osx_port_name
        elif detected_os == OSType.unrecognized:
            self.port_name = None
            raise RuntimeError(f"OS unrecognized")

        logger.warning(f"interface: {self.interface_type}")
        logger.warning(f"arduino_ip: {self.arduino_ip}")

        # open interface
        if self.interface_type == InterfaceType.Serial:
            self.interface = Serial(port=self.port_name, baudrate=self.baudrate, timeout=self.timeout)
        elif self.interface_type == InterfaceType.Wifi:
            self.interface = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP
            self.interface.settimeout(self.timeout)
        else:
            raise RuntimeError(f"Unknown Interface Type: {self.interface_type}")

    def close(self):
        """
        Called are the end of each communications sessions
        :caveats: only closes serial com, wifi_socket should already be closed
        """
        if self.interface_type == InterfaceType.Serial:
            self.interface.close()

    def open_udp_socket(self):
        self.interface = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP
        self.interface.settimeout(self.timeout)

    def close_udp_socket(self):
        self.interface.close()

    def write(self, byte_cmd):
        """
        write a byte via interface (serial or wifi udp)
        :param byte_cmd: bytes object - raw string of bytes to send to uC
        """
        if self.interface_type == InterfaceType.Serial:
            self.interface.write(byte_cmd)
        elif self.interface_type == InterfaceType.Wifi:
            self.interface.sendto(byte_cmd, (self.arduino_ip, self.udp_port))
        else:
            raise RuntimeError(f"Unknown Interface Type: {self.interface_type}")

    def read(self):
        """
        read a byte from interface (serial or wifi udp)
        """
        if self.interface_type == InterfaceType.Serial:
            return self.interface.read()
        elif self.interface_type == InterfaceType.Wifi:
            return self.interface.recv(1024)
        else:
            raise RuntimeError(f"Unknown Interface Type: {self.interface_type}")

    def get_settings_interface(self):
        """
        gets interface type specified in settings json  file
        :return InterfaceType: Enum
        """
        literal_interface_type = self.json_setings["comm_settings"]["default_interface_type"]
        if literal_interface_type == "Serial":
            return InterfaceType.Serial
        elif literal_interface_type == "Wifi":
            return InterfaceType.Wifi
        else:
            raise RuntimeError(f"Unknown Interface Type: {literal_interface_type}")


class ComPorts:
    """
    Class of static methods to interact with Computer

    Other Com port related notes:
    list tty devices: ls /dev/tty.*
    i.e. osx:
    /dev/tty.Bluetooth-Incoming-Port
    /dev/tty.usbmodem142402

    list cu  devices: ls /dev/cu.*
    i.e. osx:
    /dev/cu.Bluetooth-Incoming-Port	/dev/cu.usbmodem142402

    or list all devices: ls /dev/{tty,cu}.*
    i.e. osx:

    /dev/cu.Bluetooth-Incoming-Port		/dev/tty.Bluetooth-Incoming-Port
    /dev/cu.usbmodem142402			/dev/tty.usbmodem142402

    vs code terminal used: Miniterm on /dev/cu.usbmodem142402  9600,8,N,1

    ports listed by python serial library:
    Port #: 0 -> /dev/cu.Bluetooth-Incoming-Port - n/a
    Port #: 1 -> /dev/cu.usbmodem142402 - mEDBG CMSIS-DAP
    """

    @staticmethod
    def get_com_ports():
        """
        list serial port available on system
        :return: ports - list of ports found
        """
        ports = list(port_list.comports())
        logger.info(f"list port names Qty: {len(ports)}")
        for cnt, p in enumerate(ports):
            print(f"Port #: {cnt} -> {p}")
            logger.info(f"Port #: {cnt} -> {p}")


class Arduino:
    """
    Class of static methods to interact with arduino uC
    """
    detected_os = OSDetection.get_os_type()
    tx_crc8_enabled = False
    rx_crc8_enabled = False

    @staticmethod
    def config_io_state(com, output_type="ssr", output_num=1, output_state=True):
        """
        configures GPIO on arduino uC and verifies that it was correctly set

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :param output_type: string - describes type of output (ssr or opto)
        :param output_num: int - which output to set [1-4]
        :param output_state: bool - what state to set output too (True = ON, False = OFF)
        :caveats: asserts set state, once set
        """
        set_cmd_fsm = SetCmdFSM(com,
                                GenCmd.set_io_state(output_type,
                                                    output_num,
                                                    output_state,
                                                    append_crc8=Arduino.tx_crc8_enabled),
                                GenCmd.get_io_state(output_type, output_num, append_crc8=Arduino.tx_crc8_enabled),
                                [RX.bool],
                                Arduino.assert_io_state,
                                output_state,
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        io_state = RX.get_bool_value(set_cmd_fsm)
        logger.info(f"CONFIG:{output_type}|{output_num}->State: {io_state}")

    @staticmethod
    def get_io_state(com, output_type="ssr", io_num=1):
        """
        reads GPIO on arduino uC

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :param output_type: string - describes type of output (ssr or opto)
        :param io_num: int - which io to get [1-4]
        :return io_state: bool - GPIO IO state on uC
        """
        get_cmd_fsm = GetCmdFSM(com,
                                GenCmd.get_io_state(output_type, io_num, append_crc8=Arduino.tx_crc8_enabled),
                                [RX.bool],
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        io_state = RX.get_bool_value(get_cmd_fsm)
        logger.info(f"GET:{output_type}|{io_num}->State: {io_state}")
        return io_state

    @staticmethod
    def assert_io_state(expected_io_state, rx_data_list):
        """
        :param expected_io_state: bool - expected state of configured IO
        :param rx_data_list: list - chunks of data returned from SET FSM
        :return: bool - True if IO set correctly
        :caveats: expect bool data @ position 0 of rx_data_list
        """
        if rx_data_list[0] == expected_io_state:
            return True
        else:
            logger.info(f"Failed to set IO -> expected state: {expected_io_state} != set state: {rx_data_list[0]}")
            return False

    @staticmethod
    def get_input_pulse_count(com, input_num=1):
        """
        reads opto pulse count associated to output_num

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :param input_num: int - which io to get [1-2]
        :return input_pulse_count: int - number of times input was pulsed
        """
        get_cmd_fsm = GetCmdFSM(com,
                                GenCmd.get_input_pulse_count(input_num, append_crc8=Arduino.tx_crc8_enabled),
                                [RX.int],
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        input_pulse_count = RX.get_int_value(get_cmd_fsm)
        logger.info(f"GET: INPUT PULSE COUNT: {input_pulse_count}")
        return input_pulse_count

    @staticmethod
    def config_rtc_time(com, dt_obj=None):
        """
        configures rtc time on arduino uC and verifies that time was set correctly

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :param dt_obj: date time object - used to generate time portion of RTC configuration
        :caveats: asserts time, once set. 5 second tolerance when comparing time expected/set, raises runTimeError
                  on failure
        """
        if dt_obj is None:
            dt_obj = datetime.now()
        set_cmd_fsm = SetCmdFSM(com,
                                GenCmd.set_date_time(dt_obj=dt_obj, append_crc8=Arduino.tx_crc8_enabled),
                                GenCmd.get_rtc_time(append_crc8=Arduino.tx_crc8_enabled),
                                [RX.int, RX.byte, RX.byte, RX.byte, RX.byte, RX.byte],
                                Arduino.assert_rtc_time,
                                dt_obj,
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        set_dt_obj = RX.get_time(set_cmd_fsm)
        set_epoch = set_dt_obj.timestamp()
        expected_epoch = dt_obj.timestamp()
        logger.info(f"SET RTC Time: Date(Y/M/D): {set_dt_obj.year}/{set_dt_obj.month}/{set_dt_obj.day}"
                    f"RTC Time(H:M:S): {set_dt_obj.hour}:{set_dt_obj.minute}:{set_dt_obj.second}")
        logger.info(f"\tset      rtc time Epoch: {set_epoch}")
        logger.info(f"\texpected rtc time Epoch: {expected_epoch}")

    @staticmethod
    def get_rtc_time(com):
        """
        get rtc time on arduino uC

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :return dt_obj: datetime object: rtc time
        """
        get_cmd_fsm = GetCmdFSM(com,
                                GenCmd.get_rtc_time(append_crc8=Arduino.tx_crc8_enabled),
                                [RX.int, RX.byte, RX.byte, RX.byte, RX.byte, RX.byte],
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        dt_obj = RX.get_time(get_cmd_fsm)
        logger.info(f"GET RTC Time: Date(Y/M/D): {dt_obj.year}/{dt_obj.month}/{dt_obj.day} "
                    f"RTC Time(H:M:S): {dt_obj.hour}:{dt_obj.minute}:{dt_obj.second}")
        epoch = dt_obj.timestamp()
        logger.info(f"Epoch: {epoch}")
        return dt_obj

    @staticmethod
    def assert_rtc_time(expected_dt_obj, rx_data_list):
        """
        :param expected_dt_obj: date time object - expected time
        :param rx_data_list: list - chunks of data returned from SET FSM
        :return: bool - True if time set correctly
        :caveats: expect year/month/date/hour/minute/second @ positions [0-5] of rx_data_list
        """
        year = rx_data_list[0]
        month = rx_data_list[1]
        day = rx_data_list[2]
        hour = rx_data_list[3]
        minute = rx_data_list[4]
        second = rx_data_list[5]
        set_dt_obj = datetime(year, month, day, hour, minute, second)
        set_epoch = set_dt_obj.timestamp()
        expected_epoch = expected_dt_obj.timestamp()
        if abs(set_epoch - expected_epoch) > 5:
            logger.info(f"FAILED SET RTC Time: Date(Y/M/D): {set_dt_obj.year}/{set_dt_obj.month}/{set_dt_obj.day}"
                        f"RTC Time(H:M:S): {set_dt_obj.hour}:{set_dt_obj.minute}:{set_dt_obj.second}")
            logger.info(f"\tset      rtc time Epoch: {set_epoch}")
            logger.info(f"\texpected rtc time Epoch: {expected_epoch}")
            return False
        else:
            return True

    @staticmethod
    def get_system_time(com):
        """
        get system time on arduino uC

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :return dt_obj: datetime object: system rtc
        """
        get_cmd_fsm = GetCmdFSM(com,
                                GenCmd.get_system_time(append_crc8=Arduino.tx_crc8_enabled),
                                [RX.int, RX.byte, RX.byte, RX.byte, RX.byte, RX.byte],
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        dt_obj = RX.get_time(get_cmd_fsm)
        logger.info(f"GET SYSTEM Time: Date(Y/M/D): {dt_obj.year}/{dt_obj.month}/{dt_obj.day} "
                    f"System Time(H:M:S): {dt_obj.hour}:{dt_obj.minute}:{dt_obj.second}")
        epoch = dt_obj.timestamp()
        logger.info(f"Epoch: {epoch}")
        return dt_obj

    @staticmethod
    def get_rtc_config_flag(com):
        """
        reads rtc config flag on arduino uC

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :return rtc_config_flag: bool - rtc config flag
        """
        get_cmd_fsm = GetCmdFSM(com,
                                GenCmd.get_rtc_config_flag(append_crc8=Arduino.tx_crc8_enabled),
                                [RX.bool],
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        rtc_config_flag = RX.get_bool_value(get_cmd_fsm)
        logger.info(f"GET: RTC Config Flag->State: {rtc_config_flag}")
        return rtc_config_flag

    @staticmethod
    def get_rtc_parse_flag(com):
        """
        reads rtc parse flag on arduino uC

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :return rtc_parse_flag: bool - rtc parse flag
        """
        get_cmd_fsm = GetCmdFSM(com,
                                GenCmd.get_rtc_parse_flag(append_crc8=Arduino.tx_crc8_enabled),
                                [RX.bool],
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        rtc_parse_flag = RX.get_bool_value(get_cmd_fsm)
        logger.info(f"GET: RTC Parse Failure Flag->State: {rtc_parse_flag}")
        return rtc_parse_flag

    @staticmethod
    def get_system_time_flag(com):
        """
        reads system time set flag on arduino uC

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :return system_time_flag: bool - system time flag
        """
        get_cmd_fsm = GetCmdFSM(com,
                                GenCmd.get_system_time_flag(append_crc8=Arduino.tx_crc8_enabled),
                                [RX.bool],
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        system_time_flag = RX.get_bool_value(get_cmd_fsm)
        logger.info(f"GET: System Time Flag->State: {system_time_flag}")
        return system_time_flag

    @staticmethod
    def config_output_alarm(com, output_type="ssr", output_num=1, on_off=True, enable=True, dt_obj=None):
        """
        configures output alarm from arduino uC and verifies that time was set correctly

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :param output_type: string - describes type of output (ssr)
        :param output_num: int - which output to set [1-4]
        :param on_off: bool - ON or OFF alarm to config (True = ON, False = OFF)
        :param enable: bool - if True, alarm is enabled for use
        :param dt_obj: date time object - used to generate time portion of alarm configuration

        :caveats: asserts time, once set.5 second tolerance when comparing time expected/set, raises runTimeError
                  on failure + asserts enable flag
        """
        if dt_obj is None:
            dt_obj = datetime.now()
        expected_alarm_dict = {}
        expected_alarm_dict.update({"enable": enable})
        expected_alarm_dict.update({"hour": dt_obj.hour})
        expected_alarm_dict.update({"minute": dt_obj.minute})
        expected_alarm_dict.update({"second": dt_obj.second})
        expected_alarm_dict.update({"dt_obj": dt_obj})
        expected_epoch = dt_obj.timestamp()
        set_cmd_fsm = SetCmdFSM(com,
                                GenCmd.set_output_alarm(output_type=output_type,
                                                        output_num=output_num,
                                                        on_off=on_off,
                                                        enable=enable,
                                                        dt_obj=dt_obj,
                                                        append_crc8=Arduino.tx_crc8_enabled),
                                GenCmd.get_output_alarm(output_type=output_type,
                                                        output_num=output_num,
                                                        on_off=on_off,
                                                        append_crc8=Arduino.tx_crc8_enabled),
                                [RX.bool, RX.byte, RX.byte, RX.byte],
                                Arduino.assert_output_alarm,
                                expected_alarm_dict,
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        set_alarm_dict = RX.get_output_alarm(set_cmd_fsm)
        set_epoch = set_alarm_dict['dt_obj'].timestamp()
        logger.info(
            f"SET output Alarm:<type>{output_type}|{output_num}|Fct: {on_off}|Enable: {set_alarm_dict['enable']}")
        logger.info(
            f"SET      Time(H:M:S): {set_alarm_dict['hour']}:{set_alarm_dict['minute']}:{set_alarm_dict['second']}")
        logger.info(
            f"Expected Time(H:M:S): {expected_alarm_dict['hour']}:{expected_alarm_dict['minute']}"
            f":{expected_alarm_dict['second']}")
        logger.info(f"\tSET      time Epoch: {set_epoch}")
        logger.info(f"\tExpected time Epoch: {expected_epoch}")

    @staticmethod
    def get_output_alarm(com, output_type="ssr", output_num=1, on_off=True, ):
        """
        reads output alarm from arduino uC

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :param output_type: string - describes type of output (ssr)
        :param output_num: int - which output to get [1-4]
        :param on_off: bool - ON or OFF alarm to config (True = ON, False = OFF)
        :return alarm_dict: dict - output alarm values (keys = enable, hour, minute, second)
        """
        get_cmd_fsm = GetCmdFSM(com,
                                GenCmd.get_output_alarm(output_type=output_type,
                                                        output_num=output_num,
                                                        on_off=on_off,
                                                        append_crc8=Arduino.tx_crc8_enabled),
                                [RX.bool, RX.byte, RX.byte, RX.byte],
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        alarm_dict = RX.get_output_alarm(get_cmd_fsm)
        get_epoch = alarm_dict['dt_obj'].timestamp()
        logger.info(f"GET output Alarm:<type>{output_type}|{output_num}|Fct: {on_off}")
        logger.info(f"Enable: {alarm_dict['enable']}")
        logger.info(f"GET Time(H:M:S): {alarm_dict['hour']}:{alarm_dict['minute']}:{alarm_dict['second']}")
        logger.info(f"GET time Epoch: {get_epoch}")
        return alarm_dict

    @staticmethod
    def assert_output_alarm(expected_alarm_dict, rx_data_list):
        """
        :param expected_alarm_dict: dict - expected enable flag + time[H:M:S]
        :param rx_data_list: list - chunks of data returned from SET FSM
        :return: bool - True if enable & timeset correctly
        :caveats: expect enable flag/hour/minute/second @ positions [0-3] of rx_data_list
        """
        set_alarm_dict = {}
        set_alarm_dict.update({"enable": rx_data_list[0]})
        set_alarm_dict.update({"hour": rx_data_list[1]})
        set_alarm_dict.update({"minute": rx_data_list[2]})
        set_alarm_dict.update({"second": rx_data_list[3]})
        set_dt_obj = datetime(year=1971,
                              month=1,
                              day=1,
                              hour=set_alarm_dict['hour'],
                              minute=set_alarm_dict['minute'],
                              second=set_alarm_dict['second'])
        set_alarm_dict.update({"dt_obj": set_dt_obj})
        set_epoch = set_dt_obj.timestamp()
        expected_epoch = expected_alarm_dict['dt_obj'].timestamp()
        if abs(set_epoch - expected_epoch) > 5:
            logger.info(f"Failed SET ALARM Time(H:M:S): {set_dt_obj.hour}:{set_dt_obj.minute}:{set_dt_obj.second}")
            logger.info(f"\tset      time Epoch: {set_epoch}")
            logger.info(f"\texpected time Epoch: {expected_epoch}")
            return False
        else:
            if set_alarm_dict['enable'] == expected_alarm_dict['enable']:
                return True
            else:
                logger.info(f"Failed SET ALARM Enable-> expected state: {expected_alarm_dict['enable']} !="
                            f"set state: {set_alarm_dict['enable']}")
                return False

    @staticmethod
    def config_output_timer(com, output_num=1, value=1, cycle_duration=True, enable=True):
        """
        configures output timer from arduino uC and verifies that setting was set correctly

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :param output_num: int - which output to set [1-4]
        :param value: int - # of cycles per day [1-48] or cycle duration in minutes [1-15]
        :param cycle_duration: bool - cycle # of duration timer to config (True = cycle, False = duration)
        :param enable: bool - if True, timer is enabled for use
        :caveats: asserts time, once set.5 second tolerance when comparing time expected/set, raises runTimeError
                  on failure + asserts enable flag
        """
        if cycle_duration:
            dt_obj = GenCmd.generate_cycles_per_day(value)
        else:
            dt_obj = GenCmd.generate_cycle_duration(value)
        expected_alarm_dict = {}
        expected_alarm_dict.update({"enable": enable})
        expected_alarm_dict.update({"hour": dt_obj.hour})
        expected_alarm_dict.update({"minute": dt_obj.minute})
        expected_alarm_dict.update({"second": dt_obj.second})
        expected_alarm_dict.update({"dt_obj": dt_obj})
        expected_epoch = dt_obj.timestamp()
        set_cmd_fsm = SetCmdFSM(com,
                                GenCmd.set_output_timer(output_num=output_num,
                                                        value=value,
                                                        cycle_duration=cycle_duration,
                                                        enable=enable,
                                                        append_crc8=Arduino.tx_crc8_enabled),
                                GenCmd.get_output_alarm(output_type="ssr",
                                                        output_num=output_num,
                                                        on_off=cycle_duration,
                                                        append_crc8=Arduino.tx_crc8_enabled),
                                [RX.bool, RX.byte, RX.byte, RX.byte],
                                Arduino.assert_output_alarm,
                                expected_alarm_dict,
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        set_alarm_dict = RX.get_output_alarm(set_cmd_fsm)
        set_epoch = set_alarm_dict['dt_obj'].timestamp()
        logger.info(
            f"SET output timer:<type>ssr|{output_num}|Fct: {cycle_duration}|Cycle_Duration: {set_alarm_dict['enable']}")
        logger.info(
            f"SET      Time(H:M:S): {set_alarm_dict['hour']}:{set_alarm_dict['minute']}:{set_alarm_dict['second']}")
        logger.info(
            f"Expected Time(H:M:S): {expected_alarm_dict['hour']}:{expected_alarm_dict['minute']}"
            f":{expected_alarm_dict['second']}")
        logger.info(f"\tSET      time Epoch: {set_epoch}")
        logger.info(f"\tExpected time Epoch: {expected_epoch}")

    @staticmethod
    def config_alarm_mode(com, output_num=1, mode=True):
        """
        configures io alarm mode on arduino uC and verifies that it was correctly set

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :param output_num: int - which output to set [1-4]
        :param mode: bool - what mode to set output too (True = ON_OFF, False = )
        :caveats: asserts set mode, once set
        """
        set_cmd_fsm = SetCmdFSM(com,
                                GenCmd.set_output_alarm_mode(output_num=output_num,
                                                             mode=mode,
                                                             append_crc8=Arduino.tx_crc8_enabled),
                                GenCmd.get_output_alarm_mode(output_num, append_crc8=Arduino.tx_crc8_enabled),
                                [RX.bool],
                                Arduino.assert_alarm_mode,
                                mode,
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        set_mode = RX.get_bool_value(set_cmd_fsm)
        logger.info(f"CONFIG:ssr|{output_num}->Mode: {set_mode}")

    @staticmethod
    def get_alarm_mode(com, output_num=1):
        """
        reads GPIO alarm mode arduino uC

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :param output_num: int - which output to get [1-4]
        :return set_mode: bool - True = ON_OFF, False = CYCLE
        """
        get_cmd_fsm = GetCmdFSM(com,
                                GenCmd.get_output_alarm_mode(output_num, append_crc8=Arduino.tx_crc8_enabled),
                                [RX.bool],
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        set_mode = RX.get_bool_value(get_cmd_fsm)
        logger.info(f"GET:ssr|{output_num}->Mode: {set_mode}")
        return set_mode

    @staticmethod
    def assert_alarm_mode(expected_mode, rx_data_list):
        """
        :param expected_mode: bool - expected mode (True = ON_OFF, False = CYCLE)
        :param rx_data_list: list - chunks of data returned from SET FSM
        :return: bool - True if mode set correctly
        :caveats: expect bool data @ position 0 of rx_data_list
        """
        if rx_data_list[0] == expected_mode:
            return True
        else:
            logger.info(f"Failed to set alarm mode -> expected state: {expected_mode} != set mode: {rx_data_list[0]}")
            return False

    @staticmethod
    def config_master_alarm_enable(com, master_alarm_enable=True):
        """
        configures master alarm enable arduino uC and verifies that it was correctly set

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :param master_alarm_enable: bool - if True, master alarm enable is set
        :caveats: asserts state, once set
        """
        set_cmd_fsm = SetCmdFSM(com,
                                GenCmd.set_master_alarm_enable(master_alarm_enable,
                                                               append_crc8=Arduino.tx_crc8_enabled),
                                GenCmd.get_master_alarm_enable(append_crc8=Arduino.tx_crc8_enabled),
                                [RX.bool],
                                Arduino.assert_master_alarm_enable_state,
                                master_alarm_enable,
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        set_master_alarm_enable_state = RX.get_bool_value(set_cmd_fsm)
        logger.info(f"CONFIG Master Alarm:->State: {set_master_alarm_enable_state}")

    @staticmethod
    def get_master_alarm_enable(com):
        """
        reads master alarm enable on arduino uC

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :return master_alarm_enable - bool - master alarm enable flag
        """
        get_cmd_fsm = GetCmdFSM(com,
                                GenCmd.get_master_alarm_enable(append_crc8=Arduino.tx_crc8_enabled),
                                [RX.bool],
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        master_alarm_enable = RX.get_bool_value(get_cmd_fsm)
        logger.info(f"GET: Master Alarm->State: {master_alarm_enable}")
        return master_alarm_enable

    @staticmethod
    def assert_master_alarm_enable_state(expected_master_alarm_enable_state, rx_data_list):
        """
        :param expected_master_alarm_enable_state: bool - expected state of configured master alarm enable
        :param rx_data_list: list - chunks of data returned from SET FSM
        :return: bool - True if master alarm enable set correctly
        :caveats: expect bool data @ position 0 of rx_data_list
        """
        if rx_data_list[0] == expected_master_alarm_enable_state:
            return True
        else:
            logger.info(
                f"Failed to set master alarm enable -> expected state: {expected_master_alarm_enable_state} "
                f"!= set state: {rx_data_list[0]}")
            return False

    @staticmethod
    def clear_eeprom(com):
        """
        clears eeprom on arduino uC

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :caveats: asserts clear eeprom counter, once cleared
        """
        clear_eeprom_count = Arduino.get_clear_eeprom_count(com)
        set_cmd_fsm = SetCmdFSM(com,
                                GenCmd.set_clear_eeprom(append_crc8=Arduino.tx_crc8_enabled),
                                GenCmd.get_clear_eeprom_count(append_crc8=Arduino.tx_crc8_enabled),
                                [RX.int],
                                Arduino.assert_clear_eeprom_count,
                                clear_eeprom_count + 1,
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        updated_clear_eeprom_count = RX.get_int_value(set_cmd_fsm)
        logger.info(f"Cleared EEPROM-->Count:{updated_clear_eeprom_count}")
        return {"updated_clear_eeprom_count": updated_clear_eeprom_count}

    @staticmethod
    def get_clear_eeprom_count(com):
        """
        reads clear eeprom count on arduino uC

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :return clear_eeprom_count: int - number of times eeprom was cleared since startup
        """
        get_cmd_fsm = GetCmdFSM(com,
                                GenCmd.get_clear_eeprom_count(append_crc8=Arduino.tx_crc8_enabled),
                                [RX.int],
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        clear_eeprom_count = RX.get_int_value(get_cmd_fsm)
        logger.info(f"GET:EEPROM CLEAR COUNT: {clear_eeprom_count}")
        return clear_eeprom_count

    @staticmethod
    def assert_clear_eeprom_count(expected_clear_eeprom_count, rx_data_list):
        """
        :param expected_clear_eeprom_count: int - expected number of times eeprom should be cleared
        :param rx_data_list: list - chunks of data returned from SET FSM
        :return: bool - True if eeprom cleared correctly
        :caveats: expect int data @ position 0 of rx_data_list
        """
        if rx_data_list[0] == expected_clear_eeprom_count:
            return True
        else:
            logger.info(f"Failed to set clear eeprom -> expected count: {expected_clear_eeprom_count} "
                        f"!= current count: {rx_data_list[0]}")
            return False

    @staticmethod
    def pulse_opto_output(com, output_num=1, n=1):
        """
        pulses specific opto output on arduino uC

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :param output_num: int - which output to pulse [1-4]
        :param n: int - number of times to pulse output [1-9]
        :caveats: asserts pulse counter, once pulsed
        """
        opto_pulse_count = Arduino.get_opto_pulse_count(com, output_num)
        set_cmd_fsm = SetCmdFSM(com,
                                GenCmd.pulse_opto_output(output_num, n, append_crc8=Arduino.tx_crc8_enabled),
                                GenCmd.get_opto_pulse_count(output_num, append_crc8=Arduino.tx_crc8_enabled),
                                [RX.int],
                                Arduino.assert_clear_eeprom_count,
                                opto_pulse_count + n,
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        updated_opto_pulse_count = RX.get_int_value(set_cmd_fsm)
        logger.info(f"OPTO:{output_num}-->Pulse Count:{updated_opto_pulse_count}")
        return {"updated_opto_pulse_count": updated_opto_pulse_count}

    @staticmethod
    def get_opto_pulse_count(com, output_num=1):
        """
        reads opto pulse count associated to output_num

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :param output_num: int - which output to get pulse count [1-4]
        :return opto_pulse_count: int - number of times opto output was pulsed
        """
        get_cmd_fsm = GetCmdFSM(com,
                                GenCmd.get_opto_pulse_count(output_num, append_crc8=Arduino.tx_crc8_enabled),
                                [RX.int],
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        opto_pulse_count = RX.get_int_value(get_cmd_fsm)
        logger.info(f"GET: OPTO PULSE COUNT: {opto_pulse_count}")
        return opto_pulse_count

    @staticmethod
    def assert_opto_pulse_count(expected_pulse_count, rx_data_list):
        """
        :param expected_pulse_count: int - expected pulse count
        :param rx_data_list: list - chunks of data returned from SET FSM
        :return: bool - True if IO set correctly
        :caveats: expect int data @ position 0 of rx_data_list
        """
        if rx_data_list[0] == expected_pulse_count:
            return True
        else:
            logger.info(f"Failed to pulse opto output -> expected pulse count: {expected_pulse_count} "
                        f"!= current count: {rx_data_list[0]}")
            return False

    @staticmethod
    def config_expected_io_state(com, output_type="ssr", output_num=1):
        """
        configures expected io state on arduino uC depending on configured alarm

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :param output_type: string - describes type of output (ssr)
        :param output_num: int - which output to set to expected state[1-4]
        :caveats: asserts set expected io counter, once set
        """
        set_expected_io_count = Arduino.get_set_expected_io_count(com)
        set_cmd_fsm = SetCmdFSM(com,
                                GenCmd.set_expected_io_state(output_type=output_type, output_num=output_num,
                                                             append_crc8=Arduino.tx_crc8_enabled),
                                GenCmd.get_set_expected_io_count(append_crc8=Arduino.tx_crc8_enabled),
                                [RX.int],
                                Arduino.assert_set_expected_io_count,
                                set_expected_io_count + 1,
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        updated_set_expected_io_count = RX.get_int_value(set_cmd_fsm)
        logger.info(f"SET EXPECTED IO-->Count:{updated_set_expected_io_count}")

        logger.info(f"CONFIG:{output_type}|{output_num}->Count: {updated_set_expected_io_count}")

    @staticmethod
    def get_set_expected_io_count(com):
        """
        reads set expected io count on arduino uC

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :return set_expected_io_count: int - number of times IOs were set to expected state by associated alarms
        """
        get_cmd_fsm = GetCmdFSM(com,
                                GenCmd.get_set_expected_io_count(append_crc8=Arduino.tx_crc8_enabled),
                                [RX.int],
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        set_expected_io_count = RX.get_int_value(get_cmd_fsm)
        logger.info(f"GET:SET EXPECTED IO COUNT: {set_expected_io_count}")
        return set_expected_io_count

    @staticmethod
    def assert_set_expected_io_count(expected_io_count, rx_data_list):
        """
        :param expected_io_count: int - expected number of times IOs were set to expected state by associated alarms
        :param rx_data_list: list - chunks of data returned from SET FSM
        :return: bool - True if IO set correctly
        :caveats: expect int data @ position 0 of rx_data_list
        """
        if rx_data_list[0] == expected_io_count:
            return True
        else:
            logger.info(f"Failed to set expected io state -> expected count: {expected_io_count} "
                        f"!= current count: {rx_data_list[0]}")
            return False

    @staticmethod
    def get_analog_reading(com, input_num=1):
        """
        reads analog input on arduino uC

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :param input_num: int - which io to get [1-2]
        :return reading_value: float - reading measured on Uc
        """
        get_cmd_fsm = GetCmdFSM(com,
                                GenCmd.get_analog_reading(input_num=input_num, append_crc8=Arduino.tx_crc8_enabled),
                                [RX.float],
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        reading_value = RX.get_float_value(get_cmd_fsm)
        logger.info(f"GET:Analog|{input_num}->Value: {reading_value}")
        return reading_value

    @staticmethod
    def get_number_probes(com):
        """
        reads number of recognized temperature probes on arduino uC

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :return number_probes: int - number of recognized temperature probes
        """
        get_cmd_fsm = GetCmdFSM(com,
                                GenCmd.get_number_probes(append_crc8=Arduino.tx_crc8_enabled),
                                [RX.int],
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        number_probes = RX.get_int_value(get_cmd_fsm)
        logger.info(f"GET: # of Recognized Probes: {number_probes}")
        return number_probes

    @staticmethod
    def get_probe_recognition(com, input_num):
        """
        reads temperature specific probe(1-4) recognition flag on arduino uC

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :param input_num: int - which probe input to get [1-4]
        :return probe_recognition_flag: bool - True -> probe associated to input_num is recognized
        """
        get_cmd_fsm = GetCmdFSM(com,
                                GenCmd.get_probe_recognition(input_num=input_num, append_crc8=Arduino.tx_crc8_enabled),
                                [RX.bool],
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        probe_recognition_flag = RX.get_bool_value(get_cmd_fsm)
        logger.info(f"GET: Probe #:{input_num} Recognition: {probe_recognition_flag}")
        return probe_recognition_flag

    @staticmethod
    def get_probe_reading(com, input_num):
        """
        reads temperature specific probe(1-4) value in celsius on arduino uC

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :param input_num: int - which probe input to get [1-4]
        :return probe_reading: float - reading measured on uC
        """
        get_cmd_fsm = GetCmdFSM(com, GenCmd.get_probe_reading(input_num=input_num, append_crc8=Arduino.tx_crc8_enabled),
                                [RX.float],
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        probe_reading = RX.get_float_value(get_cmd_fsm)
        logger.info(f"GET:Probe #:{input_num} Temperature(C): {probe_reading}")
        return probe_reading

    @staticmethod
    def get_wifi_status(com):
        """
        reads wifi status on arduino uC

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :return wifi_status: dict - wifi status returned from uC (keys = int, def)
        """
        get_cmd_fsm = GetCmdFSM(com,
                                GenCmd.get_wifi_status(append_crc8=Arduino.tx_crc8_enabled),
                                [RX.int],
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        wifi_status_int = RX.get_int_value(get_cmd_fsm)
        wifi_status_def = InterpretOutput.wifi_status_definition(wifi_status_int)
        wifi_status = {"int": wifi_status_int, "def": wifi_status_def}
        logger.info(f"GET:Wifi Status: {wifi_status_int}:{wifi_status_def}")
        return wifi_status

    @staticmethod
    def get_wifi_ip_address(com):
        """
        reads wifi ip address on arduino uC

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :return wifi_ip_bytes: list - 4 x bytes representing wifi ip address
        """
        get_cmd_fsm = GetCmdFSM(com,
                                GenCmd.get_wifi_ip_address(append_crc8=Arduino.tx_crc8_enabled),
                                [RX.byte, RX.byte, RX.byte, RX.byte],
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        wifi_ip_bytes = RX.get_wifi_ip_address(get_cmd_fsm)
        logger.info(f"GET:Wifi IP Address: {wifi_ip_bytes}")
        return wifi_ip_bytes

    @staticmethod
    def get_wifi_rssi(com):
        """
        reads wifi status on arduino uC RSSI (dBm)

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :return rssi_dbm: long - wifi signal strength (dBm) detected by uC
        """
        get_cmd_fsm = GetCmdFSM(com,
                                GenCmd.get_wifi_rssi(append_crc8=Arduino.tx_crc8_enabled),
                                [RX.long],
                                rx_crc8_enabled=Arduino.rx_crc8_enabled)
        rssi_dbm = RX.get_long_value(get_cmd_fsm)
        logger.info(f"GET:Wifi IP RSSI (dBm): {rssi_dbm}")
        return rssi_dbm


class RX:
    """
    Class of static methods to handle received bytes from arduino uC via communication interface
    """
    detected_os = OSDetection.get_os_type()

    @staticmethod
    @retry(tries=10, delay=0)
    def ack(com):
        """
        rx and validates ACK from a command sent to arduino uC

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :caveats: raise error if NAK or anything else is received (could timeout)
        """
        rec_byte = com.read()
        logger.debug(rec_byte)
        logger.debug(int.from_bytes(rec_byte, 'big'))
        if int.from_bytes(rec_byte, 'big') == 6:
            logger.debug("ACK DETECTED")
        elif int.from_bytes(rec_byte, 'big') == 21:
            raise NakReceived("NAK RECEIVED")
        else:
            raise UnexpectedByte(f"received: {rec_byte}")

    @staticmethod
    @retry(tries=10, delay=0)
    def bool(com):
        """
        rx and validates bool value response from a command sent to arduino uC

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :return tuple(bool, byte string) - state of GPIO pin, raw byte
        :caveats: raise error anything else than 1 or 0 is received
        """
        rec_byte = com.read()
        logger.debug(rec_byte)
        int_conversion = int.from_bytes(rec_byte, 'big')
        logger.debug(f"Detected State: {int_conversion}")
        if int_conversion == 1:
            return True, rec_byte
        elif int_conversion == 0:
            return False, rec_byte
        else:
            raise UnexpectedByte(f"received: {rec_byte}")

    @staticmethod
    @retry(tries=10, delay=0)
    def byte(com):
        """
        rx and validates byte value response from a command sent to arduino
        and converts value into an python int data type

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :return tuple(int, byte string) - value of (int)byte sent by arduino, raw bytes
        :caveats: won't raise an error and just interpret whatever value of byte as an int
        """
        rec_byte = com.read()
        logger.debug(rec_byte)
        int_conversion = int.from_bytes(rec_byte, 'big')
        logger.debug(f"(int)Byte: {int_conversion}")
        return int_conversion, rec_byte

    @staticmethod
    def int(com):
        """
        rx and validates int value response from a command sent to arduino

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :return tuple(int, byte string) - value sent by arduino, raw bytes
        :caveats: won't raise an error and just interpret whatever combined value of bytes as an int
        """
        rx_high_byte = com.read()
        logger.debug(f"high byte: {rx_high_byte}")
        rx_low_byte = com.read()
        logger.debug(f"low byte: {rx_low_byte}")
        rx_total_byte = rx_high_byte + rx_low_byte
        logger.debug(f"total byte: {rx_total_byte}")
        int_conversion = int.from_bytes(rx_total_byte, 'big')
        logger.debug(f"(int): {int_conversion}")
        return int_conversion, rx_total_byte

    @staticmethod
    def float(com):
        """
        rx and validates float (4 x bytes) value response from a command sent to arduino

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :return: tuple(float, byte string) - temperature celsius read from probe, raw bytes
        :caveats: won't raise an error and just interpret whatever combined value of bytes as a float
        """
        rec_byte_4 = com.read()
        logger.debug(f"byte 4: {rec_byte_4}")
        rec_byte_3 = com.read()
        logger.debug(f"byte 3: {rec_byte_3}")
        rec_byte_2 = com.read()
        logger.debug(f"byte 2: {rec_byte_2}")
        rec_byte_1 = com.read()
        logger.debug(f"byte 1: {rec_byte_1}")
        rx_total_byte = rec_byte_4 + rec_byte_3 + rec_byte_2 + rec_byte_1
        logger.debug(f"total byte: {rx_total_byte}")
        float_conversion = struct.unpack('>f', rx_total_byte)[0]
        logger.debug(f"(float): {float_conversion}")
        return float_conversion, rx_total_byte

    @staticmethod
    def long(com):
        """
        rx and validates long (4 x bytes) value response from a command sent to arduino

        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :return: tuple(long, byte string) - value returned from arduino uC, raw bytes
        :caveats: won't raise an error and just interpret whatever combined value of bytes as a float
        """
        rec_byte_4 = com.read()
        logger.debug(f"byte 4: {rec_byte_4}")
        rec_byte_3 = com.read()
        logger.debug(f"byte 3: {rec_byte_3}")
        rec_byte_2 = com.read()
        logger.debug(f"byte 2: {rec_byte_2}")
        rec_byte_1 = com.read()
        logger.debug(f"byte 1: {rec_byte_1}")
        rx_total_byte = rec_byte_4 + rec_byte_3 + rec_byte_2 + rec_byte_1
        logger.debug(f"total byte: {rx_total_byte}")
        long_conversion = struct.unpack('>l', rx_total_byte)[0]
        logger.debug(f"(long): {long_conversion}")
        return long_conversion, rx_total_byte

    @staticmethod
    def get_bool_value(fsm):
        """
        runs fsm and parses bool data out of finite state machine

        :param fsm: finite state machine object - either GetCmdFSM or SetCmdFSM
        :return: bool - state of config (or flag)
        """
        fsm.start_fsm()
        if fsm.literal_state == "get_cmd_ok" or fsm.literal_state == "set_cmd_ok":
            return fsm.rx_data_list[0]
        else:
            raise FailedFSM(f"State: {fsm.literal_state}")

    @staticmethod
    def get_int_value(fsm):
        """
        runs fsm and parses int data out of finite state machine

        :param fsm: finite state machine object - either GetCmdFSM or SetCmdFSM
        :return: int - value returned from uC
        """
        fsm.start_fsm()
        if fsm.literal_state == "get_cmd_ok" or fsm.literal_state == "set_cmd_ok":
            return fsm.rx_data_list[0]
        else:
            raise FailedFSM(f"State: {fsm.literal_state}")

    @staticmethod
    def get_float_value(fsm):
        """
        runs fsm and parses float data out of finite state machine

        :param fsm: finite state machine object - either GetCmdFSM or SetCmdFSM
        :return: float - value returned from uC
        """
        fsm.start_fsm()
        if fsm.literal_state == "get_cmd_ok" or fsm.literal_state == "set_cmd_ok":
            return fsm.rx_data_list[0]
        else:
            raise FailedFSM(f"State: {fsm.literal_state}")

    @staticmethod
    def get_long_value(fsm):
        """
        runs fsm and parses long data out of finite state machine

        :param fsm: finite state machine object - either GetCmdFSM or SetCmdFSM
        :return: long - value returned from uC
        """
        fsm.start_fsm()
        if fsm.literal_state == "get_cmd_ok" or fsm.literal_state == "set_cmd_ok":
            return fsm.rx_data_list[0]
        else:
            raise FailedFSM(f"State: {fsm.literal_state}")

    @staticmethod
    def get_wifi_ip_address(fsm):
        """
        runs fsm and parses ip address (4x bytes) data out of finite state machine

        :param fsm: finite state machine object - either GetCmdFSM or SetCmdFSM
        :return: list - 4 x bytes returned from uC representing ip address
        """
        fsm.start_fsm()
        if fsm.literal_state == "get_cmd_ok" or fsm.literal_state == "set_cmd_ok":
            ip_address_bytes = [fsm.rx_data_list[0],
                                fsm.rx_data_list[1],
                                fsm.rx_data_list[2],
                                fsm.rx_data_list[3]]
            return ip_address_bytes
        else:
            raise FailedFSM(f"State: {fsm.literal_state}")

    @staticmethod
    def get_time(fsm):
        """
        runs fsm and parses time data out of finite state machine

        :param fsm: finite state machine object - either GetCmdFSM or SetCmdFSM
        :return: datetime object - parsed time
        """
        fsm.start_fsm()
        if fsm.literal_state == "get_cmd_ok" or fsm.literal_state == "set_cmd_ok":
            year = fsm.rx_data_list[0]
            logger.debug(f"Year: {year}")
            month = fsm.rx_data_list[1]
            logger.debug(f"Month: {month}")
            day = fsm.rx_data_list[2]
            logger.debug(f"Day: {day}")
            hour = fsm.rx_data_list[3]
            logger.debug(f"Hour: {hour}")
            minute = fsm.rx_data_list[4]
            logger.debug(f"Minute: {minute}")
            second = fsm.rx_data_list[5]
            logger.debug(f"Second: {second}")
            return datetime(year, month, day, hour, minute, second)
        else:
            raise FailedFSM(f"State: {fsm.literal_state}")

    @staticmethod
    def get_output_alarm(fsm):
        """
        runs fsm and parses alarm data out of finite state machine

        :param fsm: finite state machine object - either GetCmdFSM or SetCmdFSM
        :return: dict - of alarm values
        """
        fsm.start_fsm()
        if fsm.literal_state == "get_cmd_ok" or fsm.literal_state == "set_cmd_ok":
            alarm_dict = {}
            alarm_dict.update({"enable": fsm.rx_data_list[0]})
            logger.info(f"Enable: {alarm_dict['enable']}")
            alarm_dict.update({"hour": fsm.rx_data_list[1]})
            logger.info(f"Hour: {alarm_dict['hour']}")
            alarm_dict.update({"minute": fsm.rx_data_list[2]})
            logger.info(f"Minute: {alarm_dict['minute']}")
            alarm_dict.update({"second": fsm.rx_data_list[3]})
            logger.info(f"Second: {alarm_dict['second']}")
            dt_obj = datetime(year=1971,
                              month=1,
                              day=1,
                              hour=alarm_dict['hour'],
                              minute=alarm_dict['minute'],
                              second=alarm_dict['second'])
            alarm_dict.update({"dt_obj": dt_obj})
            return alarm_dict
        else:
            raise FailedFSM(f"State: {fsm.literal_state}")


class GetCmdFSM:
    """
    uC communications finite state machine for Get Commands
    """

    def __init__(self, com, byte_cmd, rx_function_list, rx_crc8_enabled=False):
        """
        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :param byte_cmd: byte string - get command used
        :param rx_function_list: list function - list of receiving function used to parse data
        :param rx_crc8_enabled : bool - if true, expects to receive crc byte after data
        """
        self.com = com
        self.byte_cmd = byte_cmd
        self.rx_function_list = rx_function_list
        self.rx_data_list = []
        self.rx_raw = b''
        self.rx_crc = None
        self.rx_calculated_crc = None
        self.rx_crc_is_valid = False
        self.rx_crc8_enabled = rx_crc8_enabled

        self.literal_state = "comms_start"
        self.wait_get_ack_failure_counter = 0
        self.wait_data_failure_counter = 0
        self.wait_failure_limit = 10

    def start_fsm(self):
        # open socket at start of transaction
        if self.com.interface_type == InterfaceType.Wifi:
            self.com.open_udp_socket()
        self.comms_start("start_comms")

    def restart_fsm(self):
        # open socket at restart of transaction
        if self.com.interface_type == InterfaceType.Wifi:
            self.com.open_udp_socket()
        self.wait_get_ack_failure_counter = 0
        self.wait_data_failure_counter = 0
        self.comms_start("start_comms")

    # ===============================================================================
    # State Functions
    # ===============================================================================

    def comms_start(self, transition):
        self.literal_state = "comms_start"
        if transition == 'start_comms':
            self.com.write(self.byte_cmd)
            self.wait_get_ack("tx_get_cmd")

    def wait_get_ack(self, transition):
        self.literal_state = "wait_get_ack"
        if transition == 'tx_get_cmd':
            try:
                RX.ack(self.com)
                self.wait_get_ack_failure_counter = 0
                self.wait_data("ack_rx")
            except (socket.timeout, SerialException):
                logger.debug(f"get ack timeout")
                self.increment_retry_get("nth_timeout_ack_not_rx")
            except NakReceived:
                logger.warning(f"get ack got Nak instead")
                self.comms_failure("nak_rx")
            except UnexpectedByte:
                logger.warning("unexpected byte received")
                self.comms_failure("unexpected_byte_rx")

    def increment_retry_get(self, transition):
        self.literal_state = "increment_retry_get"
        if transition == "nth_timeout_ack_not_rx":
            self.wait_get_ack_failure_counter += 1
            if self.wait_get_ack_failure_counter < self.wait_failure_limit:
                self.com.write(self.byte_cmd)
                self.wait_get_ack("tx_get_cmd")
            else:
                self.comms_failure("retry_get_ack>limit")
        elif transition == "nth_timeout_data_not_rx":
            self.wait_data_failure_counter += 1
            if self.wait_data_failure_counter < self.wait_failure_limit:
                self.com.write(self.byte_cmd)
                self.wait_get_ack("tx_get_cmd")
            else:
                self.comms_failure("retry_get_data>limit")

    def wait_data(self, transition):
        self.literal_state = "wait_data"
        if transition == "ack_rx":
            try:
                # receive values
                for rx_func in self.rx_function_list:
                    rx_tuple = rx_func(self.com)
                    self.rx_data_list.append(rx_tuple[0])
                    self.rx_raw = self.rx_raw + rx_tuple[1]
                # receive CRC
                if self.rx_crc8_enabled:
                    self.rx_crc = RX.byte(self.com)[1]
                    self.rx_calculated_crc = GenCmd.compute_crc8(self.rx_raw)
                    assert self.rx_crc == self.rx_calculated_crc
                    self.rx_crc_is_valid = True
                self.wait_data_failure_counter = 0
                self.get_cmd_ok()
            except (socket.timeout, SerialException):
                logger.debug(f"data timeout")
                self.rx_raw = b''
                self.increment_retry_get("nth_timeout_data_not_rx")
            except UnexpectedByte:
                logger.warning("unexpected byte received")
                self.comms_failure("unexpected_byte_rx")

    def get_cmd_ok(self):
        self.literal_state = "get_cmd_ok"
        # close socket at end of transaction
        if self.com.interface_type == InterfaceType.Wifi:
            self.com.close_udp_socket()

    def comms_failure(self, transition):
        self.literal_state = "comms_failure"
        if transition == "retry_get_ack>limit":
            logger.debug(f"last transition: {transition}")
        elif transition == "retry_get_data>limit":
            logger.debug(f"last transition: {transition}")
        elif transition == "nak_rx":
            logger.debug(f"last transition: {transition}")
        elif transition == "unexpected_byte_rx":
            logger.debug(f"last transition: {transition}")
        # close socket at end of transaction
        if self.com.interface_type == InterfaceType.Wifi:
            self.com.close_udp_socket()


class SetCmdFSM:
    """
    uC communications finite state machine for SET Commands
    """

    def __init__(self, com, set_byte_cmd, get_byte_cmd, rx_function_list, assertion_function, expected_data,
                 rx_crc8_enabled=False):
        """
        :param com: Interface object - communication interface (serial port or wifi udp socket)
        :param set_byte_cmd: byte string - set command used
        :param get_byte_cmd: byte string - get command used
        :param rx_function_list: list function - list of receiving function used to parse data
        :param assertion_function: function - used with expected_data to assert configured resource on uC
        :param expected_data: variable data type - expected value of resource configured on uC
        :param rx_crc8_enabled : bool - if true, expects to receive crc byte after data
        """
        self.com = com
        self.set_byte_cmd = set_byte_cmd
        self.get_byte_cmd = get_byte_cmd
        self.rx_function_list = rx_function_list
        self.rx_data_list = []
        self.rx_raw = b''
        self.rx_crc = None
        self.rx_calculated_crc = None
        self.rx_crc_is_valid = False
        self.rx_crc8_enabled = rx_crc8_enabled
        self.assertion_function = assertion_function
        self.expected_data = expected_data

        self.literal_state = "comms_start"
        self.wait_get_ack_failure_counter = 0
        self.wait_data_failure_counter = 0
        self.wait_verify_get_ack_failure_counter = 0
        self.wait_verify_data_failure_counter = 0
        self.assert_verify_data_failure_counter = 0
        self.wait_failure_limit = 10
        self.wait_verify_failure_limit = 10
        self.assert_verify_data_failure_limit = 10
        logger.warning(f"Set cmd: {set_byte_cmd}")

    def start_fsm(self):
        # open socket at start of transaction
        if self.com.interface_type == InterfaceType.Wifi:
            self.com.open_udp_socket()
        self.comms_start("start_comms")

    def restart_fsm(self):
        # open socket at restart of transaction
        if self.com.interface_type == InterfaceType.Wifi:
            self.com.open_udp_socket()
        self.wait_get_ack_failure_counter = 0
        self.wait_data_failure_counter = 0
        self.wait_verify_get_ack_failure_counter = 0
        self.wait_verify_data_failure_counter = 0
        self.assert_verify_data_failure_counter = 0
        self.comms_start("start_comms")

    # ===============================================================================
    # State Functions
    # ===============================================================================

    def comms_start(self, transition):
        self.literal_state = "comms_start"
        if transition == 'start_comms':
            self.com.write(self.set_byte_cmd)
            self.wait_set_ack("tx_set_cmd")

    def wait_set_ack(self, transition):
        self.literal_state = "wait_set_ack"
        if transition == "tx_set_cmd":
            try:
                RX.ack(self.com)
                self.com.write(self.get_byte_cmd)
                self.wait_get_ack("ack_rx+tx_get_cmd")
            except (socket.timeout, SerialException):
                logger.debug(f"set ack timeout")
                self.com.write(self.get_byte_cmd)
                self.wait_verify_get_ack("ack_not_rx+tx_verify_get_cmd")
            except NakReceived:
                logger.warning(f"get ack got Nak instead")
                self.comms_failure("nak_rx")
            except UnexpectedByte:
                logger.warning("unexpected byte received")
                self.comms_failure("unexpected_byte_rx")
        elif transition == "invalid_assert+tx_set_cmd":
            # 2nd time around because packet lost
            try:
                RX.ack(self.com)
                self.com.write(self.get_byte_cmd)
                self.wait_get_ack("ack_rx+tx_get_cmd")
            except (socket.timeout, SerialException):
                logger.debug(f"set ack timeout")
                self.com.write(self.get_byte_cmd)
                self.wait_verify_get_ack("ack_not_rx+tx_verify_get_cmd")
            except NakReceived:
                logger.warning(f"get ack got Nak instead")
                self.comms_failure("nak_rx")
            except UnexpectedByte:
                logger.warning("unexpected byte received")
                self.comms_failure("unexpected_byte_rx")

    def wait_get_ack(self, transition):
        self.literal_state = "wait_get_ack"
        if transition == 'ack_rx+tx_get_cmd' or transition == 'tx_get_cmd':
            try:
                RX.ack(self.com)
                self.wait_get_ack_failure_counter = 0
                self.wait_data("ack_rx")
            except (socket.timeout, SerialException):
                logger.debug(f"get ack timeout")
                self.increment_retry_get("nth_timeout_ack_not_rx")
            except NakReceived:
                logger.warning(f"get ack got Nak instead")
                self.comms_failure("nak_rx")
            except UnexpectedByte:
                logger.warning("unexpected byte received")
                self.comms_failure("unexpected_byte_rx")

    def wait_verify_get_ack(self, transition):
        self.literal_state = "wait_verify_get_ack"
        if transition == "ack_not_rx+tx_verify_get_cmd" or transition == "tx_verify_get_cmd":
            try:
                RX.ack(self.com)
                self.wait_verify_get_ack_failure_counter = 0
                self.wait_verify_data("ack_rx")
            except (socket.timeout, SerialException):
                logger.debug(f"verify get ack timeout")
                self.increment_retry_verify_get("nth_timeout_ack_not_rx")
            except NakReceived:
                logger.warning(f"get ack got Nak instead")
                self.comms_failure("nak_rx")
            except UnexpectedByte:
                logger.warning("unexpected byte received")
                self.comms_failure("unexpected_byte_rx")

    def increment_retry_get(self, transition):
        self.literal_state = "increment_retry_get"
        if transition == "nth_timeout_ack_not_rx":
            self.wait_get_ack_failure_counter += 1
            if self.wait_get_ack_failure_counter < self.wait_failure_limit:
                self.com.write(self.get_byte_cmd)
                self.wait_get_ack("tx_get_cmd")
            else:
                self.comms_failure("retry_get_ack>limit")
        elif transition == "nth_timeout_data_not_rx":
            self.wait_data_failure_counter += 1
            if self.wait_data_failure_counter < self.wait_failure_limit:
                self.com.write(self.get_byte_cmd)
                self.wait_get_ack("tx_get_cmd")
            else:
                self.comms_failure("retry_get_data>limit")

    def increment_retry_verify_get(self, transition):
        self.literal_state = "increment_retry_verify_get"
        if transition == "nth_timeout_ack_not_rx":
            self.wait_verify_get_ack_failure_counter += 1
            if self.wait_verify_get_ack_failure_counter < self.wait_verify_failure_limit:
                self.com.write(self.get_byte_cmd)
                self.wait_verify_get_ack("tx_verify_get_cmd")
            else:
                self.comms_failure("retry_verify_get_ack>limit")
        elif transition == "nth_timeout_data_not_rx":
            self.wait_verify_data_failure_counter += 1
            if self.wait_verify_data_failure_counter < self.wait_failure_limit:
                self.com.write(self.get_byte_cmd)
                self.wait_verify_get_ack("tx_verify_get_cmd")
            else:
                self.comms_failure("retry_verify_get_data>limit")

    def wait_data(self, transition):
        self.literal_state = "wait_data"
        if transition == "ack_rx":
            try:
                # receive values
                for rx_func in self.rx_function_list:
                    rx_tuple = rx_func(self.com)
                    self.rx_data_list.append(rx_tuple[0])
                    self.rx_raw = self.rx_raw + rx_tuple[1]
                # receive CRC
                if self.rx_crc8_enabled:
                    self.rx_crc = RX.byte(self.com)[1]
                    self.rx_calculated_crc = GenCmd.compute_crc8(self.rx_raw)
                    assert self.rx_crc == self.rx_calculated_crc
                    self.rx_crc_is_valid = True
                self.wait_data_failure_counter = 0
                self.assert_data("data_rx")
            except (socket.timeout, SerialException):
                logger.debug(f"data timeout")
                self.rx_raw = b''
                self.increment_retry_get("nth_timeout_data_not_rx")
            except UnexpectedByte:
                logger.warning("unexpected byte received")
                self.comms_failure("unexpected_byte_rx")

    def wait_verify_data(self, transition):
        self.literal_state = "wait_verify_data"
        if transition == "ack_rx":
            try:
                # receive values
                for rx_func in self.rx_function_list:
                    rx_tuple = rx_func(self.com)
                    self.rx_data_list.append(rx_tuple[0])
                    self.rx_raw = self.rx_raw + rx_tuple[1]
                # receive CRC
                if self.rx_crc8_enabled:
                    self.rx_crc = RX.byte(self.com)[1]
                    self.rx_calculated_crc = GenCmd.compute_crc8(self.rx_raw)
                    assert self.rx_crc == self.rx_calculated_crc
                    self.rx_crc_is_valid = True
                self.wait_verify_data_failure_counter = 0
                self.assert_verify_data("data_rx")
            except (socket.timeout, SerialException):
                logger.debug(f"verfiy data timeout")
                self.rx_raw = b''
                self.increment_retry_verify_get("nth_timeout_data_not_rx")
            except UnexpectedByte:
                logger.warning("unexpected byte received")
                self.comms_failure("unexpected_byte_rx")

    def assert_data(self, transition):
        self.literal_state = "assert_data"
        if transition == "data_rx":
            try:
                assert self.assertion_function(self.expected_data, self.rx_data_list)
                self.set_cmd_ok()
            except Exception as e:
                logger.info(f"assertion failure: e: {e}")
                self.rx_raw = b''
                self.uc_failure()

    def assert_verify_data(self, transition):
        self.literal_state = "assert_verify_data"
        if transition == "data_rx":
            try:
                assert self.assertion_function(self.expected_data, self.rx_data_list)
                self.assert_verify_data_failure_counter = 0
                self.set_cmd_ok()
            except Exception as e:
                logger.info(f"assertion failure: e: {e}")
                self.rx_raw = b''
                self.assert_verify_data_failure_counter += 1
                if self.assert_verify_data_failure_counter < self.assert_verify_data_failure_limit:
                    self.com.write(self.set_byte_cmd)
                    self.wait_set_ack("invalid_assert+tx_set_cmd")
                else:
                    self.comms_failure("retry_verify_assert_data>limit")

    def set_cmd_ok(self):
        self.literal_state = "set_cmd_ok"
        # close socket at end of transaction
        if self.com.interface_type == InterfaceType.Wifi:
            self.com.close_udp_socket()

    def comms_failure(self, transition):
        self.literal_state = "comms_failure"
        if transition == "retry_get_ack>limit":
            logger.info(f"last transition: {transition}")
        elif transition == "retry_get_data>limit":
            logger.info(f"last transition: {transition}")
        if transition == "retry_verify_get_ack>limit":
            logger.info(f"last transition: {transition}")
        elif transition == "retry_verify_get_data>limit":
            logger.info(f"last transition: {transition}")
        elif transition == "retry_verify_assert_data>limit":
            logger.info(f"last transition: {transition}")
        elif transition == "nak_rx":
            logger.debug(f"last transition: {transition}")
        elif transition == "unexpected_byte_rx":
            logger.debug(f"last transition: {transition}")
        # close socket at end of transaction
        if self.com.interface_type == InterfaceType.Wifi:
            self.com.close_udp_socket()

    def uc_failure(self):
        self.literal_state = "uc_failure"
        # close socket at end of transaction
        if self.com.interface_type == InterfaceType.Wifi:
            self.com.close_udp_socket()


class GenCmd:
    """
    Class of static methods to generate byte commands to be send to
    arduino uC via communication interface
    """
    detected_os = OSDetection.get_os_type()

    @staticmethod
    def get_system_time(append_crc8=False):
        """
        generates command to get system time
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        """
        return GenCmd.generate_byte_string_cmd('TGT', append_crc8=append_crc8)

    @staticmethod
    def get_rtc_time(append_crc8=False):
        """
        generates command to get rtc time
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        """
        return GenCmd.generate_byte_string_cmd('TGR', append_crc8=append_crc8)

    @staticmethod
    def get_rtc_config_flag(append_crc8=False):
        """
        generates command to get rtc config flag
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        """
        return GenCmd.generate_byte_string_cmd('TGC', append_crc8=append_crc8)

    @staticmethod
    def get_rtc_parse_flag(append_crc8=False):
        """
        generates command to get rtc parse flag
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        """
        return GenCmd.generate_byte_string_cmd('TGP', append_crc8=append_crc8)

    @staticmethod
    def get_master_alarm_enable(append_crc8=False):
        """
        generates command to get master alarm enable flag
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        """
        return GenCmd.generate_byte_string_cmd('EGM', append_crc8=append_crc8)

    @staticmethod
    def get_system_time_flag(append_crc8=False):
        """
        generates command to get system time flag
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        """
        return GenCmd.generate_byte_string_cmd('TGS', append_crc8=append_crc8)

    @staticmethod
    def get_number_probes(append_crc8=False):
        """
        generates command to get number of temperature probes
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        """
        return GenCmd.generate_byte_string_cmd('KGN', append_crc8=append_crc8)

    @staticmethod
    def get_wifi_status(append_crc8=False):
        """
        generates command to get wifi status
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        """
        return GenCmd.generate_byte_string_cmd('WGS', append_crc8=append_crc8)

    @staticmethod
    def get_wifi_ip_address(append_crc8=False):
        """
        generates command to get wifi status
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        """
        return GenCmd.generate_byte_string_cmd('WGI', append_crc8=append_crc8)

    @staticmethod
    def get_wifi_rssi(append_crc8=False):
        """
        generates command to get wifi rssi (dbm signal strength)
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        """
        return GenCmd.generate_byte_string_cmd('WGT', append_crc8=append_crc8)

    @staticmethod
    def get_clear_eeprom_count(append_crc8=False):
        """
        generates command to get clear eeprom count
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        """
        return GenCmd.generate_byte_string_cmd('EGK', append_crc8=append_crc8)

    @staticmethod
    def set_clear_eeprom(append_crc8=False):
        """
        generates command to set clear eeprom
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        """
        return GenCmd.generate_byte_string_cmd('ESA', append_crc8=append_crc8)

    @staticmethod
    def get_set_expected_io_count(append_crc8=False):
        """
        generates command to get set expectd io count
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        """
        return GenCmd.generate_byte_string_cmd('EGX', append_crc8=append_crc8)

    @staticmethod
    def get_io_state(io_type="ssr", io_num=1, append_crc8=False):
        """
        generates command to get io state in bytes format
        :param io_type: string - describes type of input/output (ssr or opto, push_button)
        :param io_num: int - which io to get [1-4]
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        :caveats: raises runTimeError when incorrect arguments are used
        """
        if io_type == "ssr":
            type_char = "C"
        elif io_type == "opto":
            type_char = "D"
        elif io_type == "push_button":
            type_char = "P"
            if io_num < 1 or io_num > 2:
                raise UnexpectedIONum(f"unexpected input #: {io_num}")
        else:
            raise UnexpectedIOType(f"unexpected output type: {io_type}")
        if io_num < 1 or io_num > 4:
            raise UnexpectedIONum(f"unexpected output #: {io_num}")
        cmd_string = f"{type_char}G{io_num}"
        cmd_byte = GenCmd.generate_byte_string_cmd(cmd_string, append_crc8=append_crc8)
        logger.debug(cmd_byte)
        return cmd_byte

    @staticmethod
    def set_io_state(output_type="ssr", output_num=1, output_state=True, append_crc8=False):
        """
        generates command to set io state in bytes format
        :param output_type: string - describes type of output (ssr or opto)
        :param output_num: int - which output to set [1-4]
        :param output_state: bool - what state to set output too (True = ON, False = OFF)
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        :caveats: raises runTimeError when incorrect arguments are used
        """
        if output_type == "ssr":
            type_char = "C"
        elif output_type == "opto":
            type_char = "D"
        else:
            raise UnexpectedIOType(f"unexpected output type: {output_type}")
        if output_num < 1 or output_num > 4:
            raise UnexpectedIONum(f"unexpected output #: {output_num}")
        if output_state:
            state_char = "1"
        else:
            state_char = "0"
        cmd_string = f"{type_char}S{output_num}{state_char}"
        cmd_byte = GenCmd.generate_byte_string_cmd(cmd_string, append_crc8=append_crc8)
        logger.debug(cmd_byte)
        return cmd_byte

    @staticmethod
    def get_input_pulse_count(input_num=1, append_crc8=False):
        """
        generates command to get push/latch button pulse (falling edge) count in bytes format
        :param input_num: int - which io to get [1-2]
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        :caveats: raises runTimeError when incorrect arguments are used
        """
        if input_num < 1 or input_num > 2:
            raise UnexpectedIONum(f"unexpected input #: {input_num}")
        cmd_string = f"IG{input_num}"
        cmd_byte = GenCmd.generate_byte_string_cmd(cmd_string, append_crc8=append_crc8)
        logger.debug(cmd_byte)
        return cmd_byte

    @staticmethod
    def get_opto_pulse_count(output_num=1, append_crc8=False):
        """
        generates command to get opto pulse count in bytes format
        :param output_num: int - which io to get [1-4]
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        :caveats: raises runTimeError when incorrect arguments are used
        """
        if output_num < 1 or output_num > 4:
            raise UnexpectedIONum(f"unexpected output #: {output_num}")
        cmd_string = f"LG{output_num}"
        cmd_byte = GenCmd.generate_byte_string_cmd(cmd_string, append_crc8=append_crc8)
        logger.debug(cmd_byte)
        return cmd_byte

    @staticmethod
    def pulse_opto_output(output_num=1, n=1, append_crc8=False):
        """
        generates command to pulse opto output (n # of times) in bytes format
        :param output_num: int - which output to set [1-4]
        :param n: int - number of times to pulse output [1-9]
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        :caveats: raises runTimeError when incorrect arguments are used
        """
        if output_num < 1 or output_num > 4:
            raise UnexpectedIONum(f"unexpected output #: {output_num}")
        if n < 1 or n > 9:
            raise InvalidPulseAmount(f"unexpected n #: {n}")
        cmd_string = f"LS{output_num}{n}"
        cmd_byte = GenCmd.generate_byte_string_cmd(cmd_string, append_crc8=append_crc8)
        logger.debug(cmd_byte)
        return cmd_byte

    @staticmethod
    def get_analog_reading(input_num=1, append_crc8=False):
        """
        generates command to get analog reading in bytes format
        :param input_num: int - which input to get [1-2]
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        :caveats: raises runTimeError when incorrect arguments are used
        """
        if input_num < 1 or input_num > 2:
            raise UnexpectedIONum(f"unexpected input #: {input_num}")

        cmd_string = f"AGR{input_num}"
        cmd_byte = GenCmd.generate_byte_string_cmd(cmd_string, append_crc8=append_crc8)
        logger.debug(cmd_byte)
        return cmd_byte

    @staticmethod
    def get_probe_recognition(input_num=1, append_crc8=False):
        """
        generates command to get temperature probe recognition flag in bytes format
        :param input_num: int - which probe input to get [1-4]
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        :caveats: raises runTimeError when incorrect arguments are used
        """
        if input_num < 1 or input_num > 4:
            raise UnexpectedIONum(f"unexpected input #: {input_num}")

        cmd_string = f"KGR{input_num}"
        cmd_byte = GenCmd.generate_byte_string_cmd(cmd_string, append_crc8=append_crc8)
        logger.debug(cmd_byte)
        return cmd_byte

    @staticmethod
    def get_probe_reading(input_num=1, append_crc8=False):
        """
        generates command to get probe temperature reading (celsius) in bytes format
        :param input_num: int - which probe input to get [1-4]
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        :caveats: raises runTimeError when incorrect arguments are used
        """
        if input_num < 1 or input_num > 4:
            raise UnexpectedIONum(f"unexpected input #: {input_num}")

        cmd_string = f"KGC{input_num}"
        cmd_byte = GenCmd.generate_byte_string_cmd(cmd_string, append_crc8=append_crc8)
        logger.debug(cmd_byte)
        return cmd_byte

    @staticmethod
    def set_date_time(dt_obj=None, append_crc8=False):
        """
        generates full data time command in bytes format
        :param dt_obj: date time object - used to generate time portion of RTC configuration
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        :caveats:
            RTC Time Read Output string example: 11:47:42
            RTC Date Output string example: (D/M/Y): 3/3/2021

        """
        if dt_obj is None:
            dt_obj = datetime.now()
        time_string = GenCmd.time_string(dt_obj)
        date_string = GenCmd.date_string(dt_obj)
        full_cmd = f"TS{date_string}|{time_string}"
        full_byte_cmd = GenCmd.generate_byte_string_cmd(full_cmd, append_crc8=append_crc8)
        logger.debug(f"Epoch: {dt_obj.timestamp()}")
        logger.debug(f"Time CMD: {full_byte_cmd}")
        return full_byte_cmd

    @staticmethod
    def set_output_alarm(output_type="ssr", output_num=1, on_off=True, enable=True, dt_obj=None, append_crc8=False):
        """
        generates full command to set output alarm in bytes format
        :param output_type: string - describes type of output (ssr)
        :param output_num: int - which output to set [1-4]
        :param on_off: bool - ON or OFF alarm to config (True = ON, False = OFF)
        :param enable: bool - if True, alarm is enabled for use
        :param dt_obj: date time object - used to generate time portion of alarm configuration
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        :caveats:
            i.e. set dc output 2 on not enabled @ 11:15:03
            [ESD210|11:15:03]

        """
        if output_type == "ssr":
            type_char = "C"
        else:
            raise UnexpectedIOType(f"unexpected output type: {output_type}")
        if output_num < 1 or output_num > 4:
            raise UnexpectedIONum(f"unexpected output #: {output_num}")
        if on_off:
            state_char = "1"
        else:
            state_char = "0"
        if enable:
            enable_char = "1"
        else:
            enable_char = "0"
        if dt_obj is None:
            dt_obj = datetime.now()

        time_string = GenCmd.time_string(dt_obj)
        full_cmd = f"ES{type_char}{output_num}{state_char}{enable_char}|{time_string}"
        full_byte_cmd = GenCmd.generate_byte_string_cmd(full_cmd, append_crc8=append_crc8)
        logger.debug(full_byte_cmd)
        return full_byte_cmd

    @staticmethod
    def get_output_alarm(output_type="ssr", output_num=1, on_off=True, append_crc8=False):
        """
        generates full command to get output alarm in bytes format
        :param output_type: string - describes type of output (ssr)
        :param output_num: int - which output to get [1-4]
        :param on_off: bool - ON or OFF alarm to get (True = ON, False = OFF)
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        :caveats: raises runTimeError when incorrect arguments are used
        """
        if output_type == "ssr":
            type_char = "C"
        else:
            raise UnexpectedIOType(f"unexpected output type: {output_type}")
        if output_num < 1 or output_num > 4:
            raise UnexpectedIONum(f"unexpected output #: {output_num}")
        if on_off:
            state_char = "1"
        else:
            state_char = "0"
        cmd_string = f"EG{type_char}{output_num}{state_char}"
        cmd_byte = GenCmd.generate_byte_string_cmd(cmd_string, append_crc8=append_crc8)
        logger.debug(cmd_byte)
        return cmd_byte

    @staticmethod
    def set_master_alarm_enable(master_alarm_enable=True, append_crc8=False):
        """
        generates full command to set master alarm enable
        :param master_alarm_enable: bool - if True, master alarm enable is set
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        """
        if master_alarm_enable:
            enable_char = "1"
        else:
            enable_char = "0"
        cmd_string = f"ESM{enable_char}"
        cmd_byte = GenCmd.generate_byte_string_cmd(cmd_string, append_crc8=append_crc8)
        logger.debug(cmd_byte)
        return cmd_byte

    @staticmethod
    def set_output_alarm_mode(output_num=1, mode=True, append_crc8=False):
        """
        generates full command to set output alarm mode in bytes format
        :param output_num: int - which output to set [1-4]
        :param mode: bool - alarm mode to config (True = Cycle, False = ON_OFF)
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        :caveats:
            i.e. set ssr output 2 to cycle mode
            [ESO21]
        """
        if output_num < 1 or output_num > 4:
            raise UnexpectedIONum(f"unexpected output #: {output_num}")
        if mode:
            mode_char = "1"
        else:
            mode_char = "0"
        cmd_string = f"ESO{output_num}{mode_char}"
        cmd_byte = GenCmd.generate_byte_string_cmd(cmd_string, append_crc8=append_crc8)
        logger.debug(cmd_byte)
        return cmd_byte

    @staticmethod
    def get_output_alarm_mode(io_num=1, append_crc8=False):
        """
        generates command to get io alarm mode in bytes format
        :param io_num: int - which io to get [1-4]
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        :caveats: raises runTimeError when incorrect arguments are used
        """
        if io_num < 1 or io_num > 4:
            raise UnexpectedIONum(f"unexpected output #: {io_num}")
        cmd_string = f"EGO{io_num}"
        cmd_byte = GenCmd.generate_byte_string_cmd(cmd_string, append_crc8=append_crc8)
        logger.debug(cmd_byte)
        return cmd_byte

    @staticmethod
    def set_output_timer(output_num=1, value=1, cycle_duration=True, enable=True, append_crc8=False):
        """
        generates full command to set output cycle timer in bytes format
        :param output_num: int - which output to set [1-4]
        :param value: int - # of cycles per day [1-48] or cycle duration in minutes [1-15]
        :param cycle_duration: bool - cycle # of duration timer to config (True = cycle, False = duration)
        :param enable: bool - if True, timer is enabled for use
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        :caveats:
            i.e. set ssr output 3 cycle timer to repeat every 2.5 hours
            [EST311|02:30:00]
        """
        if output_num < 1 or output_num > 4:
            raise UnexpectedIONum(f"unexpected output #: {output_num}")
        if cycle_duration:
            cycle_duration_char = "1"
            dt_obj = GenCmd.generate_cycles_per_day(value)
        else:
            cycle_duration_char = "0"
            dt_obj = GenCmd.generate_cycle_duration(value)
        if enable:
            enable_char = "1"
        else:
            enable_char = "0"
        time_string = GenCmd.time_string(dt_obj)
        full_cmd = f"EST{output_num}{cycle_duration_char}{enable_char}|{time_string}"
        full_byte_cmd = GenCmd.generate_byte_string_cmd(full_cmd, append_crc8=append_crc8)
        logger.debug(full_byte_cmd)
        return full_byte_cmd

    @staticmethod
    def set_expected_io_state(output_type="ssr", output_num=1, append_crc8=False):
        """
        generates command to set expected io state depending on configured alarms
        :param output_type: string - describes type of output (ssr)
        :param output_num: int - which output to set [1-4]
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return: byte string
        :caveats: raises runTimeError when incorrect arguments are used
        """
        if output_type == "ssr":
            type_char = "C"
        else:
            raise UnexpectedIOType(f"unexpected output type: {output_type}")
        if output_num < 1 or output_num > 4:
            raise UnexpectedIONum(f"unexpected output #: {output_num}")
        cmd_string = f"ESX{type_char}{output_num}"
        cmd_byte = GenCmd.generate_byte_string_cmd(cmd_string, append_crc8=append_crc8)
        logger.debug(cmd_byte)
        return cmd_byte

    # helper functions
    @staticmethod
    def time_string(dt_obj=None):
        """
        generates time string in proper format to config arduino RTC
        :param dt_obj: date time object - used to generate time portion of RTC configuration
        :caveats: if datetime object not passed in, now() is used
        :return: string
        """
        if dt_obj is None:
            dt_obj = datetime.now()
        time_string = dt_obj.strftime("%H:%M:%S")
        return time_string

    @staticmethod
    def date_string(dt_obj=None):
        """
        generates date string in proper format to config arduino RTC
        :param dt_obj: date time object - used to generate time portion of RTC configuration
        :caveats: if datetime object not passed in, now() is used
        :return:  string
        """
        if dt_obj is None:
            dt_obj = datetime.now()
        date_string = f"{dt_obj.strftime('%b')} {dt_obj.strftime('%d')} {dt_obj.strftime('%Y')}"
        return date_string

    @staticmethod
    def generate_cycles_per_day(cycles_per_day=1):
        """
        generates H:M:S values for given cycles per day
        :param cycles_per_day: int - # of cycles per day i.e. [48,24,12,6,4,3,2,1]
        :return dt_obj: date time object
        :caveats:
            will automatically select proper 30 min increments (8 choices)
                cycles_per_day = [48,24,12,6,4,3,2,1]
                minutes =        [30,60,120,240,360,480,720, 1440]
        """
        if cycles_per_day < 1 or cycles_per_day > 48:
            raise UnexpectedIONum(f"unexpected # cycles per day: {cycles_per_day}")
        cycle_values = [48, 24, 12, 6, 4, 3, 2, 1]
        aligned_cycles_per_day = min(cycle_values, key=lambda x: abs(x - cycles_per_day))
        m, s = divmod(24 / aligned_cycles_per_day * 60 * 60, 60)
        h, m = divmod(m, 60)
        if aligned_cycles_per_day == 1:
            h = 23
            m = 59
            s = 59
        return datetime(1971, 1, 1, int(h), int(m), int(s))

    @staticmethod
    def generate_cycle_duration(cycle_duration=1):
        """
        generates H:M:S values for given cycle duration
        :param cycle_duration: int - duration in minutes cycles per day i.e. [1-15]
        :return dt_obj: date time object
        """
        if cycle_duration < 1 or cycle_duration > 15:
            raise UnexpectedIONum(f"unexpected cycle duration(min): {cycle_duration}")
        return datetime(1971, 1, 1, 0, int(cycle_duration), 0)

    @staticmethod
    def get_cycles_per_day(hms):
        """
        converts hms format into cycles per day
        :param hms: dict - key[hour, minute, second]
        :return: int - cycles per day
        """
        h = hms['hour']
        m = hms['minute']
        s = hms['second']
        return int(86400 / (h * 3600 + m * 60 + s))

    @staticmethod
    def get_cycle_duration_minutes(hms):
        """
        converts hms format into cycle duration in minutes
        :param hms: dict - key[hour, minute, second]
        :return: int - cycles per day
        """
        h = hms['hour']
        m = hms['minute']
        s = hms['second']
        return int((h * 60 + m + s / 60))

    @staticmethod
    def compute_crc8(payload):
        """
        :param payload: byte string - command payload
        :return:  byte string - crc value
        """
        crc_generator = crc8()
        crc_generator.update(payload)
        calculated_crc = crc_generator.digest()
        logger.debug(f"Calculated CRC: {calculated_crc}")
        return calculated_crc

    @staticmethod
    def generate_byte_string_cmd(cmd_string, append_crc8=False):
        """
        :param cmd_string: string - command string
        :param append_crc8: bool - if true, calculate and append crc8 at end of command
        :return:  byte string - with crc appended or not
        """
        if append_crc8:
            calculated_crc = GenCmd.compute_crc8(bytes(cmd_string, "ascii"))
            return b'[' + bytes(cmd_string, "ascii") + calculated_crc + b']'
        else:
            return b'[' + bytes(cmd_string, "ascii") + b']'


class InterpretOutput:
    """
    Class of static methods to interpret output returned by arduino uC
    """

    @staticmethod
    def wifi_status_definition(rx_int):
        """
        generates wifi status string based on int value returned by arduino uC
        :param rx_int: int - int value returned by arduino uC
        :return: string - wifi status description
        """
        if rx_int == 0:
            return "WL_IDLE_STATUS"
        elif rx_int == 250:
            return "WL_NO_MODULE"
        elif rx_int == 1:
            return "WL_NO_SSID_AVAIL"
        elif rx_int == 2:
            return "WL_SCAN_COMPLETED"
        elif rx_int == 3:
            return "WL_CONNECTED"
        elif rx_int == 4:
            return "WL_CONNECT_FAILED"
        elif rx_int == 5:
            return "WL_CONNECTION_LOST"
        elif rx_int == 6:
            return "WL_DISCONNECTED"
        elif rx_int == 7:
            return "WL_AP_LISTENING"
        elif rx_int == 8:
            return "WL_AP_CONNECTED"
        elif rx_int == 9:
            return "WL_AP_FAILED"
        else:
            raise UnexpectedWifiStatus(f"code: {rx_int}")
