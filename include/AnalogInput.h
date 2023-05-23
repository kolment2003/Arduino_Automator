/*
  AnalogInput.h - Library for handling analog input
*/
#ifndef AnalogInput_h
#define AnalogInput_h

#include "Arduino.h"

const byte adc_array_length = 10;

class AnalogInput
{
  public:
    AnalogInput(int);    
    void read_probe();
    float get_analog_value();

  private:
    int _input_pin;
    float _voltage;
    int _raw_adc_array[adc_array_length];   //Store the average value of the sensor feedback
    int _array_index=0;
    float _an_value;

    void read_an();
    float avg_array(int*, int);
};

#endif