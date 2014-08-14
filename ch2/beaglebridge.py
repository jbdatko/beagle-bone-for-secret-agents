# The code is free and can be used for any purpose including
# commercial purposes.  Packt Publishing and the authors can not be
# held liable for any use or result of the book's text or code.
# Further copyright & license info is found in the book's Copyright
# page.  The book can be obtained from
# "https://www.packtpub.com/hardware-and-creative/beaglebone-secret-agents".

from stem.control import Controller, EventType
import Adafruit_BBIO.GPIO as GPIO
import Adafruit_BBIO.ADC as ADC
import Adafruit_BBIO.UART as UART
import serial
import threading
from time import sleep
from math import ceil, floor
import Queue
import sys

def Mbits_2_bytes(Mbps):
  return Mbps * 1024 * 1024 / 8


def str_bytes_2_Mbytes(num):
  'Takes Bytes as a string and returns Mega Bytes as a string'
  return str(int(num) / (1024 * 1024))


class SpeedTest(object):
  '''Class for parsing the output of speedtest_cli'''

  def __init__(self, test_file):
    with open(test_file, 'r') as f:
      for line in f:
        if 'Download' in line:
          # Units are in MBps
          self.down = float(line.split()[1])
        if 'Upload' in line:
          # Units are in MBps
          self.up = float(line.split()[1])

  def get_down(self):
    return Mbits_2_bytes(self.down)

  def get_up_Bps(self):
    return Mbits_2_bytes(self.up)

  def get_tenth(self, val, val_max):
    '''Return the ratio of the bandwidth to the whole number'''
    return ceil((val * 10) / val_max)

  def get_down_ratio(self, val):
    return self.get_tenth(val, self.get_down())

  def get_up_ratio(self, val):
    return self.get_tenth(val, self.get_up_Bps())


class TorFreedomLED(object):
  def __init__(self):
    self.pin = 'P9_15'
    GPIO.setup(self.pin, GPIO.OUT)

  def on(self):
    GPIO.output(self.pin, GPIO.HIGH)

  def off(self):
    GPIO.output(self.pin, GPIO.LOW)

  def blink(self):
    self.on()
    sleep(.5)
    self.off()


class FrontPanelDisplay(object):

  block_char = '\xFF'
  rows = 16
  clear_command = '\x01'

  def __init__(self):
    self.uart = 'UART4'
    UART.setup(self.uart)
    self.port = serial.Serial(port="/dev/ttyO4", baudrate=9600)
    self.port.open()

  def reset_cursor(self):
    self.port.write('\xFE')
    self.port.write('\x80')

  def clear_screen(self):
    self.reset_cursor()
    blank_line = ' ' * self.rows
    self.port.write(self.clear_command)
    self.reset_cursor()

  def write(self, data):
    self.clear_screen()
    out = str(data)[:32]
    self.port.write(out)

  def fill_screen(self):
    self.clear_screen()
    blocks = self.block_char * self.rows
    self.port.write(blocks)
    self.port.write(blocks)

  def display_graph(self, up, down):
    self.clear_screen()
    up_str = '{0:<16}'.format('Up:   ' + self.block_char * up)
    dn_str = '{0:<16}'.format('Down: ' + self.block_char * down)

    self.port.write(up_str)
    self.port.write(dn_str)

  def display_rates(self, rate, burst):
    self.clear_screen()
    rate_str = '{0:<16}'.format('Rate:  ' + rate + "KBps")
    burs_str = '{0:<16}'.format('Burst: ' + burst + "KBps")
    self.port.write(rate_str)
    self.port.write(burs_str)
    sleep(5)

  def splash(self, bytes_read, bytes_written, num_ckts, finger):
    self.clear_screen()
    hello_str = '{0:<16}'.format('Controller Init')
    read_str = '{0:<16}'.format('MBs Down:    ' + bytes_read)
    writ_str = '{0:<16}'.format('MBs Up  : ' + bytes_written)
    num_ckts_str = '{0:<16}'.format('Num Ckts: ' + str(num_ckts))
    fingerprint_str = "Finger: " + finger[:24]

    # Fun animation
    self.port.write(hello_str)
    self.port.write('....')
    sleep(2)
    self.port.write('....')
    sleep(2)
    self.port.write('....')
    sleep(2)
    self.port.write('....')
    sleep(2)
    self.port.write(read_str)
    self.port.write(writ_str)
    sleep(10)
    self.port.write(num_ckts_str)
    sleep(5)
    # Display the last 24 characters of the bridge's fingerprint
    self.clear_screen()
    self.port.write(fingerprint_str)
    sleep(5)

def make_bw_callback(test):
  def print_bw(event):
    'Callback to print the instantaneous Bytes per second usage'
    up = int(test.get_up_ratio(event.written))
    down = int(test.get_down_ratio(event.read))
    lcd.display_graph(up, down)

  return print_bw

def make_conf_callback(lcd):
  def conf_changed(event):
    'Callback to print the new bandwidth rates'
    rate = str(int(event.config['RelayBandwidthRate']) / 1024)
    burst = str(int(event.config['RelayBandwidthBurst']) / 1024)
    lcd.display_rates(rate, burst)

  return conf_changed


class BeagleBridge(object):

  def __init__(self, rate, lcd):

    self.controller = Controller.from_port()
    self.controller.authenticate()

    self.fingerprint = self.controller.get_info('fingerprint')
    self.rate = rate
    self.controller.set_conf('SocksPort', '9050')
    self.lcd = lcd

  def add_listeners(self):
    self.listeners = list()
    self.listeners.append((make_bw_callback(self.rate), EventType.BW))
    self.listeners.append((make_conf_callback(self.lcd), EventType.CONF_CHANGED))

    for listener in self.listeners:
      self.controller.add_event_listener(listener[0], listener[1])

  def shutdown(self):
    for listener in self.listeners:
      self.controller.remove_event_listener(listener[0])

  def get_read_written(self):
    bytes_read = self.controller.get_info("traffic/read")
    bytes_written = self.controller.get_info("traffic/written")

    return bytes_read, bytes_written

  def get_ckts(self):
    return len(self.controller.get_circuits())

  def set_rate_and_burst(self, speed):
    rate = str(int(floor(speed))) + "KB"
    try:
      rates = {'RelayBandwidthRate': rate, 'RelayBandwidthBurst': rate}
      self.controller.set_options(rates)
    except:
      print "setting rates failed"
      exit(1)

  def update_rate(self, val_0_thru_10):

    if val_0_thru_10 <= 0:
      return None

    rate = float(val_0_thru_10 / 10) * self.rate.get_up_Bps() / 1024
    self.set_rate_and_burst(rate)


class BandwidthKnob(threading.Thread):

  def __init__(self, pin, *args, **kwargs):

    threading.Thread.__init__(self, *args, **kwargs)
    self.pin = pin
    self.setup_adc()
    self.kill = False
    self.prev_value = -1
    self.q = Queue.Queue()

  def setup_adc(self):
    'Load the Adafruit device tree fragment for ADC pins'
    ADC.setup()

  def read_value(self):
    return ceil(10 * ADC.read(self.pin))

  def stop(self):
    self.kill = True

  def run(self):
    knob = self.prev_value

    while knob != 0 and not self.kill:
      sleep(1)
      knob = self.read_value()
      if knob != self.prev_value:
        self.q.put(knob)
        self.prev_value = knob



if __name__ == '__main__':

  if len(sys.argv) < 1:
    print "Usage: " + sys.argv[0] + " speed_test_results.txt"
    exit(1)

  test = SpeedTest(sys.argv[1])
  led = TorFreedomLED()
  lcd = FrontPanelDisplay()

  lcd.clear_screen()
  lcd.fill_screen()

  bb = BeagleBridge(test, lcd)

  read, written = bb.get_read_written()

  lcd.splash(str_bytes_2_Mbytes(read),
             str_bytes_2_Mbytes(written),
             bb.get_ckts(),
             bb.fingerprint)

  # Add the listeners here as to not interrupt the splash sequence
  bb.add_listeners()

  knob = BandwidthKnob("AIN5")
  knob.start()

  level = knob.q.get()

  while 0 != level:
    try:
      level = knob.q.get(timeout=10)
    except Queue.Empty:
      # Time Reached, allow main thread some execution and then go
      # back to waiting
      led.blink()
    else:
      bb.update_rate(level)

  bb.shutdown()
  knob.stop()
  lcd.fill_screen()

  try:
    knob.join()
  except KeyboardInterrupt:
    exit(0)
