/*
  InputIO.h - Library for handling debouncing input push buttons and latches
  and input indicators leds
*/
#ifndef InputIO_h
#define InputIO_h

#include "Arduino.h"
#define MIN_DEBOUNCE_COUNT 10
enum SwitchStates {IS_OPEN, IS_RISING, IS_CLOSED, IS_FALLING};

class InputIO
{
  public:
    InputIO(int, int);
    void run_input_io_fsm();
    void config_input_io_pins();
    bool read_instant_state();
    int get_falling_pulse_count();
    int get_alarm_trigger_count();
    void reset_alarm_trigger_count();
    bool get_determined_input_state();

  private:
    int _input_pin;
    int _indicator_pin;
    bool _indicator_state = false;
    SwitchStates _switch_state = IS_OPEN;
    int _debounce_accumulator = 0;
    bool _input_state = false;
    bool _old_input_state = false;

    int _rising_pulse_cnt = 0;
    int _total_pulse_cnt = 0;
    int _falling_pulse_cnt = 0;    
    int _alarm_trigger_cnt = 0;
    bool _determined_input_state = true;
    bool debounce_input();
};

#endif