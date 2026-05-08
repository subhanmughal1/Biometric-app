import time
from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot
from package.utils.zkclient import ZkClient
from package.utils.logger import Logger


# //////////////////////////////////////////////////////////////////////////////////////////////////
# connection checking 
# //////////////////////////////////////////////////////////////////////////////////////////////////

class ConnectionWorker(QThread):

    # Signal to communicate with the main thread
    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(str,str)

    def __init__(self,clients=None):
        super().__init__()
        self.clients = clients

    def run(self): 
        while not self.isInterruptionRequested():    
            try:
                if self.clients:
                    connections = ""
                    for ipaddress in self.clients:
                        client =  ZkClient(ipaddress=ipaddress,timeout=3)
                        if client.isConnected: 
                            connections = f"{connections} | {ipaddress}"
                    if connections:
                        self.progress.emit(f"Connected clients {connections}", "green")
                    else:
                        self.progress.emit("No connected clients", "red")
            except Exception as e:
                Logger.error(f"Connectetion checking thread error: {e}")
                # self.error.emit("Attendance posting is not working properly")
            finally:            
                # interruptible sleep (so stop responds quickly)
                for _ in range(10):
                    if self.isInterruptionRequested():
                        break
                    time.sleep(1)                

class ConnectionManager:
    def __init__(self,ref):
        self.ref = ref
        self.thread = None
        self.is_running = False

        
    def start(self):
        clients = self.ref.clients
        if self.is_running:
            return
        self.thread = ConnectionWorker(clients=clients)
        self.thread.finished.connect(self.on_thread_finished)
        self.thread.progress.connect(self.on_thread_progress)
        self.thread.error.connect(self.on_thread_error)
        self.thread.start()
        self.is_running = True
        
    def stop(self):
        if self.thread is not None and self.thread.isRunning():
            self.thread.requestInterruption()
            self.thread.wait()
            self.is_running = False
        
    def on_thread_finished(self):
        self.is_running = False
        
    def on_thread_progress(self,text=''):
        self.ref.connectionStatus.setText(text)
        self.ref.connectionStatus.setStyleSheet("background-color: rgb(0, 0, 0);font: 9pt 'Fixedsys';color: rgb(0, 255, 0);")
        
    def on_thread_error(self,text=''):
        self.ref.connectionStatus.setText(text)
        self.ref.connectionStatus.setStyleSheet("background-color: rgb(0, 0, 0);font: 9pt 'Fixedsys';color: rgb(255, 255, 0);")