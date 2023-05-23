/*
  ACIO.h - Library for handling AC SSR outputs
*/

#ifndef ACIO_h
#define ACIO_h

#include "Arduino.h"

#define SSR_1 2
#define SSR_2 3
#define SSR_3 4
#define SSR_4 5

const byte  ssr_output_num = 4;

class ACIO
{
  public:
    ACIO();
    void config_ac_io_pins();
    void set_ssr1_output(bool);
    void set_ssr2_output(bool);
    void set_ssr3_output(bool);
    void set_ssr4_output(bool);
    void set_ssrx_output(int, bool);
    bool get_ssrx_output(int);
    void set_all_ssr_outputs(bool);

  private:
    bool _ssrx_state[ssr_output_num] = {0};
    pin_size_t _ssr_pinout[ssr_output_num] = {SSR_1,SSR_2,SSR_3,SSR_4};
};

#endif
