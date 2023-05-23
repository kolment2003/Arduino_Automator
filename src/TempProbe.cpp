/*
  TempProbe.h - Library for handling DS1820B temperature probes
*/

#include "Arduino.h"
#include "TempProbe.h"

TempProbe::TempProbe(int probe_pin)
{
  _probe_pin = probe_pin;
  _ptr_ds = new OneWire(_probe_pin);
}

void TempProbe::config_temp_probe()
{
  byte i  = 0;
  byte h;
  byte c;
  bool rom_matched;

  while(_ptr_ds->search(&_probe_addresses[i][0]) && i < 4)
  {
    _probes_found[i] = true;
    if (OneWire::crc8(&_probe_addresses[i][0], 7) != _probe_addresses[i][7]) 
      _valid_crcs[i] = false;
    else
    {
      _valid_crcs[i] = true;
      // the first ROM byte indicates which chip
      switch (_probe_addresses[i][0]) {
        case 0x10:
          _chip_types[i] = 0x10;
          _probes_recognized[i] = true;
          break;
        case 0x28:
          _chip_types[i] = 0x28;
          _probes_recognized[i] = true;
          break;
        case 0x22:
          _chip_types[i] = 0x22;
          _probes_recognized[i] = true;
          break;
        default:
          _chip_types[i] = 0x00;
          _probes_recognized[i] = true;
      }
    }
    // check if a hardcoded ROM # is recognized
    if (_probes_recognized[i])
    {
      rom_matched = false;
      c = 0;
      while(!rom_matched && c < 4)
      {
        rom_matched = byte_array_compare(&_probe_addresses[i][0], &_hardcoded_probe_addresses[c][0], 8);
        c += 1;
      }
      if (rom_matched)
      {
        _rom_recognized[c - 1] = rom_matched;
        _num_rom_recognized += 1;
      }
    }
    i += 1;
  }
  _num_probes_found = i;
}

void TempProbe::start_temp_conv()
{
  for( byte i = 0; i < 4; i++) 
  {
    if (_rom_recognized[i])
    {
      _ptr_ds->reset();
      _ptr_ds->select(&_hardcoded_probe_addresses[i][0]);
      _ptr_ds->write(0x44); // start conversion, with parasite power on at the end wait 1000 ms per sensor
    }
  }
}

void TempProbe::read_temp()
{
  byte i;
  byte present = 0;
  byte type_s;
  byte data[12];

  for( byte c = 0; c < 4; c++)
  {
    if (_rom_recognized[c])
    {
      // we might do a ds.depower() here, but the reset will take care of it.
      present = _ptr_ds->reset();
      _ptr_ds->select(&_hardcoded_probe_addresses[c][0]);    
      _ptr_ds->write(0xBE);         // Read Scratchpad

      for ( i = 0; i < 9; i++) {           // we need 9 bytes
        data[i] = _ptr_ds->read();
      }
      // Convert the data to actual temperature
      // because the result is a 16 bit signed integer, it should
      // be stored to an "int16_t" type, which is always 16 bits
      // even when compiled on a 32 bit processor.
      int16_t raw = (data[1] << 8) | data[0];
      if (type_s) {
        raw = raw << 3; // 9 bit resolution default
        if (data[7] == 0x10) {
          // "count remain" gives full 12 bit resolution
          raw = (raw & 0xFFF0) + 12 - data[6];
        }
      } 
      else {
        byte cfg = (data[4] & 0x60);
        // at lower res, the low bits are undefined, so let's zero them
        if (cfg == 0x00) raw = raw & ~7;  // 9 bit resolution, 93.75 ms
        else if (cfg == 0x20) raw = raw & ~3; // 10 bit res, 187.5 ms
        else if (cfg == 0x40) raw = raw & ~1; // 11 bit res, 375 ms
        //// default is 12 bit resolution, 750 ms conversion time
      }
      _probe_reading_celsius[c] = (float)raw / 16.0;
      _probe_reading_fahrenheit[c] = _probe_reading_celsius[c] * 1.8 + 32.0;
    }
  }
}

bool TempProbe::byte_array_compare(byte *a, byte *b, int array_size)
{
   for (int i = 0; i < array_size; ++i)
     if (a[i] != b[i])
       return(false);
   return(true);
}

bool TempProbe::get_rom_recognized(int input)
{
  return _rom_recognized[input-1]; 
}

int TempProbe::get_num_rom_recognized()
{
  return _num_rom_recognized; 
}

float TempProbe::get_probe_reading_celsius(int input)
{
  return _probe_reading_celsius[input-1]; 
}