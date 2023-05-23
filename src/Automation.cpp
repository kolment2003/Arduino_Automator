/*
  Automation.h - Top Class Object to hold every important object for 
  arduino automation resources
*/

#include "Arduino.h"
#include "Automation.h"

Automation::Automation()
{
  ptr_blue_push_button = new InputIO(PUSH_BUTTON,PUSH_BUTTON_BLUE_LED);
  ptr_red_latch_button = new InputIO(LATCH_BUTTON,LATCH_BUTTON_RED_LED);
  ptr_ch0_probe = new  AnalogInput(CH_AN_0);
  ptr_ch1_probe = new AnalogInput(CH_AN_1);
  ptr_ds1820b = new TempProbe(DS1820B);
  ptr_ds1307 = new Clock;
  ptr_ssr_outputs = new ACIO;
  ptr_opto_outputs = new DCIO;
}

bool Automation::get_input_state(int io_num)
{
  if (io_num == 1)
    return ptr_blue_push_button->get_determined_input_state();
  else if (io_num == 2)
    return ptr_red_latch_button->get_determined_input_state();
}

int Automation::get_input_pulse_cnt(int io_num)
{
  if (io_num == 1)
    return ptr_blue_push_button->get_falling_pulse_count();
  else if (io_num == 2)
    return ptr_red_latch_button->get_falling_pulse_count();
}

float Automation::get_probe_value(int io_num)
{
  if (io_num == 1)
    return ptr_ch0_probe->get_analog_value();
  else if (io_num == 2)
    return ptr_ch1_probe->get_analog_value();
}