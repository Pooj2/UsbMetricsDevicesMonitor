# UsbMetricsDevicesMonitor
USB Metrics Devices Monitor

## Credit where credit is due.
All the code here was initially grabbed from the internet by google searches. I've mentioned some of the original authors, but in the long error-search-trail-repeat hours I've certainly lost some of the original authors names. 

Please file an issue when I didn't give you credit.

## Usb Metrics Devices Monitor goals
Usb Metrics Devices Monitor UMDM goals are:
* on a Raspberry Pi
* run a REST service
* in Python with
** PyUSB
* that collects metrics 
* from USB devices like
** a 04d9:a052 TFA Dostmann CO2 Monitor
** a 64bd:74e3 Amgaze GM1356 Digital Sound Level Meter
* that measure some quantity

## Notes

### Create system user
TODO: modifiy for the new service

```bash
sudo addgroup co2monitor
sudo adduser --system --group co2monitor co2monitor
#sudo usermod -g co2monitor co2monitor
id co2monitor

sudo su - co2monitor -s /bin/bash
```

### Service start
TODO: modifiy for the new service

```bash
sudo systemctl enable co2monitor
sudo systemctl status co2monitor
sudo systemctl --now start co2monitor
```

### Tests
TODO: modifiy for the new service

```bash
curl -s -N --connect-timeout 20 --max-time 30 http://localhost:8090/co2ppm?monitor=0
{"data": 807}
curl -s -N --connect-timeout 20 --max-time 30 http://localhost:8090/temperature?monitor=0
{"data": 21.912500000000023}
```