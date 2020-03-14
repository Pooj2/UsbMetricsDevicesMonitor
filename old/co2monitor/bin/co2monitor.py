#!/usr/bin/env python

# based on code by henryk ploetz
# https://hackaday.io/project/5301-reverse-engineering-a-low-cost-usb-co-monitor/log/17909-all-your-base-are-belong-to-us


import sys, fcntl
from multiprocessing import Value

class Co2Monitor:
    def __init__(self, hidRawdDevice, verbose=False, temperature=Value('d', 0.0), co2ppm=Value('i', 0)):
        self.hidRawdDevice = hidRawdDevice
        self.isVerbose = verbose
        self.temperature = temperature
        self.co2ppm = co2ppm

    @classmethod
    def connect(cls, hidRawdDevice, temperature, co2ppm):
        return cls(hidRawdDevice, False, temperature, co2ppm)

    def get_temperature(self):
        return self.temperature

    def get_co2ppm(self):
        return self.co2ppm

    def decrypt(self, key,  data):
        cstate = [0x48,  0x74,  0x65,  0x6D,  0x70,  0x39,  0x39,  0x65]
        shuffle = [2, 4, 0, 7, 1, 6, 5, 3]

        phase1 = [0] * 8
        for i, o in enumerate(shuffle):
            phase1[o] = data[i]

        phase2 = [0] * 8
        for i in range(8):
            phase2[i] = phase1[i] ^ key[i]

        phase3 = [0] * 8
        for i in range(8):
            phase3[i] = ( (phase2[i] >> 3) | (phase2[ (i-1+8)%8 ] << 5) ) & 0xff

        ctmp = [0] * 8
        for i in range(8):
            ctmp[i] = ( (cstate[i] >> 4) | (cstate[i]<<4) ) & 0xff

        out = [0] * 8
        for i in range(8):
            out[i] = (0x100 + phase3[i] - ctmp[i]) & 0xff

        return out

    def hd(self, d):
        return " ".join("%02X" % e for e in d)

    def verbose(self, line):
        if self.isVerbose:
            print line,

    def run(self):
        # Key retrieved from /dev/random, guaranteed to be random ;)
        key = [0xc4, 0xc6, 0xc0, 0x92, 0x40, 0x23, 0xdc, 0x96]

        fp = open(self.hidRawdDevice, "a+b",  0)

        HIDIOCSFEATURE_9 = 0xC0094806
        set_report = "\x00" + "".join(chr(e) for e in key)
        fcntl.ioctl(fp, HIDIOCSFEATURE_9, set_report)

        values = {}

        while True:
            data = list(ord(e) for e in fp.read(8))
            decrypted = self.decrypt(key, data)
            if decrypted[4] != 0x0d or (sum(decrypted[:3]) & 0xff) != decrypted[3]:
                print self.hd(data), " => ", self.hd(decrypted),  "Checksum error", self.hidRawdDevice
            else:
                op = decrypted[0]
                val = decrypted[1] << 8 | decrypted[2]
            
                values[op] = val
            
                # Output all data, mark just received value with asterisk
                self.verbose(", ".join( "%s%02X: %04X %5i" % ([" ", "*"][op==k], k, v, v) for (k, v) in sorted(values.items())))
                self.verbose("  ") 
                ## From http://co2meters.com/Documentation/AppNotes/AN146-RAD-0401-serial-communication.pdf
                if 0x50 in values:
                    self.co2ppm.value = values[0x50]
                    self.verbose("CO2: %4i" % self.co2ppm.value)
                if 0x42 in values:
                    self.temperature.value = values[0x42]/16.0-273.15
                    self.verbose("T: %2.2f" % self.temperature.value)
                if 0x44 in values:
                    self.verbose("RH: %2.2f" % (values[0x44]/100.0))
                self.verbose("\n")

