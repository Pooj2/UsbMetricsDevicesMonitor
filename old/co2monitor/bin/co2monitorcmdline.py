#!/usr/bin/env python

import sys
import co2monitor

if __name__ == "__main__":
    co2monitor = co2monitor.Co2Monitor(sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "True") == "True")
    co2monitor.run()
