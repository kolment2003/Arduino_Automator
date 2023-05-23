/*
  TempProbe.h - Library for handling DS1820B temperature probes
*/

#ifndef TempProbe_h
#define TempProbe_h

#include "Arduino.h"
#include <OneWire.h>

class TempProbe
{
  public:
    TempProbe(int);
    void config_temp_probe();
    void start_temp_conv();
    void read_temp();
    bool get_rom_recognized(int);
    int get_num_rom_recognized();
    float get_probe_reading_celsius(int);

  private:
    int _probe_pin;
    OneWire *_ptr_ds;
    bool _rom_recognized[4] = {false, false,false,false};
    int _num_rom_recognized = 0;
    int _num_probes_found = 0;
    byte _probe_addresses[4][8];
    byte _hardcoded_probe_addresses[4][8] = 
      {
        {0x28, 0x50, 0xFA, 0x75, 0xD0, 0x01, 0x3C, 0xC2},
        {0x28, 0xBD, 0x13, 0x75, 0xD0, 0x01, 0x3C, 0x88},
        {0x28, 0xBB, 0xEA, 0x75, 0xD0, 0x01, 0x3C, 0x6F},
        {0x28, 0x51, 0x6C, 0x75, 0xD0, 0x01, 0x3C, 0xDE}
      };
    bool _probes_found[4] = {false, false,false,false};
    bool _valid_crcs[4] = {false, false,false,false};
    bool _probes_recognized[4] = {false, false,false,false};
    byte _chip_types[4] = {0x00, 0x00, 0x00, 0x00};
    float _probe_reading_celsius[4] = {0,0,0,0};
    float _probe_reading_fahrenheit[4] = {0,0,0,0};
    
    bool byte_array_compare(byte *a,byte *b,int);
};

#endif