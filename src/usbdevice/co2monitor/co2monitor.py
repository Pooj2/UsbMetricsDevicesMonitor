#!/usr/bin/env python

# based on code by henryk ploetz
# https://hackaday.io/project/5301-reverse-engineering-a-low-cost-usb-co-monitor/log/17909-all-your-base-are-belong-to-us

from multiprocessing import Value
from usbdevice.usbDevice import UsbDevice
import usb.core
import array
import logging


class Co2Monitor(UsbDevice):
    _VID = 0x04d9
    _PID = 0xa052
    logger = logging.getLogger('Co2Monitor')

    def __init__(self, device, verbose=False, temperature=Value('d', 0.0), co2ppm=Value('i', 0)):
        self.device = device
        self.isVerbose = verbose
        self.temperature = temperature
        self.co2ppm = co2ppm

    @classmethod
    def connect(cls, device, temperature, co2ppm):
        return cls(device, False, temperature, co2ppm)

    def get_temperature(self):
        return self.temperature

    def get_co2ppm(self):
        return self.co2ppm

    def decrypt(self, key, data):
        cstate = [0x48, 0x74, 0x65, 0x6D, 0x70, 0x39, 0x39, 0x65]
        shuffle = [2, 4, 0, 7, 1, 6, 5, 3]

        phase1 = [0] * 8
        for i, o in enumerate(shuffle):
            phase1[o] = data[i]

        phase2 = [0] * 8
        for i in range(8):
            phase2[i] = phase1[i] ^ key[i]

        phase3 = [0] * 8
        for i in range(8):
            phase3[i] = ((phase2[i] >> 3) | (phase2[ (i - 1 + 8) % 8 ] << 5)) & 0xff

        ctmp = [0] * 8
        for i in range(8):
            ctmp[i] = ((cstate[i] >> 4) | (cstate[i] << 4)) & 0xff

        out = [0] * 8
        for i in range(8):
            out[i] = (0x100 + phase3[i] - ctmp[i]) & 0xff

        return out

    def hd(self, d):
        return " ".join("%02X" % e for e in d)

    def verbose(self, line):
        if self.isVerbose:
            self.logger.info(line)

    def run(self):
        dev = self.device
        self.logger.info("dev reset...")
        dev.reset()
        self.logger.info("dev reset done.")

        interface_number = 0
        if dev.is_kernel_driver_active(interface_number):
            self.logger.info("kernel driver active.")
            self.logger.info("detach kernel driver...")
            dev.detach_kernel_driver(interface_number)
            self.logger.info("detach kernel driver done.")

        # get an endpoint instance
        cfg = dev.get_active_configuration()
        self.logger.info('cfg: %s', cfg)
        intf = cfg[(0, 0)]
        epin = usb.util.find_descriptor(
        intf,
        custom_match=
        lambda e: 
            usb.util.endpoint_direction(e.bEndpointAddress) == 
            usb.util.ENDPOINT_IN)

        assert epin is not None

        usb.util.claim_interface(dev, interface_number)

        # Key retrieved from /dev/random, guaranteed to be random ;)
        # key = [0xc4, 0xc6, 0xc0, 0x92, 0x40, 0x23, 0xdc, 0x96]
        key = array.array('B', [0xe2, 0xe5, 0xe2, 0xdb,
                                0xe6, 0xa8, 0xe6, 0xdf])

        # #fp = open(self.device, "a+b",  0)

        # #HIDIOCSFEATURE_9 = 0xC0094806
        # #set_report = "\x00" + "".join(chr(e) for e in key)
        # #fcntl.ioctl(fp, HIDIOCSFEATURE_9, set_report)
        self.logger.info("ctrl_transfer...")

        result = dev.ctrl_transfer(0x21, 0x09, wValue=0x0300, wIndex=0x00, data_or_wLength=key)
        self.logger.info("ctrl_transfer done, result: %s", result)

        values = {}
        while True:
            # #data = list(ord(e) for e in fp.read(8))
            try:
                data = epin.read(8, timeout=5000)
            except usb.core.USBError as e:
                if e.args == (110, 'Operation timed out'):
                    self.logger.warn("TIMEOUT")
                    continue
            decrypted = self.decrypt(key, data)
            if decrypted[4] != 0x0d or (sum(decrypted[:3]) & 0xff) != decrypted[3]:
                self.logger.error("%s => %s Checksum error %s", self.hd(data), self.hd(decrypted), self.device._str())
            else:
                op = decrypted[0]
                val = decrypted[1] << 8 | decrypted[2]
            
                values[op] = val
            
                # Output all data, mark just received value with asterisk
                line = ", ".join("%s%02X: %04X %5i" % ([" ", "*"][op == k], k, v, v) for (k, v) in sorted(values.items()))
                line = line + "  " 
                # # From http://co2meters.com/Documentation/AppNotes/AN146-RAD-0401-serial-communication.pdf
                if 0x50 in values:
                    self.co2ppm.value = values[0x50]
                    line = line + ("CO2: %4i" % self.co2ppm.value)
                if 0x42 in values:
                    self.temperature.value = values[0x42] / 16.0 - 273.15
                    line = line + ("T: %2.2f" % self.temperature.value)
                if 0x44 in values:
                    line = line + ("RH: %2.2f" % (values[0x44] / 100.0))
                self.verbose(line)
