/*
  Comms.h - Library for handling general communications
*/

#include "Arduino.h"
#include "Comms.h"

Comms::Comms(Automation *ptr_uc_resources)
{
  _ptr_uc_resources = ptr_uc_resources;
  _ptr_udp = new WiFiUDP();
}

void Comms::config_uart(bool wait_for_serial)
{
  Serial.begin(9600);
  
  if (wait_for_serial){
    while (!Serial);
  }
}

void Comms::handle_connection()
{
  _status = WiFi.status();
  if (_status != WL_NO_MODULE) {
    if (_status != WL_CONNECTED) {
      // Connect to WPA/WPA2 network
      _status = WiFi.begin(_ssid, _pass);
      _status = WiFi.status();
      if (_status == WL_CONNECTED)
      {
        _ip = WiFi.localIP();
        _ptr_udp->begin(_localPort);
      }
    }
  }
}

void Comms::get_serial_packet()
{
  static boolean rec_in_progress = false;
  static byte num_byte_rx = 0;
  char start_marker = '[';
  char end_marker = ']';
  while (Serial.available() > 0 ) {
    char rc = Serial.read();  
    if (rec_in_progress == true) 
    {
      if (rc != end_marker) 
      {
        if (num_byte_rx < max_data_length) { 
          _serial_command_buffer[num_byte_rx] = rc;
          num_byte_rx++;
        }
      }
      else 
      {
        // check for case where crc = end marker ']'
        if (_rx_crc_enabled)
        {
         if (Serial.available()> 0) 
         {
           if (Serial.read() == end_marker)
           {
            if (num_byte_rx < max_data_length)
            {
              _serial_command_buffer[num_byte_rx] = rc;
              num_byte_rx++;
            }
           }
         }
        }
        _serial_command_buffer[num_byte_rx] = '\0'; // terminate the string
        rec_in_progress = false;
        if (_rx_crc_enabled)
          {
            prep_crc_generator();
            for (int i = 0; i < num_byte_rx - 1; i++)
              _crc.add(_serial_command_buffer[i]);
            _rx_calculated_crc = _crc.getCRC();
            _rx_crc = (byte)_serial_command_buffer[num_byte_rx - 1];
            if (_rx_calculated_crc != _rx_crc)
            {
              reply_nak(SERIAL_COM);
            }
            else
              parse_packet(num_byte_rx - 1, _serial_command_buffer, SERIAL_COM);
          }
        else
          parse_packet(num_byte_rx, _serial_command_buffer, SERIAL_COM);
        num_byte_rx = 0;
      }
    }
    else if (rc == start_marker)
      rec_in_progress = true;
  }
}

void Comms::get_udp_packet()
{
  byte num_byte_rx = 0;
  char start_marker = '[';
  char end_marker = ']';
  bool packet_in_progress = false;
  int packetSize = _ptr_udp->parsePacket();
  _status = WiFi.status();
  if (_status == WL_CONNECTED) {
    if (packetSize) {
      IPAddress remoteIp = _ptr_udp->remoteIP();
      // read the packet into packetBufffer
      int len = _ptr_udp->read(_packet_buffer, 255);
      if (len > 0)
        _packet_buffer[len] = 0;
      _valid_udp_cmd = false;
      if (_packet_buffer[0] == start_marker)
      {
        packet_in_progress = true;
        while (num_byte_rx < packetSize && num_byte_rx < max_data_length && packet_in_progress == true)
        {
          if (_packet_buffer[num_byte_rx + 1] != end_marker) 
          {
            if (num_byte_rx < max_data_length) { 
              _udp_command_buffer[num_byte_rx] = _packet_buffer[num_byte_rx + 1];
              num_byte_rx++;
            }
          }
          else 
          {
            // check for case where crc = end marker ']'
            if (_rx_crc_enabled)
            {
              if (num_byte_rx + 1 < packetSize)
              {
                if (_packet_buffer[num_byte_rx + 2] == end_marker)
                {
                  _udp_command_buffer[num_byte_rx] = _packet_buffer[num_byte_rx + 1];
                  num_byte_rx++;
                }
              }
            }
            _udp_command_buffer[num_byte_rx] = '\0'; // terminate the string
            packet_in_progress = false;
            _valid_udp_cmd = true;
          }
        }
        if (_valid_udp_cmd)
        {
          if (_rx_crc_enabled)
          {
            prep_crc_generator();
            for (int i = 0; i < num_byte_rx - 1; i++)
              _crc.add(_udp_command_buffer[i]);
            _rx_calculated_crc = _crc.getCRC();
            _rx_crc = (byte)_udp_command_buffer[num_byte_rx - 1];
            if (_rx_calculated_crc != _rx_crc)
            {
              reply_nak(WIFI_COM);
            }
            else
              parse_packet(num_byte_rx - 1, _udp_command_buffer, WIFI_COM);
          }
          else
            parse_packet(num_byte_rx, _udp_command_buffer, WIFI_COM);
        }
      }
    }
  }
}

void Comms::parse_rtc_time_packet(byte num_byte_rx,char *rx_chars, Interface interface)
{
  char date_chars[max_date_length];
  char time_chars[max_time_length];
  int year;
  switch (rx_chars[1]) {
    case 'G':
      switch (rx_chars[2]) {
        case 'T':
          _ptr_uc_resources->ptr_ds1307->get_system_time();
          year = tmYearToCalendar(_ptr_uc_resources->ptr_ds1307->get_sys_tm().Year);
          _output_buffer[0] =  highByte(year);
          _output_buffer[1] =  lowByte(year);
          _output_buffer[2] =  _ptr_uc_resources->ptr_ds1307->get_sys_tm().Month;
          _output_buffer[3] =  _ptr_uc_resources->ptr_ds1307->get_sys_tm().Day;
          _output_buffer[4] =  _ptr_uc_resources->ptr_ds1307->get_sys_tm().Hour;
          _output_buffer[5] =  _ptr_uc_resources->ptr_ds1307->get_sys_tm().Minute;
          _output_buffer[6] =  _ptr_uc_resources->ptr_ds1307->get_sys_tm().Second;
          send_packet(interface, 7);
          break;
        case 'R':
          if(not _ptr_uc_resources->ptr_ds1307->read_rtc_time())
            reply_nak(interface);
          year = tmYearToCalendar(_ptr_uc_resources->ptr_ds1307->get_rtc_tm().Year);
          _output_buffer[0] =  highByte(year);
          _output_buffer[1] =  lowByte(year);
          _output_buffer[2] =  _ptr_uc_resources->ptr_ds1307->get_rtc_tm().Month;
          _output_buffer[3] =  _ptr_uc_resources->ptr_ds1307->get_rtc_tm().Day;
          _output_buffer[4] =  _ptr_uc_resources->ptr_ds1307->get_rtc_tm().Hour;
          _output_buffer[5] =  _ptr_uc_resources->ptr_ds1307->get_rtc_tm().Minute;
          _output_buffer[6] =  _ptr_uc_resources->ptr_ds1307->get_rtc_tm().Second;
          send_packet(interface, 7);
          break;
        case 'C':
          _output_buffer[0] = _ptr_uc_resources->ptr_ds1307->is_rtc_configured();
          send_packet(interface, 1);
          break;
        case 'P':
          _output_buffer[0] = _ptr_uc_resources->ptr_ds1307->get_parsing_failure();
          send_packet(interface, 1);
          break;
        case 'S':
          _output_buffer[0] = _ptr_uc_resources->ptr_ds1307->is_time_set();
          send_packet(interface, 1);
          break;
        default:
          reply_nak(interface);
      }
      break;
    case 'S':
      if (num_byte_rx == 22)
      {
        parse_date(rx_chars, date_chars);
        parse_time(rx_chars, time_chars);
        if(_ptr_uc_resources->ptr_ds1307->set_rtc_time(date_chars, time_chars))
          send_ack(interface);
        else
          reply_nak(interface);
      }
      else
        reply_nak(interface);
      break;
    default:
      reply_nak(interface);
  }
}

void Comms::parse_alarm_packet(byte num_byte_rx,char *rx_chars, Interface interface)
{
  int io_num;
  bool mode;
  tmElements_t tmp_tm;
  switch (rx_chars[1]) {
    case 'G':
      switch (rx_chars[2]) {
        case 'C':
          io_num = char_to_int(rx_chars[3]);
          if (io_num >= 1 && io_num <= 4)
          {
            tmp_tm = _ptr_uc_resources->ptr_ds1307->get_ssrx_output_alarm_tm(io_num,char_to_bool(rx_chars[4]));
            _output_buffer[0] =  _ptr_uc_resources->ptr_ds1307->get_ssrx_output_alarm_enable(io_num,char_to_bool(rx_chars[4]));
            _output_buffer[1] =  tmp_tm.Hour;
            _output_buffer[2] =  tmp_tm.Minute;
            _output_buffer[3] =  tmp_tm.Second;
            send_packet(interface, 4);
          }
          else
            reply_nak(interface);
          break;
        case 'M':
          _output_buffer[0] = _ptr_uc_resources->ptr_ds1307->get_master_alarm_enable();
          send_packet(interface, 1);
          break;
        case 'K':
          _output_buffer[0] =  highByte(_ptr_uc_resources->ptr_ds1307->get_clear_eeprom_count());
          _output_buffer[1] =  lowByte(_ptr_uc_resources->ptr_ds1307->get_clear_eeprom_count());
          send_packet(interface, 2);
          break;
        case 'X':
          _output_buffer[0] =  highByte(_ptr_uc_resources->ptr_ds1307->get_set_expected_io_count());
          _output_buffer[1] =  lowByte(_ptr_uc_resources->ptr_ds1307->get_set_expected_io_count());
          send_packet(interface, 2);
          break;
        case 'O':
          io_num = char_to_int(rx_chars[3]);
          if (io_num >= 1 && io_num <= 4)
          {
            _output_buffer[0] = _ptr_uc_resources->ptr_ds1307->get_ssrx_alarm_mode(io_num);
            send_packet(interface, 1);
          }
          else
            reply_nak(interface);
          break;
        default:
          reply_nak(interface);
      }
      break;
    case 'S':
      switch (rx_chars[2]) {
        case 'C':
          if (num_byte_rx == 15)
          {
            if(_ptr_uc_resources->ptr_ds1307->config_alarm_or_timer(rx_chars, true))
            {
              io_num = Comms::char_to_int(rx_chars[3]);
              _ptr_uc_resources->ptr_ssr_outputs->set_ssrx_output(io_num, false);
              send_ack(interface);
            }
            else
              reply_nak(interface);
          }
          else
            reply_nak(interface);
          break;
        case 'T':
          if (num_byte_rx == 15)
          {
            if(_ptr_uc_resources->ptr_ds1307->config_alarm_or_timer(rx_chars, false))
            {
              io_num = Comms::char_to_int(rx_chars[3]);
              _ptr_uc_resources->ptr_ssr_outputs->set_ssrx_output(io_num, false);
              send_ack(interface);
            }
            else
              reply_nak(interface);
          }
          else
            reply_nak(interface);
          break;
        case 'M':
          _ptr_uc_resources->ptr_ds1307->set_master_alarm_enable(char_to_bool(rx_chars[3]));
          _ptr_uc_resources->ptr_ds1307->write_master_alarm_enable_eeprom();
          send_ack(interface);
          break;
        case 'A':
          send_ack(interface);
          _ptr_uc_resources->ptr_ds1307->clear_eeprom();
          break;
        case 'X':
          if (rx_chars[3] == 'C')
          {
            io_num = char_to_int(rx_chars[4]);
            if (io_num >= 1 && io_num <= 4)
            {
              _ptr_uc_resources->ptr_ds1307->increment_set_expected_io_count();
              config_expected_output(io_num);
              send_ack(interface);
            }
            else
              reply_nak(interface);
          }
          else
            reply_nak(interface);
          break;
        case 'O': // swap mode, false = on_off, true = cycle
          io_num = char_to_int(rx_chars[3]);
          mode = char_to_bool(rx_chars[4]);
          if (io_num >= 1 && io_num <= 4)
          {
            send_ack(interface);
            _ptr_uc_resources->ptr_ds1307->swap_mode(io_num,mode);
            if (mode)
              config_expected_output(io_num);
            else
              _ptr_uc_resources->ptr_ssr_outputs->set_ssrx_output(io_num, false);
          }
          else
            reply_nak(interface);
          break;  
        default:
          reply_nak(interface);
      }
      break;
    default:
      reply_nak(interface);
  }
}

void Comms::parse_temperature_packet(char *rx_chars, Interface interface)
{
  int io_num;
  byte conversion_bytes[4];
  if (rx_chars[1] == 'G')
  {
    switch (rx_chars[2]) {
      case 'N':
        _output_buffer[0] =  highByte(_ptr_uc_resources->ptr_ds1820b->get_num_rom_recognized());
        _output_buffer[1] =  lowByte(_ptr_uc_resources->ptr_ds1820b->get_num_rom_recognized());
        send_packet(interface, 2);
        break;        
      case 'R':
        io_num = char_to_int(rx_chars[3]);
        if (io_num >= 1 && io_num <= 4)
        {
          _output_buffer[0] =_ptr_uc_resources->ptr_ds1820b->get_rom_recognized(io_num);
          send_packet(interface, 1);
        }
        else
          reply_nak(interface);
        break;
      case 'C':
        io_num = char_to_int(rx_chars[3]);
        if (io_num >= 1 && io_num <= 4)
        {
          *((float *)conversion_bytes) = _ptr_uc_resources->ptr_ds1820b->get_probe_reading_celsius(io_num);
          _output_buffer[0] =  conversion_bytes[3];
          _output_buffer[1] =  conversion_bytes[2];
          _output_buffer[2] =  conversion_bytes[1];
          _output_buffer[3] =  conversion_bytes[0];
          send_packet(interface, 4);
        }
        else
          reply_nak(interface);
        break;
      default:
        reply_nak(interface);
    }
  }
}

void Comms::parse_pushbutton_state_packet(char *rx_chars, Interface interface)
{
  int io_num;
  bool determined_input_state;
  if (rx_chars[1] == 'G')
  {
    io_num = char_to_int(rx_chars[2]);
    if (io_num == 1 || io_num == 2)
    {
      _output_buffer[0] = _ptr_uc_resources->get_input_state(io_num);
      send_packet(interface, 1);
    }
    else
      reply_nak(interface);
  }
  else
    reply_nak(interface);
}

void Comms::parse_pushbutton_pulse_cnt_packet(char *rx_chars, Interface interface)
{
  int io_num = char_to_int(rx_chars[2]);
  if (io_num == 1 || io_num == 2)
  {
    if (rx_chars[1] == 'G')
    {
      int tmp_falling_pulse_cnt = _ptr_uc_resources->get_input_pulse_cnt(io_num);
      _output_buffer[0] =  highByte(tmp_falling_pulse_cnt);
      _output_buffer[1] =  lowByte(tmp_falling_pulse_cnt);
      send_packet(interface, 2);
    }
    else
      reply_nak(interface);
  }
  else
    reply_nak(interface);
}

void Comms::parse_ssr_packet(char *rx_chars, Interface interface)
{
  int io_num = char_to_int(rx_chars[2]);
  if (io_num >= 1 && io_num <= 4)
  {
    switch (rx_chars[1]) {
      case 'G':
        _output_buffer[0] = _ptr_uc_resources->ptr_ssr_outputs->get_ssrx_output(io_num);
        send_packet(interface, 1);
        break;
      case 'S':
        send_ack(interface);
        _ptr_uc_resources->ptr_ssr_outputs->set_ssrx_output(io_num, char_to_bool(rx_chars[3]));
        break;
      default:
        reply_nak(interface);
    }
  }
  else
    reply_nak(interface);
}

void Comms::parse_opto_packet(char *rx_chars, Interface interface)
{
  int io_num = char_to_int(rx_chars[2]);
  if (io_num >= 1 && io_num <= 4)
  {
    switch (rx_chars[1]) {
      case 'G':
        _output_buffer[0] = _ptr_uc_resources->ptr_opto_outputs->get_optox_output(io_num);
        send_packet(interface, 1);
        break;
      case 'S':
        send_ack(interface);
        _ptr_uc_resources->ptr_opto_outputs->set_optox_output(io_num, char_to_bool(rx_chars[3]));
        break;
      default:
        reply_nak(interface);
    }
  }
  else
    reply_nak(interface);
}

void Comms::parse_opto_pulse_cnt_packet(char *rx_chars, Interface interface)
{
  int io_num = char_to_int(rx_chars[2]);
  if (io_num >= 1 && io_num <= 4)
  {
    switch (rx_chars[1]) {
      case 'G':
        _output_buffer[0] =  highByte(_ptr_uc_resources->ptr_opto_outputs->get_optox_pulse_count(io_num));
        _output_buffer[1] =  lowByte(_ptr_uc_resources->ptr_opto_outputs->get_optox_pulse_count(io_num));
        send_packet(interface, 2);
        break;
      case 'S':
        if (char_to_int(rx_chars[3]) >= 1 && char_to_int(rx_chars[3]) <= 9)
        {
          send_ack(interface);
          _ptr_uc_resources->ptr_opto_outputs->increment_optox_pulse_count(io_num, char_to_int(rx_chars[3]));
        }
        else
          reply_nak(interface);
        break;
      default:
        reply_nak(interface);
    }
  }
  else
    reply_nak(interface);
}

void Comms::parse_probe_packet(char *rx_chars, Interface interface)
{
  int io_num;
  bool tmp_flag;
  int tmp_cnt;
  byte conversion_bytes[4];


  switch (rx_chars[1]) {
    case 'G':
      switch (rx_chars[2]) {
        case 'R':
          io_num = char_to_int(rx_chars[3]);
          if (io_num == 1 || io_num == 2)
          {
            *((float *)conversion_bytes) = _ptr_uc_resources->get_probe_value(io_num);
            _output_buffer[0] =  conversion_bytes[3];
            _output_buffer[1] =  conversion_bytes[2];
            _output_buffer[2] =  conversion_bytes[1];
            _output_buffer[3] =  conversion_bytes[0];
            send_packet(interface, 4);
          }
          else
            reply_nak(interface);
          break;

        default:
          reply_nak(interface);
      }
      break;
    default:
      reply_nak(interface);
  }
}

void Comms::parse_network_info_packet(char *rx_chars, Interface interface)
{
  byte conversion_bytes[4];
  if (rx_chars[1] == 'G')
  {
    switch (rx_chars[2]) {
      case 'S':
        _output_buffer[0] =  highByte(_status);
        _output_buffer[1] =  lowByte(_status);
        send_packet(interface, 2);
        break;
      case 'I':
        _output_buffer[0] =  _ip[0];
        _output_buffer[1] =  _ip[1];
        _output_buffer[2] =  _ip[2];
        _output_buffer[3] =  _ip[3];
        send_packet(interface, 4);
        break;
      case 'T':
        *((long *)conversion_bytes) = WiFi.RSSI();
        _output_buffer[0] =  conversion_bytes[3];
        _output_buffer[1] =  conversion_bytes[2];
        _output_buffer[2] =  conversion_bytes[1];
        _output_buffer[3] =  conversion_bytes[0];
        send_packet(interface, 4);
        break;
      default:
        reply_nak(interface);
    }
  }
  else
    reply_nak(interface);
}

void Comms::parse_packet(byte num_byte_rx, char *rx_chars, Interface interface)
{
  set_cmd_validity(interface, true);
  switch (rx_chars[0]) {
    case 'T':
      parse_rtc_time_packet(num_byte_rx, rx_chars,interface);
      break;
    case 'E': 
      parse_alarm_packet(num_byte_rx, rx_chars,interface);
      break;
    case 'K':
      parse_temperature_packet(rx_chars,interface);
      break;
    case 'P':
      parse_pushbutton_state_packet(rx_chars, interface);
      break;
    case 'I':
      parse_pushbutton_pulse_cnt_packet(rx_chars, interface);
      break;
    case 'C':
      parse_ssr_packet(rx_chars, interface);
      break;
    case 'D':
      parse_opto_packet(rx_chars, interface);
      break;
    case 'L':
      parse_opto_pulse_cnt_packet(rx_chars, interface);
      break;
    case 'A':
      parse_probe_packet(rx_chars,interface);
      break;
    case 'W':
      parse_network_info_packet(rx_chars,interface);
      break;
    default:
      reply_nak(interface);
  }
}

void Comms::send_byte(Interface interface, byte tx_byte)
{
  if (interface == SERIAL_COM)
    Serial.write(tx_byte);
  else
    reply_udp_byte(tx_byte);
}

void Comms::reply_udp_byte(byte tx_byte)
{
  // send to the IP address and port that sent us the packet we received
  _ptr_udp->beginPacket(_ptr_udp->remoteIP(), _ptr_udp->remotePort());
  _ptr_udp->write(tx_byte);
  _ptr_udp->endPacket();
}

void Comms::send_ack(Interface interface )
{
  // 6 or 0x6 = ACK byte code
  if (interface == SERIAL_COM)
    Serial.write(0x6);
  else
    reply_udp_byte(0x6);
}

void Comms::reply_nak(Interface interface)
{
  set_cmd_validity(interface, false);
  send_nak(interface);
}

void Comms::send_nak(Interface interface)
{
  // 21 or 0x15 = NAK byte code
  if (interface == SERIAL_COM)
    Serial.write(0x15);  
  else
    reply_udp_byte(0x15);
}

int Comms::char_to_int(char character)
{
  int int_conversion = character - '0';
  return int_conversion;
}

bool Comms::char_to_bool(char character)
{
 int int_conversion = char_to_int(character);
 bool bool_conversion;
 if (int_conversion==0)
   bool_conversion = false;
 else
   bool_conversion = true;
return bool_conversion; 

}

void Comms::parse_time(char *rx_chars, char *time_chars){
  int i;
  // parse time
  for (i = 0; i < max_time_length - 1; ++i)
    time_chars[i] = rx_chars[i+14];
  time_chars[i] = '\0'; // terminate the string
}

void Comms::parse_date(char *rx_chars, char *date_chars){
  int i;
  // parse date
  for (i = 0; i < max_date_length - 1; ++i)
    date_chars[i] = rx_chars[i+2];
  date_chars[i] = '\0'; // terminate the string
}

void Comms::set_cmd_validity(Interface interface, bool cmd_validity){
  if (interface == SERIAL_COM)
    _valid_serial_cmd = cmd_validity;
  else
    _valid_udp_cmd = cmd_validity;
}

void Comms::prep_crc_generator(){
  _crc.restart();
  _crc.setPolynome(0x07);
}

void Comms::calc_reply_crc(Interface interface){
  _tx_calculated_crc = _crc.getCRC();
  send_byte(interface, _tx_calculated_crc);
}

void Comms::config_expected_output(int output){
  // config alarm output expected state depending on configured alarm and current time
  if (_ptr_uc_resources->ptr_ds1307->get_ssrx_alarm_mode(output) == ON_OFF)
    _ptr_uc_resources->ptr_ssr_outputs->set_ssrx_output(output,_ptr_uc_resources->ptr_ds1307->get_expected_ssrx_state(output));
}

void Comms::config_all_expected_outputs(){
  // config ALL alarms output expected state
  for (int i = 0; i < 4; i++) 
    config_expected_output(i+1);
}

void Comms::send_packet(Interface interface, byte num_byte_tx)
{
  if (_tx_crc_enabled)
    prep_crc_generator();
  send_ack(interface);
  for (int i = 0; i < output_buffer_length; i++) {
    send_byte(interface, _output_buffer[i]);
    if (_tx_crc_enabled)
      _crc.add(_output_buffer[i]);
    if (i >= num_byte_tx - 1)
      break;
  }
  if (_tx_crc_enabled)
      calc_reply_crc(interface);
}