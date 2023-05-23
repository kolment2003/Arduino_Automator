/*
  AnalogInput.h - Library for handling analog input
*/

#include "Arduino.h"
#include "AnalogInput.h"

AnalogInput::AnalogInput(int input_pin)
{
  _input_pin = input_pin;
}

void AnalogInput::read_probe()
{
  // analog reading -> 10-bit unsigned value [0-1023] stored in 16-bit  
  // convert to 0-5000mV float
  _raw_adc_array[_array_index++] = analogRead(_input_pin);
  if(_array_index==adc_array_length)_array_index=0;
  _voltage = avg_array(_raw_adc_array,adc_array_length)/1024.0*5000;
}


float AnalogInput::avg_array(int* arr, int number){
  int i;
  float avg;
  long amount=0;

  if(number<=0)
    return 0.0;
  else
  {
    for(i=0;i<number;i++)
    {
      amount+=arr[i];
    }
    avg = amount/(float)number;
    return avg;
  }
}


float AnalogInput::get_analog_value()
{
  return _an_value;
}
