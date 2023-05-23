/*
  Automation.h - Top Class Object to hold every important object for 
  arduino automation resources
*/

#ifndef Automation_h
#define Automation_h

#include "Arduino.h"
#include <InputIO.h>
#include <AnalogInput.h>
#include <ACIO.h>
#include <DCIO.h>
#include <TempProbe.h>
#include <Clock.h>

#define DS1820B 10

#define CH_AN_0 A0
#define CH_AN_1 A1

#define PUSH_BUTTON A2
#define PUSH_BUTTON_BLUE_LED A3
#define LATCH_BUTTON A4
#define LATCH_BUTTON_RED_LED A5

class Automation
{
  public:
    Automation();
    InputIO *ptr_blue_push_button;
    InputIO *ptr_red_latch_button;
    AnalogInput *ptr_ch0_probe;
    AnalogInput *ptr_ch1_probe;
    TempProbe *ptr_ds1820b;
    Clock *ptr_ds1307;
    ACIO *ptr_ssr_outputs;
    DCIO *ptr_opto_outputs;

    bool get_input_state(int);
    int get_input_pulse_cnt(int);
    float get_probe_value(int);
  private:
};

#endif