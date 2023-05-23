/*
  DCIO.h - Library for handling 12VDC opto outputs
*/

#ifndef DCIO_h
#define DCIO_h

#include "Arduino.h"

#define OPTO_1 6
#define OPTO_2 7
#define OPTO_3 8
#define OPTO_4 9

const byte  opto_output_num = 4;

class DCIO
{
  public:
    DCIO();
    void config_dc_io_pins();
    void set_opto1_output(bool);
    void set_opto2_output(bool);
    void set_opto3_output(bool);
    void set_opto4_output(bool);
    void set_optox_output(int, bool);
    bool get_optox_output(int);
    void set_all_opto_outputs(bool);

    int get_optox_pulse_count(int);
    void increment_optox_pulse_count(int, int);
    void start_all_opto_pulses();
    void end_all_opto_pulses();

  private:
    bool _optox_state[opto_output_num] = {0};
    pin_size_t _opto_pinout[opto_output_num] = {OPTO_1,OPTO_2,OPTO_3,OPTO_4};
    int _optox_pulse_count[opto_output_num] = {0};
    int _optox_executed_pulse_count[opto_output_num] = {0};
    bool _optox_pulse_in_progress[opto_output_num] = {0};
};

#endif