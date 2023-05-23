// User Defined Classes
#include <InputIO.h>
#include <ACIO.h>
#include <DCIO.h>
#include <TempProbe.h>
#include <Clock.h>
#include <Automation.h>
#include <Comms.h>

// Task Schedule Compile Options -------------------------------------------------------------------------------------------
// #define _TASK_TIMECRITICAL      // Enable monitoring scheduling overruns
#define _TASK_SLEEP_ON_IDLE_RUN // Enable 1 ms SLEEP_IDLE powerdowns between tasks if no callback methods were invoked during the pass
#define _TASK_STATUS_REQUEST    // Compile with support for StatusRequest functionality - triggering tasks on status change events in addition to time only
// #define _TASK_WDT_IDS           // Compile with support for wdt control points and task ids
// #define _TASK_LTS_POINTER       // Compile with support for local task storage pointer
// #define _TASK_PRIORITY          // Support for layered scheduling priority
// #define _TASK_MICRO_RES         // Support for microsecond resolution
// #define _TASK_STD_FUNCTION      // Support for std::function (ESP8266 and ESP32 ONLY)
// #define _TASK_DEBUG             // Make all methods and variables public for debug purposes
// #define _TASK_INLINE            // Make all methods "inline" - needed to support some multi-tab, multi-file implementations
// #define _TASK_TIMEOUT           // Support for overall task timeout
// #define _TASK_OO_CALLBACKS      // Support for dynamic callback method binding
#include <TaskScheduler.h>

// IO mapping
#define DS1820B 10

#define CH_AN_0 A0
#define CH_AN_1 A1

#define PUSH_BUTTON A2
#define PUSH_BUTTON_BLUE_LED A3
#define LATCH_BUTTON A4
#define LATCH_BUTTON_RED_LED A5

// function prototypes ************************************************************************
// task handlers
void handle_input_io();
void handle_analog_input();
// temp probe handlers
void handle_system_time_drift();
void handle_temp_conv_start();
void handle_temp_conv_wait();
void handle_temp_reading();
void handle_pulse_start();
void handle_pulse_wait();
void handle_pulse_end();
void handle_uart_rx();
void handle_udp_rx();
void handle_connection();
void handle_rtc();
void handle_config_alarm();

// alarm handlers
void init_alarms();
void execute_ssr_alarm_action(int,bool);
typedef void (*callbacks) ();
void start_cycle(int);
void stop_cycle(int);
void ssr1_on_alarm();
void ssr2_on_alarm();
void ssr3_on_alarm();
void ssr4_on_alarm();
void ssr1_off_alarm();
void ssr2_off_alarm();
void ssr3_off_alarm();
void ssr4_off_alarm();
void ssr1_start_cycle_timer();
void ssr1_stop_cycle_timer();
void ssr2_start_cycle_timer();
void ssr2_stop_cycle_timer();
void ssr3_start_cycle_timer();
void ssr3_stop_cycle_timer();
void ssr4_start_cycle_timer();
void ssr4_stop_cycle_timer();

// globals ***********************************************************************************
StatusRequest st_temp_probe;
StatusRequest st_opto_pulse;
Scheduler ts;

Automation uc_resources;
Comms com_interfaces(&uc_resources);

// tasks
#define PERIOD_SYNC_TIME 86400000
Task t_handle_system_time_drift( PERIOD_SYNC_TIME * TASK_MILLISECOND, -1, &handle_system_time_drift, &ts, true );

#define PERIOD_INPUT_SWITCHES 50
Task t_handle_input_io( PERIOD_INPUT_SWITCHES * TASK_MILLISECOND, -1, &handle_input_io, &ts, true );

#define PERIOD_TEMPERATURE 3000
Task t_handle_temp_conv_start(TASK_IMMEDIATE,TASK_ONCE, &handle_temp_conv_start, &ts, true);
Task t_handle_temp_conv_wait( TASK_IMMEDIATE, TASK_ONCE, &handle_temp_conv_wait, &ts, false);
Task t_handle_temp_reading(&handle_temp_reading, &ts);

#define PERIOD_PULSE 500
Task t_handle_pulse_start(TASK_IMMEDIATE,TASK_ONCE, &handle_pulse_start, &ts, true);
Task t_handle_pulse_wait( TASK_IMMEDIATE, TASK_ONCE, &handle_pulse_wait, &ts, false);
Task t_handle_pulse_end(&handle_pulse_end, &ts);

#define PERIOD_ANALOG_INPUT 250
Task t_read_analog_input( PERIOD_ANALOG_INPUT * TASK_MILLISECOND, -1, &handle_analog_input, &ts, true );

#define PERIOD_UART 50
Task t_handle_uart_rx( PERIOD_UART * TASK_MILLISECOND, -1, &handle_uart_rx, &ts, true );

#define PERIOD_CONN_CHECK 15000
Task t_handle_check_connection( PERIOD_CONN_CHECK * TASK_MILLISECOND, -1, &handle_connection, &ts, true );
#define PERIOD_UDP 50
Task t_handle_udp_rx( PERIOD_UDP * TASK_MILLISECOND, -1, &handle_udp_rx, &ts, true );

#define PERIOD_CONFIG_ALARM 1000
Task t_handle_config_alarm( PERIOD_CONFIG_ALARM * TASK_MILLISECOND, -1, &handle_config_alarm, &ts, true );

callbacks ssrx_on_callbacks[] =
{
  ssr1_on_alarm,
  ssr2_on_alarm,
  ssr3_on_alarm,
  ssr4_on_alarm
};
callbacks ssrx_off_callbacks[] =
{
  ssr1_off_alarm,
  ssr2_off_alarm,
  ssr3_off_alarm,
  ssr4_off_alarm
};
callbacks ssrx_start_cycle_timer_callbacks[] =
{
  ssr1_start_cycle_timer,
  ssr2_start_cycle_timer,
  ssr3_start_cycle_timer,
  ssr4_start_cycle_timer
};
callbacks ssrx_stop_cycle_timer_callbacks[] =
{
  ssr1_stop_cycle_timer,
  ssr2_stop_cycle_timer,
  ssr3_stop_cycle_timer,
  ssr4_stop_cycle_timer
};

void setup() {
  com_interfaces.config_uart(true);
  // Do some initial hardware configuration set-up
  uc_resources.ptr_ssr_outputs->config_ac_io_pins();
  uc_resources.ptr_opto_outputs->config_dc_io_pins();
  uc_resources.ptr_blue_push_button->config_input_io_pins();
  uc_resources.ptr_red_latch_button->config_input_io_pins();
  uc_resources.ptr_ds1820b->config_temp_probe();
  uc_resources.ptr_ds1307->update_system_time();
  uc_resources.ptr_ds1307->set_master_alarm_enable(uc_resources.ptr_ds1307->read_master_alarm_enable_eeprom());
  uc_resources.ptr_ds1307->update_all_alarms_from_eeprom();
  init_alarms();
  com_interfaces.handle_connection();
}

void loop() {
  ts.execute();
  Alarm.delay(0);
}

// === Task Scheduler functions =======================================
void handle_system_time_drift()
{
  uc_resources.ptr_ds1307->update_system_time();
}

void handle_input_io() {
  uc_resources.ptr_blue_push_button->run_input_io_fsm();
  uc_resources.ptr_red_latch_button->run_input_io_fsm();
}

void handle_analog_input()
{
  uc_resources.ptr_ch0_probe->read_probe();
  uc_resources.ptr_ch1_probe->read_probe();
}

// temperature probe tasks
void handle_temp_conv_start()
{
  uc_resources.ptr_ds1820b->start_temp_conv();
  t_handle_temp_conv_start.disable();
  //prepare task status
  st_temp_probe.setWaiting();
  t_handle_temp_reading.waitFor(&st_temp_probe);
  t_handle_temp_conv_wait.enableDelayed(PERIOD_TEMPERATURE * TASK_MILLISECOND);
}

void handle_temp_conv_wait()
{
  st_temp_probe.signalComplete();
}

void handle_temp_reading()
{
  uc_resources.ptr_ds1820b->read_temp();
  t_handle_temp_conv_wait.restart();
  t_handle_temp_conv_start.restart();
}

// opto pulse tasks
void handle_pulse_start() 
{
  uc_resources.ptr_opto_outputs->start_all_opto_pulses();
  t_handle_pulse_start.disable();
  //prepare task status
  st_opto_pulse.setWaiting();
  t_handle_pulse_end.waitFor(&st_opto_pulse);

  t_handle_pulse_wait.enableDelayed(PERIOD_PULSE * TASK_MILLISECOND);
}

void handle_pulse_wait()
{
  st_opto_pulse.signalComplete();
}

void handle_pulse_end()
{
  uc_resources.ptr_opto_outputs->end_all_opto_pulses();
  t_handle_pulse_wait.restart();
  t_handle_pulse_start.restart();
}

void handle_uart_rx() {
  com_interfaces.get_serial_packet();
}

void handle_udp_rx() {
  com_interfaces.get_udp_packet();
}

void handle_connection() {
  com_interfaces.handle_connection();
}

void handle_config_alarm()
{
  if (t_handle_config_alarm.isFirstIteration())
  {
    if(!uc_resources.ptr_red_latch_button->read_instant_state())
      com_interfaces.config_all_expected_outputs();
    else
      uc_resources.ptr_ds1307->set_master_alarm_enable(false);   
  }
  else
  {
    if(!uc_resources.ptr_red_latch_button->get_determined_input_state())
    {
      if(uc_resources.ptr_blue_push_button->get_alarm_trigger_count() > 0)
      {
        uc_resources.ptr_blue_push_button->reset_alarm_trigger_count();
        com_interfaces.config_all_expected_outputs();
        uc_resources.ptr_ds1307->set_master_alarm_enable(true);
      }
    }
    else
    {
      if(uc_resources.ptr_blue_push_button->get_alarm_trigger_count() > 0)
      {
        uc_resources.ptr_blue_push_button->reset_alarm_trigger_count();
        uc_resources.ptr_ssr_outputs->set_all_ssr_outputs(false);
        uc_resources.ptr_ds1307->set_master_alarm_enable(false);
      }      
    }
  }
}

// === Alarm functions =======================================
void init_alarms()
{
  for (int i = 0; i < 4; i++) {
    uc_resources.ptr_ds1307->init_all_alarms(i+1, ssrx_on_callbacks[i], ssrx_off_callbacks[i], ssrx_start_cycle_timer_callbacks[i]);
  }
}

void start_cycle(int output)
{
  if (uc_resources.ptr_ds1307->get_master_alarm_enable())
    {
      uc_resources.ptr_ssr_outputs->set_ssrx_output(output,true);
      uc_resources.ptr_ds1307->init_timer(ssrx_stop_cycle_timer_callbacks[output-1], output, false);
    }
}

void stop_cycle(int output)
{
  if (uc_resources.ptr_ds1307->get_master_alarm_enable())
    uc_resources.ptr_ssr_outputs->set_ssrx_output(output,false);
}

void execute_ssr_alarm_action(int output, bool state)
{
  if (uc_resources.ptr_ds1307->get_master_alarm_enable())
    uc_resources.ptr_ssr_outputs->set_ssrx_output(output,state);   
}

void ssr1_on_alarm(){execute_ssr_alarm_action(1,true);}
void ssr2_on_alarm(){execute_ssr_alarm_action(2,true);}
void ssr3_on_alarm(){execute_ssr_alarm_action(3,true);}
void ssr4_on_alarm(){execute_ssr_alarm_action(4,true);}

void ssr1_off_alarm(){execute_ssr_alarm_action(1,false);}
void ssr2_off_alarm(){execute_ssr_alarm_action(2,false);}
void ssr3_off_alarm(){execute_ssr_alarm_action(3,false);}
void ssr4_off_alarm(){execute_ssr_alarm_action(4,false);}

void ssr1_start_cycle_timer() {start_cycle(1);}
void ssr2_start_cycle_timer() {start_cycle(2);}
void ssr3_start_cycle_timer() {start_cycle(3);}
void ssr4_start_cycle_timer() {start_cycle(4);}

void ssr1_stop_cycle_timer() {stop_cycle(1);}
void ssr2_stop_cycle_timer() {stop_cycle(2);}
void ssr3_stop_cycle_timer() {stop_cycle(3);}
void ssr4_stop_cycle_timer() {stop_cycle(4);}