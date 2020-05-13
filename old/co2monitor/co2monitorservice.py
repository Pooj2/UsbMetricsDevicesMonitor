#!/usr/bin/env python
# https://towardsdatascience.com/build-your-own-python-restful-web-service-840ed7766832

import cherrypy
import co2monitor
from multiprocessing import Process, Value

class Co2MonitorConnector:
    def __init__(self, hidRawdDevice):
        self.hidRawdDevice = hidRawdDevice
        self.temperature = Value('d', 0.0)
        self.co2ppm = Value('i', 0)

    def connect(self, temperature, co2ppm):
        co2monitorconn = co2monitor.Co2Monitor.connect(self.hidRawdDevice, temperature, co2ppm)
        co2monitorconn.run()

class MyWebService(object):

    def __init__(self, co2monitor_connections):
        self.co2monitor_connections = co2monitor_connections

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def temperature(self, monitor):
        output = { 
                  'data': self.co2monitor_connections[int(monitor)].temperature.value
                 }
        return output

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def co2ppm(self, monitor):
        output = { 
                  'data': self.co2monitor_connections[int(monitor)].co2ppm.value
                 }
        return output
  
if __name__ == '__main__':
    co2monitor_connections = [ Co2MonitorConnector("/dev/hidraw0"),
                               Co2MonitorConnector("/dev/hidraw1") ]
    co2monitor_processes = []
    for connection in co2monitor_connections:
        co2monitor_processes.append(Process(target=connection.connect, args=(connection.temperature, connection.co2ppm)))

    for process in co2monitor_processes:
        process.start()

    config = {'server.socket_host': '0.0.0.0',
              'server.socket_port': 8090,
              'log.screen': False,
              'log.access_file': ''}
    cherrypy.config.update(config)
    cherrypy.quickstart(MyWebService(co2monitor_connections))
