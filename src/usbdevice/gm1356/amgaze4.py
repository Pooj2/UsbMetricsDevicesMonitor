# Protocol https://github.com/dobra-noc/gm1356/blob/master/PROTOCOL.md
# Adressing the device https://github.com/dobra-noc/gm1356/blob/master/lib/gm1356/device.rb
# pyusb https://www.youtube.com/watch?v=xfhzbw93rzw
#       https://github.com/pyusb/pyusb/blob/master/docs/tutorial.rst
#       and google...
#
# Joop 2020-02-08
#
from multiprocessing import Value
import usb.core
import time
import array
import binascii
import numpy
import logging
from usbdevice.usbDevice import UsbDevice


class Amgaze4(UsbDevice):
    _VID = 0x64bd
    _PID = 0x74e3
    logger = logging.getLogger('Amgaze4')

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
    GM1356_FAST_MODE = 0x40
    GM1356_HOLD_MAX_MODE = 0x20
    GM1356_NO_MAX_MODE = ~numpy.uint8(GM1356_HOLD_MAX_MODE);
    GM1356_MEASURE_DBC = 0x10
    GM1356_MEASURE_DBA = ~numpy.uint8(GM1356_MEASURE_DBC);
    
    GM1356_RANGE_30_130_DB = 0x00
    GM1356_RANGE_30_80_DB = 0x01
    GM1356_RANGE_50_100_DB = 0x02
    GM1356_RANGE_60_110_DB = 0x03
    GM1356_RANGE_80_130_DB = 0x04
    
    GM1356_FLAGS_RANGE_MASK = 0x0f
    
    GM1356_COMMAND_CAPTURE = 0xb3
    GM1356_COMMAND_CONFIGURE = 0x56

    def __init__(self, device, verbose=False, db=Value('d', 0.0)):
        self.device = device
        self.isVerbose = verbose
        self.db = db

    @classmethod
    def connect(cls, device, db):
        return cls(device, False, db)

    def get_temperature(self):
        return self.temperature
    
    def get_units(self, value):
        """ Return dB units """
    
        if value & self.GM1356_MEASURE_DBC:
            return 'dB C'
        else:
            return 'dB A'
    
    max_lock = 0
    
    def get_max_lock(self, value):
        """ Return if Max lock is on or off.
            NOTE: when Max lock is only the max is returned from the device.
        """
    
        if value & self.GM1356_HOLD_MAX_MODE:
            return 'Max lock on'
        else:
            return 'Max lock off'
    
    def get_speed(self, value):
        """ Return if the capturing speed is fast (no filtering) or slow (filtered) """
        if value & self.GM1356_FAST_MODE:
            return 'Fast'
        else:
            return 'Slow'
    
    RANGES = [ '30 - 130',
               '30 - 80',
               '50 - 100',
               '60 - 110',
               '80 - 130' ]
    
    def get_range(self, value):
        """ Return the range for under or over limit message """
        aRange = value & self.GM1356_FLAGS_RANGE_MASK
        try:
            range_string = self.RANGES[aRange]
        except IndexError:
            range_string = 'UNKNOWN(' + str(aRange) + ')'
    
        return range_string
    
    def get_dB(self, value1, value2):
        """ Calculate the dB value out of two bytes information """
        dB = value1 << 8 | value2
        return dB / 10.0
    
    STATE_REQUEST = array.array('B', [GM1356_COMMAND_CAPTURE, 0x00, 0x00, 0x00,
                                                        0x00, 0x00, 0x00, 0x00])
    
    def spl_read(self):
        data = array.array('B', [0x00, 0x00, 0x00, 0x00,
                                 0x00, 0x00, 0x00, 0x00])
        while True:
            time.sleep(0.5)
            self.spl_write(self.STATE_REQUEST)
            try:
                read = self.epin.read(data, 1000)
                if read == 8:
                    break
            except usb.core.USBError as e:
                if e.args == ('Operation timed out',):
                    self.logger.warn('TIMEOUT')
                    continue
    
        self.verbose('     raw: ' + binascii.hexlify(data))
        self.db.value = self.get_dB(data[0], data[1])
        self.verbose('      db: ' + str(self.db.value))
        self.settings = data[2]
        
        self.verbose('   units: ' + str(self.get_units(data[2])))
        self.verbose('   speed: ' + str(self.get_speed(data[2])))
        self.verbose('max_lock: ' + str(self.get_max_lock(data[2])))
        self.verbose('   range: ' + str(self.get_range(data[2])))
    
    def set_config(self):
        self.logger.info("configure...")
        cmd = [self.GM1356_COMMAND_CONFIGURE, self.settings, 0x00, 0x00,
                  0x00, 0x00, 0x00, 0x00]
        self.spl_write(cmd)
    
    def spl_write(self, cmd):
        # self.logger.info("writing end point address...")
        written = self.epout.write(cmd)
        # self.logger.debug('written:', written)
        assert written == len(cmd)
        
    def run(self):
        dev = self.device
        assert dev is not None
        self.logger.debug(dev)
        self.logger.info("done print dev")
        
        # cfg = dev.get_active_configuration()
        # interface_number = cfg[(0, 0)].bInterfaceNumber
        interface_number = 0
        
        self.logger.info("dev reset...")
        dev.reset()
        self.logger.info("dev reset done.")
        
        if dev.is_kernel_driver_active(interface_number):
            self.logger.info("kernel driver active.")
            self.logger.info("detach kernel driver...")
            dev.detach_kernel_driver(interface_number)
            self.logger.info("detach kernel driver done.")
        
        # set the active configuration. With no arguments, the first
        # configuration will be the active one
        # self.logger.info("set configuration...")
        # dev.set_configuration()
        # self.logger.info("set configuration done.")
        
        # get an endpoint instance
        cfg = dev.get_active_configuration()
        self.logger.debug('cfg: %s', cfg)
        intf = cfg[(0, 0)]
        self.epin = usb.util.find_descriptor(
                intf,
                custom_match=
                lambda e: 
                    usb.util.endpoint_direction(e.bEndpointAddress) == 
                    usb.util.ENDPOINT_IN)
        
        assert self.epin is not None
        
        self.epout = usb.util.find_descriptor(
                intf,
                custom_match=
                lambda e: 
                    usb.util.endpoint_direction(e.bEndpointAddress) == 
                    usb.util.ENDPOINT_OUT)
        
        assert self.epout is not None
        
        usb.util.claim_interface(dev, interface_number)
        
        self.settings = 0x00
        self.settings |= self.GM1356_FAST_MODE
        self.settings &= self.GM1356_NO_MAX_MODE
        self.settings &= self.GM1356_MEASURE_DBA
        self.set_config()
        
        collected = 0
        while True:
            self.spl_read()
            collected += 1
            if (self.settings & self.GM1356_HOLD_MAX_MODE or
                self.settings & self.GM1356_MEASURE_DBC):
                self.settings &= self.GM1356_NO_MAX_MODE
                self.settings &= self.GM1356_MEASURE_DBA
                self.set_config()
        
        # Fin.
