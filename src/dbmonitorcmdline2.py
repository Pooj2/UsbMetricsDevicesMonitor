#!/usr/bin/env python3

import sys
from usbdevice.gm1356.amgaze4 import Amgaze4
import usb.core

if __name__ == "__main__":
    dev = usb.core.find(idVendor=Amgaze4._VID, idProduct=Amgaze4._PID)
    assert dev is not None
    print(dev._str())
    co2monitor = Amgaze4(dev, (sys.argv[1] if len(sys.argv) > 1 else "True") == "True")
    co2monitor.run()
