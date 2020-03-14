# Protocol https://github.com/dobra-noc/gm1356/blob/master/PROTOCOL.md
# Adressing the device https://github.com/dobra-noc/gm1356/blob/master/lib/gm1356/device.rb
# pyusb https://www.youtube.com/watch?v=xfhzbw93rzw
#       https://github.com/pyusb/pyusb/blob/master/docs/tutorial.rst
#       and google...
#
# Joop 2020-02-08
#
import usb.core
import time
import random
import array
import binascii
import numpy

""" 
Explanation of bits in data[3] field :
Settings have this structure: 
  [unused:1bit][slow/fast mode:1bit][max mode:1bit][a/c filter:1bit] - 4 bits
  0x000000 : bit 64 : x = 1 -> Fast ; x = 0 -> Slow
  00x00000 : bit 32 : x = 1 -> Max lock on ; x = 0 -> Max lock off
  000x0000 : bit 16 : x = 1 -> dB C ; x = 0 -> dB A 
  00000xxx : xxx = 0 ; Range 30 - 130
  00000xxx : xxx = 1 ; Range 30 - 80
  00000xxx : xxx = 2 ; Range 50 - 100
  00000xxx : xxx = 3 ; Range 60 - 110
  00000xxx : xxx = 4 ; Range 80 - 130


a, not max, fast  |   0x04

"""
GM1356_SPLMETER_VID =       0x64bd
GM1356_SPLMETER_PID =       0x74e3

GM1356_FAST_MODE    =       0x40
GM1356_HOLD_MAX_MODE=       0x20
GM1356_NO_MAX_MODE  = ~numpy.uint8(GM1356_HOLD_MAX_MODE);
GM1356_MEASURE_DBC  =       0x10
GM1356_MEASURE_DBA  = ~numpy.uint8(GM1356_MEASURE_DBC);

GM1356_RANGE_30_130_DB=     0x00
GM1356_RANGE_30_80_DB =     0x01
GM1356_RANGE_50_100_DB=     0x02
GM1356_RANGE_60_110_DB=     0x03
GM1356_RANGE_80_130_DB=     0x04

GM1356_FLAGS_RANGE_MASK=0x0f

GM1356_COMMAND_CAPTURE  =0xb3
GM1356_COMMAND_CONFIGURE=0x56

def get_units(value):
    """ Return dB units """

    if value & GM1356_MEASURE_DBC:
        return 'dB C'
    else:
        return 'dB A'

max_lock = 0
def get_max_lock(value):
    """ Return if Max lock is on or off.
        NOTE: when Max lock is only the max is returned from the device.
    """

    if value & GM1356_HOLD_MAX_MODE:
        return 'Max lock on'
    else:
        return 'Max lock off'

def get_speed(value):
    """ Return if the capturing speed is fast (no filtering) or slow (filtered) """
    if value & GM1356_FAST_MODE:
        return 'Fast'
    else:
        return 'Slow'

RANGES = [ '30 - 130',
           '30 - 80',
           '50 - 100',
           '60 - 110',
           '80 - 130' ]
def get_range(value):
    """ Return the range for under or over limit message """
    range = value & GM1356_FLAGS_RANGE_MASK
    try:
        range_string = RANGES[range]
    except IndexError:
        range_string = 'UNKNOWN(' + range + ')'

    return range_string

def get_dB(value1, value2):
    """ Calculate the dB value out of two bytes information """
    dB = value1 << 8 | value2
    return dB/10.0

STATE_REQUEST = array.array('B', [GM1356_COMMAND_CAPTURE, 0x00, 0x00, 0x00,
                                                    0x00, 0x00, 0x00, 0x00])
def spl_read():
    global settings
    data = array.array('B', [0x00, 0x00, 0x00, 0x00,
                             0x00, 0x00, 0x00, 0x00])
    while True:
        time.sleep(0.5)
        spl_write(STATE_REQUEST)
        try:
            read = epin.read(data, 1000)
            if read == 8:
                break
        except usb.core.USBError as e:
            if e.args == ('Operation timed out',):
                 print('TIMEOUT')
                 continue

    print(binascii.hexlify(data))
    print('      db:', get_dB(data[0], data[1]))

    settings = data[2]
    print('   units: ', get_units(data[2]))
    print('   speed:', get_speed(data[2]))
    print('max_lock: ', get_max_lock(data[2]))
    print('   range: ', get_range(data[2]))

def set_config():
    print("INFO configure...")
    cmd = [GM1356_COMMAND_CONFIGURE, settings, 0x00, 0x00,
              0x00, 0x00, 0x00, 0x00]
    spl_write(cmd)

def spl_write(cmd):
    #print("INFO writing end point address...")
    written = epout.write(cmd)
    #print('written:', written)
    assert written == len(cmd)

print("INFO set configuration done.")
dev = usb.core.find(idVendor=GM1356_SPLMETER_VID, idProduct=GM1356_SPLMETER_PID)
assert dev is not None
print(dev)
print("INFO done print dev")

#cfg = dev.get_active_configuration()
#interface_number = cfg[(0, 0)].bInterfaceNumber
interface_number = 0

print("INFO dev reset...")
dev.reset()
print("INFO dev reset done.")

if dev.is_kernel_driver_active(interface_number):
    print("INFO kernel driver active.")
    print("INFO detach kernel driver...")
    dev.detach_kernel_driver(interface_number)
    print("INFO detach kernel driver done.")

# set the active configuration. With no arguments, the first
# configuration will be the active one
#print("INFO set configuration...")
#dev.set_configuration()
#print("INFO set configuration done.")

# get an endpoint instance
cfg = dev.get_active_configuration()
print('cfg:', cfg)
intf = cfg[(0,0)]
epin = usb.util.find_descriptor(
        intf,
        custom_match = 
        lambda e: 
            usb.util.endpoint_direction(e.bEndpointAddress) == 
            usb.util.ENDPOINT_IN)

assert epin is not None

epout = usb.util.find_descriptor(
        intf,
        custom_match = 
        lambda e: 
            usb.util.endpoint_direction(e.bEndpointAddress) == 
            usb.util.ENDPOINT_OUT)

assert epout is not None

usb.util.claim_interface(dev, interface_number)

settings = 0x00
settings |= GM1356_FAST_MODE
settings &= GM1356_NO_MAX_MODE
settings &= GM1356_MEASURE_DBA
set_config()

collected = 0
attempts = 50
#while collected < attempts:
while True:
    spl_read()
    collected += 1
    if (settings & GM1356_HOLD_MAX_MODE or
        settings & GM1356_MEASURE_DBC):
        settings &= GM1356_NO_MAX_MODE
        settings &= GM1356_MEASURE_DBA
        set_config()

# Fin.
