/*
  Clock.h - Library for handling DS1307 real-time clock module
*/

#ifndef Clock_h
#define Clock_h

#include "Arduino.h"
#include <SPI.h>
#include <Wire.h>
#include <DS1307RTC.h>
#include <EEPROM.h>
#include "TimeAlarms.h"
// ON_OFF = 1x alarm on, 1x alarm off
// CYCLE = 1x timerRepeat(# per day), 1x timerOnce(cycle duration)
enum AlarmMode {CYCLE, ON_OFF};
const byte  alarm_output_num = 4;
const byte max_time_length = 9;

class Clock
{
  public:
    Clock();
    tmElements_t get_rtc_tm();
    tmElements_t get_sys_tm();
    bool is_rtc_configured();
    bool is_time_set();
    bool get_parsing_failure();
    int get_clear_eeprom_count();
    int get_set_expected_io_count();
    void increment_set_expected_io_count();
    bool get_master_alarm_enable();
    void set_master_alarm_enable(bool);

    bool config_alarm_or_timer(char *, bool);
    void init_all_alarms(int,void (*)(),void (*)(),void (*)());
    void update_all_alarms_from_eeprom();
    void init_timer(void (*)(),int,bool);
    void swap_mode(int,bool);

    tmElements_t get_ssrx_output_alarm_tm(int, bool);
    bool get_ssrx_output_alarm_enable(int, bool);
    byte get_ssrx_alarm_mode(int);
    bool get_expected_ssrx_state(int);

    bool read_master_alarm_enable_eeprom();
    void write_master_alarm_enable_eeprom();
    void clear_eeprom();

    bool read_rtc_time();
    bool set_rtc_time(const char *,const char *);
    void update_system_time();
    void get_system_time();

  private:
    tmElements_t _rtc_tm;
    tmElements_t _sys_tm;
    bool _time_set = false;
    bool _rtc_configured = false;
    bool _parsing_failure = false;
    int _clear_eeprom_count = 0;
    int _set_expected_io_count = 0;
    bool _master_alarm_enable = false;

    time_t _sys_epoch;
    char _time_chars[max_time_length];

    bool _ssrx_on_alarm_enable[alarm_output_num] = {0};
    bool _ssrx_off_alarm_enable[alarm_output_num] = {0};
    AlarmID_t _ssrx_on_alarm_id[alarm_output_num] = {0};
    AlarmID_t _ssrx_off_alarm_id[alarm_output_num] = {0};
    tmElements_t _ssrx_on_alarm_tm[alarm_output_num];
    tmElements_t _ssrx_off_alarm_tm[alarm_output_num];
    bool _ssrx_on_alarm_tm_validity[alarm_output_num] = {0};
    bool _ssrx_off_alarm_tm_validity[alarm_output_num] = {0};
    byte _ssrx_alarm_mode[alarm_output_num] = {ON_OFF,ON_OFF,ON_OFF,ON_OFF}; // default = on_off

    void save_alarm_to_memory(char *);
    void save_alarm_to_eeprom(int, bool);
    void disable_alarm(int, bool, bool);
    void set_alarm(int, bool);
    void init_alarm(void (*)(),int,bool);

    void parse_alarm_time(char *);
    bool validate_alarm_tm(tmElements_t);
    bool validate_timer_tm(tmElements_t, bool);
    void config_alarm_enable(AlarmID_t, bool);
    void set_ssrx_default_alarm_tm(int, bool,bool);
    void set_default_alarm_tm(tmElements_t *, bool, bool);
    void set_ssrx_output_alarm_tm(int, bool, char *);
    void set_ssrx_output_alarm_enable(int, bool, bool);

    void set_ssrx_alarm_mode(int, byte);
    AlarmID_t get_ssrx_alarm_id(int, bool);
    tmElements_t read_ssrx_output_alarm_eeprom(int, bool);
    bool read_ssrx_output_alarm_enable_eeprom(int, bool);
    byte read_ssrx_alarm_mode_eeprom(int);
    void write_ssrx_alarm_mode_eeprom(int, byte);
    void write_ssrx_output_alarm_enable_eeprom(int, bool, bool);
    void write_ssrx_output_alarm_eeprom(int, bool);

    bool getDate(const char *, tmElements_t *);
    bool getTime(const char *, tmElements_t *);
};
#endif