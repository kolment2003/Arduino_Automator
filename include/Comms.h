/*
  Comms.h - Library for handling general communications
*/

#ifndef Comms_h
#define Comms_h

#include "Arduino.h"
#include <Automation.h>
#include <WiFiNINA.h>
#include <WiFiUdp.h>
#include <CRC8.h>

enum Interface {SERIAL_COM, WIFI_COM};
// serial com consts
const byte max_data_length = 32;
const byte max_date_length = 12;
// wifi com consts
const byte max_packet_buffer_length = 256;
const byte ssid_length = 8;
const byte pass_length = 11;
const byte output_buffer_length = 10;

class Comms
{
  public:
    Comms(Automation *);
    // serial com functions
    void config_uart(bool);
    void get_serial_packet();
    // wifi com functions
    void handle_connection();
    void get_udp_packet();
    void config_all_expected_outputs();
    // helper functions
    static bool char_to_bool(char);
    static int char_to_int(char);
  private:
    Automation *_ptr_uc_resources;
    // CRC variables
    CRC8 _crc;
    bool _rx_crc_enabled = true;
    byte _rx_crc;
    byte _rx_calculated_crc;
    bool _tx_crc_enabled = true;
    byte _tx_calculated_crc;
    // serial com variables
    char _serial_command_buffer[max_data_length];
    bool _valid_serial_cmd = false;
    // wifi com variables
    char _packet_buffer[max_packet_buffer_length];
    char _udp_command_buffer[max_data_length];
    byte _output_buffer[output_buffer_length] = {0};
    bool _valid_udp_cmd = false;
    char _ssid[ssid_length] = "HomeNet";    
    char _pass[pass_length] = "123456";
    unsigned int _localPort = 2390;

    int _status = WL_IDLE_STATUS;
    bool _connecting_in_progress = false;
    IPAddress _ip;
    WiFiUDP *_ptr_udp;

    void config_expected_output(int);
    // Comms functions
    void send_ack(Interface);
    void send_nak(Interface);
    void send_byte(Interface, byte);
    void reply_nak(Interface);
    void reply_udp_byte(byte);
    void prep_crc_generator();
    void calc_reply_crc(Interface);
    void send_packet(Interface, byte);
    // general functions
    void parse_time(char *, char *);
    void parse_date(char *, char *);
    void set_cmd_validity(Interface, bool);
    // packet parsing functions
    void parse_packet(byte, char *,Interface);
    void parse_rtc_time_packet(byte, char *, Interface);
    void parse_alarm_packet(byte, char *, Interface);
    void parse_temperature_packet(char *, Interface);
    void parse_pushbutton_state_packet(char *, Interface);
    void parse_pushbutton_pulse_cnt_packet(char *, Interface);
    void parse_ssr_packet(char *, Interface);
    void parse_opto_packet(char *, Interface);
    void parse_opto_pulse_cnt_packet(char *, Interface);
    void parse_probe_packet(char *, Interface);
    void parse_network_info_packet(char *, Interface);
};

#endif