
from PyQt6 import QtCore
from package.utils.zkclient import ZkHelper
from package.utils.network import Network
from package.utils.logger import Logger

class NetworkThread(QtCore.QThread):
    stop_signal = QtCore.pyqtSignal()
    t_signal = QtCore.pyqtSignal(str,str)
    error_signal = QtCore.pyqtSignal(str)
    gateway_signal = QtCore.pyqtSignal(str)
    gateway_ip_signal = QtCore.pyqtSignal(str)
    device_signal = QtCore.pyqtSignal(str,str)

    network_devices=[]
    zk_devices=[]
    gateway_ip=None
    interface=None
    network_range=None



    def __init__(self, parent=None, index=0):
        super().__init__(parent)
        self.index = index
        self.is_running = False

    def run(self):
        self.is_running = True
        try:

            # search the gateway ip
            # self.gateway_ip, self.interface, self.network_range = self.get_default_gateway()
            self.gateway_ip = Network.get_default_gateway_ip()
            # print(self.gateway_ip)
            if self.isInterruptionRequested():
                return

            if self.gateway_ip:
                self.gateway_ip_signal.emit(self.gateway_ip)
                self.network_devices = Network.scan()
                if self.isInterruptionRequested():
                    return
                self.validate_zk_devices()
                self.stop_signal.emit()

        except Exception as e:
            Logger.error(f"Network scanning error: {format(e)}")
            self.error_signal.emit(f"Network scanning error: {format(e)}")


    def stop(self):
        self.is_running = False
        self.requestInterruption()

    # Separate ZKTeco devices
    def validate_zk_devices(self):
        # reset zk devices to blank
        self.zk_devices=[]

        # Test each discovered IP
        for ip in self.network_devices:
            if self.isInterruptionRequested():
                break
            device_type='Generic'
            if ZkHelper.isZkDevice(ip)==True:
                device_type = 'ZK'            
            self.zk_devices.append({'ip': str(ip),'type': str(device_type)})
            self.device_signal.emit(str(ip),str(device_type))

        
