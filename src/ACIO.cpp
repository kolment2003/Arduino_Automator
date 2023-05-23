/*
  ACIO.h - Library for handling AC SSR outputs
*/

#include "Arduino.h"
#include "ACIO.h"

ACIO::ACIO()
{
}

void ACIO::config_ac_io_pins()
{
  for (int i = 0; i < 4; i++)
    pinMode(_ssr_pinout[i], OUTPUT);
}

void ACIO::set_ssr1_output(bool state)
{
  _ssrx_state[0] = state;  
  digitalWrite(SSR_1,_ssrx_state[0]);
}

void ACIO::set_ssr2_output(bool state)
{
  _ssrx_state[1] = state;  
  digitalWrite(SSR_2,_ssrx_state[1]);
}

void ACIO::set_ssr3_output(bool state)
{
  _ssrx_state[2] = state;  
  digitalWrite(SSR_3,_ssrx_state[2]);
}

void ACIO::set_ssr4_output(bool state)
{
  _ssrx_state[3] = state;  
  digitalWrite(SSR_4,_ssrx_state[3]);
}

void ACIO::set_all_ssr_outputs(bool state)
{
  for (int i = 0; i < 4; i++) {
    _ssrx_state[i] = state;
    digitalWrite(_ssr_pinout[i],_ssrx_state[i]);
  }
}

void ACIO::set_ssrx_output(int output, bool state){
  _ssrx_state[output-1] = state;  
  digitalWrite(_ssr_pinout[output-1],_ssrx_state[output-1]);
}

bool ACIO::get_ssrx_output(int output){
  return _ssrx_state[output-1];  
}