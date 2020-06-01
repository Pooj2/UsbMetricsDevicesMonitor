#!/usr/bin/env python3
# https://towardsdatascience.com/build-your-own-python-restful-web-service-840ed7766832

from usbdevice.co2monitor.co2monitor import Co2Monitor
from usbdevice.gm1356.amgaze4 import Amgaze4
from multiprocessing import Process, Value
import logging.config
import cherrypy
import usb.core


class UsbMonitorConnector:
    pass


class Co2MonitorConnector(UsbMonitorConnector):

    def __init__(self, device):
        self.device = device
        self.temperature = Value('d', 0.0)
        self.co2ppm = Value('i', 0)

    def connect(self, temperature, co2ppm):
        usbDevice = Co2Monitor.connect(self.device, temperature, co2ppm)
        usbDevice.run()


class DbMonitorConnector(UsbMonitorConnector):

    def __init__(self, device):
        self.device = device
        self.db = Value('d', 0.0)

    def connect(self, db):
        usbDevice = Amgaze4.connect(self.device, db)
        usbDevice.run()


class MyWebService(object):

    def __init__(self, co2MonitorConnections, dbMonitorConnections):
        self.co2MonitorConnections = co2MonitorConnections
        self.dbMonitorConnections = dbMonitorConnections

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def temperature(self, monitor): 
        output = { 
                  'data': self.co2MonitorConnections[int(monitor)].temperature.value
                 }
        return output

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def co2ppm(self, monitor):
        output = { 
                  'data': self.co2MonitorConnections[int(monitor)].co2ppm.value
                 }
        return output

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def db(self, monitor):
        output = { 
                  'data': self.dbMonitorConnections[int(monitor)].db.value
                 }
        return output

  
if __name__ == '__main__':
    logging.config.fileConfig('logging.conf', disable_existing_loggers=False)
    logger = logging.getLogger('usbMetricsDevicesMonitor')

    usbMonitorProcesses = []

    devices = tuple(usb.core.find(find_all=True, idVendor=Co2Monitor._VID, idProduct=Co2Monitor._PID))
    co2MonitorConnections = []
    for device in devices:
        logger.info("Co2Device", device.bus, device.address)
        co2MonitorConnections.append(Co2MonitorConnector(device))
        
    for connection in co2MonitorConnections:
        usbMonitorProcesses.append(Process(target=connection.connect, args=(connection.temperature, connection.co2ppm)))

    devices = tuple(usb.core.find(find_all=True, idVendor=Amgaze4._VID, idProduct=Amgaze4._PID))
    dbMonitorConnections = []
    for device in devices:
        logger.info("DbDevice", device.bus, device.address)
        dbMonitorConnections.append(DbMonitorConnector(device))
        
    for connection in dbMonitorConnections:
        usbMonitorProcesses.append(Process(target=connection.connect, args=(connection.db)))

    for process in usbMonitorProcesses:
        process.start()

    config = {'server.socket_host': '0.0.0.0',
              'server.socket_port': 8090,
              'log.screen': False,
              'log.access_file': ''}
    cherrypy.config.update(config)
    cherrypy.quickstart(MyWebService(co2MonitorConnections, dbMonitorConnections))
