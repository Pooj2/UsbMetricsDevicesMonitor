'''
Created on Jun 1, 2020

@author: joop
'''
import logging


class UsbDevice:
    '''
    An usb device with metrics.
    '''
    _VID = 0x0
    _PID = 0x0
    logger = logging.getLogger('UsbDevice')
    
    def __init__(self, params):
        '''
        Constructor
        '''
        
    def verbose(self, line):
        if self.isVerbose:
            self.logger.info(line)
