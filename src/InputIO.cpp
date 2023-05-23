/*
  InputIO.h - Library for handling debouncing input push buttons and latches
  and input indicators leds
*/

#include "Arduino.h"
#include "InputIO.h"

InputIO::InputIO(int input_pin, int indicator_pin)
{
  _input_pin = input_pin;
  _indicator_pin = indicator_pin; 
}

bool InputIO::debounce_input()
{
  // return true if input pin state change detected
  _input_state = digitalRead(_input_pin);
  if (_input_state != _old_input_state)
  {
    _debounce_accumulator = 0; // reset
  }
  else
  {
    if (_debounce_accumulator < MIN_DEBOUNCE_COUNT)
    {
      _debounce_accumulator += 1;
    }
  }
  if (_debounce_accumulator >= MIN_DEBOUNCE_COUNT)
  {
    _determined_input_state = _input_state;
    return true;
  }
  else
  {
    _old_input_state = _input_state;
    return false;
  }
}

void InputIO::config_input_io_pins()
{
  pinMode(_input_pin, INPUT);
  pinMode(_indicator_pin, OUTPUT);
  // get initial value
  _input_state = digitalRead(_input_pin);
  _old_input_state = _input_state;
}

bool InputIO::read_instant_state()
{
  return digitalRead(_input_pin);
}


void InputIO::run_input_io_fsm()
{
  // input pin handling code
  if (debounce_input())
  {
    switch (_switch_state) {
      case IS_OPEN:    { 
        if(_determined_input_state == LOW) 
          {
            _switch_state = IS_FALLING;
          }
        break; 
        }
      case IS_RISING:  {
        _indicator_state = false; 
        digitalWrite(_indicator_pin, _indicator_state);
        _switch_state = IS_OPEN;
        _rising_pulse_cnt += 1;
        _total_pulse_cnt += 1;
        _alarm_trigger_cnt += 1;
        break; 
        }
      case IS_CLOSED:  { 
        if(_determined_input_state == HIGH)
        {
          _switch_state = IS_RISING;
        }
        break;
        }
      case IS_FALLING: {
        _indicator_state = true; 
        digitalWrite(_indicator_pin, _indicator_state);
        _falling_pulse_cnt += 1;
        _total_pulse_cnt += 1;
        _switch_state = IS_CLOSED;
        break; 
        }
    }
  }
}

int InputIO::get_falling_pulse_count()
{
  return _falling_pulse_cnt;
}

int InputIO::get_alarm_trigger_count()
{
  return _alarm_trigger_cnt;
}

void InputIO::reset_alarm_trigger_count()
{
  _alarm_trigger_cnt = 0;
}

bool InputIO::get_determined_input_state()
{
  return _determined_input_state;
}