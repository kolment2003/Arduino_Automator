/*
  Clock.h - Library for handling DS1307 real-time clock module
*/

#include "Arduino.h"
#include "Clock.h"
#include "Comms.h"

#define IO_OFFSET 9
#define ON_OFF_OFFSET 4
#define MASTER_ALARM_ENABLE 36
#define MAX_EEPROM_ADDRESS 56

#define MIN_NUM_TIMER_CYCLES 1 
#define MAX_NUM_TIME_CYCLES 48
#define MIN_CYCLE_DURATION_MINUTES 1
#define MAX_CYCLE_DURATION_MINUTES 15

Clock::Clock()
{
  for (int i = 0; i < 4; i++) {
    set_ssrx_default_alarm_tm(i+1,true, true);
    set_ssrx_default_alarm_tm(i+1,true, false);
  }
}

bool Clock::read_rtc_time(){
  if (RTC.read(_rtc_tm)) 
  {
    _rtc_configured = true;
    return true;
  }
  else
  {
    _rtc_configured = false;
    return false;
  }
}

bool Clock::set_rtc_time(const char *date_str, const char *time_str)
{
  // update rtc + system time
  if (getDate(date_str, &_rtc_tm) && getTime(time_str, &_rtc_tm)) {
    _parsing_failure = false;
    if (RTC.write(_rtc_tm))
    {
      _rtc_configured = true;
      update_system_time();
      return true;
    }
    else 
      return false;
  }
  else
  {
    _parsing_failure = true;
    return false;
  }
}

void Clock::update_system_time()
{
  if (read_rtc_time())
  {
    setTime(_rtc_tm.Hour,
      _rtc_tm.Minute,
      _rtc_tm.Second,
      _rtc_tm.Day,
      _rtc_tm.Month,
      tmYearToCalendar(_rtc_tm.Year));
    get_system_time();
    _time_set = true;
  }
}

void Clock::get_system_time()
{
  _sys_epoch = now();
  breakTime(_sys_epoch, _sys_tm); 
}

bool Clock::getTime(const char *str, tmElements_t* ptr_tmElements_t)
{
  int Hour, Min, Sec;
  if (sscanf(str, "%d:%d:%d", &Hour, &Min, &Sec) != 3) return false;
  ptr_tmElements_t->Hour = Hour;
  ptr_tmElements_t->Minute = Min;
  ptr_tmElements_t->Second = Sec;
  return true;
}

bool Clock::getDate(const char *str, tmElements_t* ptr_tmElements_t)
{
  char Month[12];
  int Day, Year;
  uint8_t monthIndex;
  const char *monthName[12] = {
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
  };
  if (sscanf(str, "%s %d %d", Month, &Day, &Year) != 3) return false;
  for (monthIndex = 0; monthIndex < 12; monthIndex++) 
    if (strcmp(Month, monthName[monthIndex]) == 0) break;
  
  if (monthIndex >= 12) return false;
  ptr_tmElements_t->Day = Day;
  ptr_tmElements_t->Month = monthIndex + 1;
  ptr_tmElements_t->Year = CalendarYrToTm(Year);
  return true;
}

tmElements_t Clock::get_ssrx_output_alarm_tm(int output, bool on_off)
{
  tmElements_t tmp_tm = (on_off ? _ssrx_on_alarm_tm[output-1] : _ssrx_off_alarm_tm[output-1]);
  return tmp_tm;
}

void Clock::set_ssrx_output_alarm_tm(int output, bool on_off, char *time_str)
{
  if (on_off)
    getTime(time_str, &_ssrx_on_alarm_tm[output-1]);
  else
    getTime(time_str, &_ssrx_off_alarm_tm[output-1]);
}

tmElements_t Clock::read_ssrx_output_alarm_eeprom(int output, bool on_off)
{
  tmElements_t tmp_tm;
  tmp_tm.Year = 0;
  tmp_tm.Month = 1;
  tmp_tm.Day = 1;

  if (on_off)
  {
    tmp_tm.Hour = EEPROM.read((output-1)*IO_OFFSET+1);
    tmp_tm.Minute = EEPROM.read((output-1)*IO_OFFSET+2);
    tmp_tm.Second = EEPROM.read((output-1)*IO_OFFSET+3);
  }
  else
  {
    tmp_tm.Hour = EEPROM.read(((output-1)*IO_OFFSET)+ON_OFF_OFFSET+1);
    tmp_tm.Minute = EEPROM.read(((output-1)*IO_OFFSET)+ON_OFF_OFFSET+2);
    tmp_tm.Second = EEPROM.read(((output-1)*IO_OFFSET)+ON_OFF_OFFSET+3);
  }
  return tmp_tm;
}

void Clock::write_ssrx_output_alarm_eeprom(int output, bool on_off)
{
  tmElements_t tmp_tm = (on_off ? _ssrx_on_alarm_tm[output-1] : _ssrx_off_alarm_tm[output-1]);
  if (on_off)
  {
    EEPROM.write((output-1)*IO_OFFSET+1,tmp_tm.Hour);
    EEPROM.write((output-1)*IO_OFFSET+2,tmp_tm.Minute);
    EEPROM.write((output-1)*IO_OFFSET+3,tmp_tm.Second);
  }
  else
  {
    EEPROM.write(((output-1)*IO_OFFSET)+ON_OFF_OFFSET+1,tmp_tm.Hour);
    EEPROM.write(((output-1)*IO_OFFSET)+ON_OFF_OFFSET+2,tmp_tm.Minute);
    EEPROM.write(((output-1)*IO_OFFSET)+ON_OFF_OFFSET+3,tmp_tm.Second);
  }
}

bool Clock::get_ssrx_output_alarm_enable(int output, bool on_off)
{
  return (on_off ? _ssrx_on_alarm_enable[output-1] : _ssrx_off_alarm_enable[output-1]);
} 

void Clock::set_ssrx_output_alarm_enable(int output, bool on_off, bool set_enable)
{
  if (on_off)
    _ssrx_on_alarm_enable[output-1] = set_enable;
  else
    _ssrx_off_alarm_enable[output-1] = set_enable;
}

bool Clock::read_ssrx_output_alarm_enable_eeprom(int output, bool on_off)
{
  bool tmp_enable;
  byte tmp_numerical_enable;
  if (on_off)
    tmp_numerical_enable = EEPROM.read((output-1)*IO_OFFSET);
  else
    tmp_numerical_enable = EEPROM.read(((output-1)*IO_OFFSET)+ON_OFF_OFFSET);

  if (tmp_numerical_enable == 0)
    return false;
  else
    return true;
}

void Clock::write_ssrx_output_alarm_enable_eeprom(int output, bool on_off, bool set_enable)
{
  if (on_off)
    EEPROM.write((output-1)*IO_OFFSET, set_enable);
  else
    EEPROM.write(((output-1)*IO_OFFSET)+ON_OFF_OFFSET, set_enable);
}

byte Clock::get_ssrx_alarm_mode(int output)
{
  return  _ssrx_alarm_mode[output-1];
} 

void Clock::set_ssrx_alarm_mode(int output, byte mode)
{
  _ssrx_alarm_mode[output-1] = mode;
}

byte Clock::read_ssrx_alarm_mode_eeprom(int output)
{
  return EEPROM.read((output*IO_OFFSET)-1);  
}

void Clock::write_ssrx_alarm_mode_eeprom(int output, byte mode)
{
  EEPROM.write((output*IO_OFFSET)-1,mode); 
}

void Clock::update_all_alarms_from_eeprom()
{
  for (int i = 0; i < 4; i++) {
    _ssrx_alarm_mode[i] = read_ssrx_alarm_mode_eeprom(i+1);
  }
  for (int i = 0; i < 4; i++) {
    _ssrx_on_alarm_tm[i] = read_ssrx_output_alarm_eeprom(i+1, true);
    _ssrx_off_alarm_tm[i] = read_ssrx_output_alarm_eeprom(i+1, false);
  }
  for (int i = 0; i < 4; i++) {
    if (_ssrx_alarm_mode[i] == ON_OFF)
    {
      _ssrx_on_alarm_tm_validity[i] = validate_alarm_tm(_ssrx_on_alarm_tm[i]);  
      _ssrx_off_alarm_tm_validity[i] = validate_alarm_tm(_ssrx_off_alarm_tm[i]);
    }
    else
    {
      _ssrx_on_alarm_tm_validity[i] = validate_timer_tm(_ssrx_on_alarm_tm[i], true);  
      _ssrx_off_alarm_tm_validity[i] = validate_timer_tm(_ssrx_off_alarm_tm[i], false);
    }
  }
  for (int i = 0; i < 4; i++) {
    _ssrx_on_alarm_enable[i] = read_ssrx_output_alarm_enable_eeprom(i+1, true);
    _ssrx_off_alarm_enable[i] = read_ssrx_output_alarm_enable_eeprom(i+1, false);
  }
}

void Clock::set_default_alarm_tm(tmElements_t* ptr_tmElements_t, bool alarm_timer, bool cycle_mode)
{
  ptr_tmElements_t->Year = 0;
  ptr_tmElements_t->Month = 1;
  ptr_tmElements_t->Day = 1;
  if (alarm_timer)
  {
    ptr_tmElements_t->Hour = 0;
    ptr_tmElements_t->Minute = 0;
    ptr_tmElements_t->Second = 0;
  }
  else
  {
    if(cycle_mode)
    {
      ptr_tmElements_t->Hour = 0;
      ptr_tmElements_t->Minute = MIN_CYCLE_DURATION_MINUTES;
      ptr_tmElements_t->Second = 0;
    }
    else
    {
      ptr_tmElements_t->Hour = 23;
      ptr_tmElements_t->Minute = 59;
      ptr_tmElements_t->Second = 59;    
    }
  }
}

void Clock::set_ssrx_default_alarm_tm(int output, bool alarm_timer, bool on_off)
{
  if (on_off)
    set_default_alarm_tm(&_ssrx_on_alarm_tm[output-1],alarm_timer,on_off);
  else
    set_default_alarm_tm(&_ssrx_off_alarm_tm[output-1],alarm_timer,on_off);
}

AlarmID_t Clock::get_ssrx_alarm_id(int output, bool on_off)
{
  if (on_off)
    return _ssrx_on_alarm_id[output-1];
  else
    return _ssrx_off_alarm_id[output-1];
}

bool Clock::read_master_alarm_enable_eeprom()
{
  if (EEPROM.read(MASTER_ALARM_ENABLE) == 0)
    return false;
  else
    return true;
}

void Clock::write_master_alarm_enable_eeprom()
{
  if (_master_alarm_enable)
    EEPROM.write(MASTER_ALARM_ENABLE, 1);
  else
    EEPROM.write(MASTER_ALARM_ENABLE, 0);
}

void Clock::clear_eeprom()
{
  _clear_eeprom_count++;
  for (int i = 0 ; i < (MAX_EEPROM_ADDRESS+1); i++) 
    EEPROM.write(i, 0);
}

bool Clock::validate_alarm_tm(tmElements_t alarm_tm)
{
  if (alarm_tm.Hour > 23 || alarm_tm.Minute > 59 || alarm_tm.Second > 59)
    return false;
  return true;
}

bool Clock::validate_timer_tm(tmElements_t alarm_tm, bool cycle_mode)
{
  int cycles_per_day;
  int duration_minutes;
  if (cycle_mode)
  {
    cycles_per_day = SECS_PER_DAY/makeTime(alarm_tm);
    if (cycles_per_day < MIN_NUM_TIMER_CYCLES || cycles_per_day > MAX_NUM_TIME_CYCLES)
      return false;
  }
  else
  {
    duration_minutes = makeTime(alarm_tm)/SECS_PER_MIN;
    if (duration_minutes < MIN_CYCLE_DURATION_MINUTES || duration_minutes > MAX_CYCLE_DURATION_MINUTES)
      return false;
  }
  return true;
}

void Clock::config_alarm_enable(AlarmID_t alarm_id, bool alarm_enable)
{
  if (alarm_enable)
    Alarm.enable(alarm_id);
  else
    Alarm.disable(alarm_id);
}

void Clock::disable_alarm(int output, bool alarm_timer, bool on_off)
{
  bool enable = false;
  set_ssrx_output_alarm_enable(output, on_off, enable);
  write_ssrx_output_alarm_enable_eeprom(output,on_off, enable);
  set_ssrx_default_alarm_tm(output,alarm_timer,on_off);
  write_ssrx_output_alarm_eeprom(output,on_off);
}

void Clock::parse_alarm_time(char *rx_chars){
  int i;
  // parse time
  for (i = 0; i < max_time_length - 1; ++i)
    _time_chars[i] = rx_chars[i+7];
  _time_chars[i] = '\0'; // terminate the string
}

void Clock::init_alarm(void (*on_off_callback)(),int output, bool on_off)
{
  tmElements_t tmp_tm = get_ssrx_output_alarm_tm(output,on_off);
  if(on_off)
  {
    _ssrx_on_alarm_id[output-1] = Alarm.alarmRepeat(tmp_tm.Hour, tmp_tm.Minute, tmp_tm.Second, on_off_callback);
    config_alarm_enable(_ssrx_on_alarm_id[output-1], _ssrx_on_alarm_enable[output-1]);
  }
  else
  {
    _ssrx_off_alarm_id[output-1] = Alarm.alarmRepeat(tmp_tm.Hour, tmp_tm.Minute, tmp_tm.Second, on_off_callback);
    config_alarm_enable(_ssrx_off_alarm_id[output-1], _ssrx_off_alarm_enable[output-1]);   
  }
}

void Clock::init_timer(void (*cycle_callback)(),int output, bool cycle_mode)
{
  tmElements_t tmp_tm = get_ssrx_output_alarm_tm(output,cycle_mode);
  if (cycle_mode)
  {
    _ssrx_on_alarm_id[output-1] = Alarm.timerRepeat(tmp_tm.Hour, tmp_tm.Minute, tmp_tm.Second, cycle_callback);
    config_alarm_enable(_ssrx_on_alarm_id[output-1], _ssrx_on_alarm_enable[output-1]);
  }
  else
  {
    _ssrx_off_alarm_id[output-1] = Alarm.timerOnce(tmp_tm.Hour, tmp_tm.Minute, tmp_tm.Second, cycle_callback);
    config_alarm_enable(_ssrx_off_alarm_id[output-1], _ssrx_off_alarm_enable[output-1]);
  }
}

void Clock::init_all_alarms(int output, void (*on_callback)(), void (*off_callback)(), void (*cycle_callback)())
{
  if (_ssrx_alarm_mode[output-1] == ON_OFF)
  {
    // config on ssr alarms
    if (_ssrx_on_alarm_tm_validity[output-1] == false || _time_set == false)
      disable_alarm(output, true, true);
    init_alarm(on_callback, output, true);  
    // config off ssr alarms
    if (_ssrx_off_alarm_tm_validity[output-1] == false || _time_set == false)
      disable_alarm(output, true, false);
    init_alarm(off_callback, output, false);
  }
  else if (_ssrx_alarm_mode[output-1] == CYCLE)
  {
    if (_ssrx_on_alarm_tm_validity[output-1] == false ||
        _ssrx_off_alarm_tm_validity[output-1] == false ||
        _time_set == false)
    {
      disable_alarm(output, false, true);
      disable_alarm(output, false, false);
    }
    init_timer(cycle_callback, output, true);
  }
}

bool Clock::config_alarm_or_timer(char *rx_chars, bool alarm_timer)
{
  bool validation;
  int output = Comms::char_to_int(rx_chars[3]);
  bool on_off = Comms::char_to_bool(rx_chars[4]);
  bool enable = Comms::char_to_bool(rx_chars[5]);

  if (output >= 1 && output <= 4)
  {
    save_alarm_to_memory(rx_chars);
    tmElements_t tmp_tm = get_ssrx_output_alarm_tm(output,on_off);
    if(alarm_timer)
      validation = validate_alarm_tm(tmp_tm);
    else
      validation = validate_timer_tm(tmp_tm, on_off);
    if (validation == false || _time_set == false)
    {
      disable_alarm(output, alarm_timer, on_off);
      set_alarm(output, on_off);
      return true;
    }
    else
      save_alarm_to_eeprom(output,on_off);
    if (alarm_timer || on_off) // only config cycle timer, duration timer is configured on the fly!
      set_alarm(output, on_off);
    return true;
  }
  else
    return false;
}

void Clock::set_alarm(int output, bool on_off)
{
  AlarmID_t tmp_id;
  tmp_id = get_ssrx_alarm_id(output, on_off);
  Alarm.write(tmp_id, makeTime(get_ssrx_output_alarm_tm(output,on_off)));       
  config_alarm_enable(tmp_id, get_ssrx_output_alarm_enable(output,on_off));
}

void Clock::swap_mode(int output, bool alarm_timer)
{
  tmElements_t tm_on;
  tmElements_t tm_off;
  AlarmID_t tmp_id;
  if(get_ssrx_alarm_mode(output) != alarm_timer)
  {
    set_ssrx_alarm_mode(output,alarm_timer);
    write_ssrx_alarm_mode_eeprom(output,alarm_timer);
    tm_on = get_ssrx_output_alarm_tm(output,true);
    tm_off = get_ssrx_output_alarm_tm(output,false);
    if (alarm_timer)
    {
      // CYCLE -> ON_OFF
      if (validate_alarm_tm(tm_on) == false || validate_alarm_tm(tm_off) == false)
      {
        disable_alarm(output, alarm_timer, true);
        disable_alarm(output, alarm_timer, false);
      }
      set_alarm(output,true);
      set_alarm(output,false);
    }
    else
    {
      // ON_OFF -> CYCLE
      if (validate_timer_tm(tm_on,true) == false || validate_timer_tm(tm_off,false) == false)
      {
        disable_alarm(output, alarm_timer, true);
        disable_alarm(output, alarm_timer, false);
        set_alarm(output,true);
        set_alarm(output,false);
      }
      else
        // 1st disable cycle timer
        tmp_id = get_ssrx_alarm_id(output, false);
        config_alarm_enable(tmp_id, false);
        set_alarm(output,true);
    }
  }
}

void Clock::save_alarm_to_memory(char *rx_chars){
  int output = Comms::char_to_int(rx_chars[3]);
  bool on_off = Comms::char_to_bool(rx_chars[4]);
  bool enable = Comms::char_to_bool(rx_chars[5]);
  parse_alarm_time(rx_chars);
  set_ssrx_output_alarm_tm(output, on_off, _time_chars);
  set_ssrx_output_alarm_enable(output, on_off, enable);
}

void Clock::save_alarm_to_eeprom(int output, bool on_off){
  write_ssrx_output_alarm_eeprom(output, on_off);
  write_ssrx_output_alarm_enable_eeprom(output, on_off,get_ssrx_output_alarm_enable(output, on_off));
}

bool Clock::get_expected_ssrx_state(int output)
{
  AlarmID_t tmp_on_id = get_ssrx_alarm_id(output, true);
  AlarmID_t tmp_off_id = get_ssrx_alarm_id(output, false);

  time_t daily_epoch = elapsedSecsToday(now());
  time_t tmp_on_epoch = Alarm.read(tmp_on_id);
  time_t tmp_off_epoch = Alarm.read(tmp_off_id);

  if(get_ssrx_output_alarm_enable(output,true) && get_ssrx_output_alarm_enable(output,false))
  {
    if (tmp_on_epoch < tmp_off_epoch)
    {
      if (daily_epoch < tmp_on_epoch)
        return false;
      else
      {
        if (daily_epoch < tmp_off_epoch)
          return true;
        else
          return false;
      }
    }
    else
    {
      if (daily_epoch < tmp_off_epoch)
        return true;
      else
      {
        if(daily_epoch < tmp_on_epoch)
          return false;
        else
          return true;
      }
    }
  }
  else
    return false;
}

bool Clock::is_rtc_configured()
{
  return _rtc_configured;
}

bool Clock::is_time_set()
{
  return _time_set;
}

bool Clock::get_parsing_failure()
{
  return _parsing_failure;
}

int Clock::get_clear_eeprom_count()
{
  return _clear_eeprom_count;
}

int Clock::get_set_expected_io_count()
{
  return _set_expected_io_count;
}

void Clock::increment_set_expected_io_count()
{
  _set_expected_io_count++;
}

void Clock::set_master_alarm_enable(bool value)
{
  _master_alarm_enable = value;
}

bool Clock::get_master_alarm_enable()
{
  return _master_alarm_enable;
}

tmElements_t Clock::get_rtc_tm()
{
 return _rtc_tm; 
}

tmElements_t Clock::get_sys_tm()
{
 return _sys_tm; 
}