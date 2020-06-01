#!/usr/bin/env python3

import sys
from usbdevice.co2monitor.co2monitor import Co2Monitor
import usb.core

if __name__ == "__main__":
    dev = usb.core.find(idVendor=Co2Monitor._VID, idProduct=Co2Monitor._PID)
    assert dev is not None
    print(dev._str())
    co2monitor = Co2Monitor(dev, (sys.argv[1] if len(sys.argv) > 1 else "True") == "True")
    co2monitor.run()