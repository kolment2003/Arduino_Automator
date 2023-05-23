/*
  DCIO.h - Library for handling 12VDC opto outputs
*/

#include "Arduino.h"
#include "DCIO.h"

DCIO::DCIO()
{
}

void DCIO::config_dc_io_pins()
{
  for (int i = 0; i < 4; i++)
    pinMode(_opto_pinout[i], OUTPUT);
}

void DCIO::set_opto1_output(bool state)
{
  _optox_state[0] = state;  
  digitalWrite(OPTO_1,_optox_state[0]);
}

void DCIO::set_opto2_output(bool state)
{
  _optox_state[1] = state;  
  digitalWrite(OPTO_2,_optox_state[1]);
}

void DCIO::set_opto3_output(bool state)
{
  _optox_state[2] = state;  
  digitalWrite(OPTO_3,_optox_state[2]);
}

void DCIO::set_opto4_output(bool state)
{
  _optox_state[3] = state;  
  digitalWrite(OPTO_4,_optox_state[3]);
}

void DCIO::set_optox_output(int output, bool state){
  _optox_state[output-1] = state;  
  digitalWrite(_opto_pinout[output-1],_optox_state[output-1]);
}    

bool DCIO::get_optox_output(int output){
  return _optox_state[output-1];
}

void DCIO::set_all_opto_outputs(bool state)
{
  for (int i = 0; i < 4; i++) {
    _optox_state[i] = state;
    digitalWrite(_opto_pinout[i],_optox_state[i]);
  }
}

int DCIO::get_optox_pulse_count(int output){
  return _optox_pulse_count[output-1];
}

void DCIO::increment_optox_pulse_count(int output, int pulse_n_increments){
  _optox_pulse_count[output-1] = _optox_pulse_count[output-1] + pulse_n_increments;
}    

void DCIO::start_all_opto_pulses()
{
  for (int i = 0; i < 4; i++) {
    if (_optox_executed_pulse_count[i] < _optox_pulse_count[i])
      {
        set_optox_output(i+1, true);
        _optox_executed_pulse_count[i]++;
        _optox_pulse_in_progress[i] = true;
      }
  }
}

void DCIO::end_all_opto_pulses()
{
  for (int i = 0; i < 4; i++) {
    if (_optox_executed_pulse_count[i] == _optox_pulse_count[i] && _optox_pulse_in_progress[i])
    {
      set_optox_output(i+1, false);
      _optox_pulse_in_progress[i] = false;
    }
  }
}