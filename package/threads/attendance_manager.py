import os
import time
from datetime import datetime
from PyQt6.QtCore import Qt,QThread, pyqtSignal, pyqtSlot, QMutex
from PyQt6.QtGui import QPixmap
from package.utils.zkclient import ZkHelper,ZkClient
from package.utils.logger import Logger
from package.utils.api import APIHelper
from package.config import ConfigHelper
from package.utils.helper import Helper
from package.utils.user import User
from main import DATA_DIR


# //////////////////////////////////////////////////////////////////////////////////////////////////
# attendance cleaning 
# //////////////////////////////////////////////////////////////////////////////////////////////////

class AttendanceCleaningWorker(QThread):

    # Signal to communicate with the main thread
    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(str,str)

    def __init__(self,ipAddress=None):
        super().__init__()
        self.ipAddress = ipAddress

    def run(self):        
        try:
            client =  ZkClient(ipaddress=self.ipAddress,timeout=90)
            if client.isConnected: 
                if client.clearAttendance():
                    self.progress.emit('Attendance log cleared from the device.','green')
                else:
                    self.progress.emit('Device not responding.','red')
            else:
                self.progress.emit('select a device first.','red')

        except Exception as e:
            Logger.error(f"{self.ipAddress}: Attendance log cleaning thread error: {e}")
            self.error.emit("Attendance log cleaning is not working properly")
        finally:            
            self.finished.emit()

class AttendanceCleaningManager:
    def __init__(self,ref,ipAddress=None):
        self.ref = ref
        self.thread = None
        self.is_running = False
        self.ipAddress = ipAddress
        
    def start(self,ipAddress=None):
        self.ipAddress=ipAddress
        if self.is_running:
            return
        self.thread = AttendanceCleaningWorker(ipAddress=ipAddress)
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
        
    def on_thread_progress(self,message='',color=''):
        self.postDeviceLog(message,color)
        
    def on_thread_error(self,message=''):
        self.postDeviceLog(message,'red')
        
    # post a log in the device options
    def postDeviceLog(self,text='',color=''):
        prefix = None if not self.ipAddress else f"{format(self.ipAddress)}: "
        if not color:
            if prefix:
                self.ref.textBrowserSelectedDeviceLog.append(prefix)
            self.ref.textBrowserSelectedDeviceLog.append(str(text))
        else:
            if prefix:
                self.ref.textBrowserSelectedDeviceLog.append('<span style="color:'+str(color)+';">'+prefix+'</span>')
            self.ref.textBrowserSelectedDeviceLog.append('<span style="color:'+str(color)+';">'+str(text)+'</span>')


# //////////////////////////////////////////////////////////////////////////////////////////////////
# attendance posting 
# //////////////////////////////////////////////////////////////////////////////////////////////////

class AttendancePostingWorker(QThread):

    # Signal to communicate with the main thread
    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(str,str)

    def __init__(self,clients=None):
        super().__init__()
        self.clients = clients     
        self.is_biometric_enabled = True        
        self.apiHelper = APIHelper()
        self.appConfig = ConfigHelper()
        self.postedCheckIns ={}
        self.postedCheckOuts ={}
        self.postedOvertimeIns ={}
        self.postedOvertimeOuts ={}

        # last posted timestamp per (ip, user_id, punch, date)
        self.last_posted = {}
        
    def isTodayRecord(self,dt_object):
        return dt_object.date() == datetime.today().date()
    
    def isPostableCheckin(self,record):
        key = f"cin_{str(record.user_id)}"
        if key in self.postedCheckIns:
            return False
        else:
            return self.isTodayRecord(record.timestamp)
        
    def isPostableCheckout(self,record):
        key = f"cout_{str(record.user_id)}"
        if key in self.postedCheckOuts:
            return False
        else:
            return self.isTodayRecord(record.timestamp)

    def isPostableOvertimeIn(self,record):
        key = f"otin_{str(record.user_id)}"
        if key in self.postedOvertimeIns:
            return False
        else:
            return self.isTodayRecord(record.timestamp)

    def isPostableOvertimeOut(self,record):
        key = f"otout_{str(record.user_id)}"
        if key in self.postedOvertimeOuts:
            return False
        else:
            return self.isTodayRecord(record.timestamp)

    def _key(self, ip, record):
        day = record.timestamp.date().isoformat()
        return (str(ip), str(record.user_id), int(record.punch), day)

    def run(self): 
        # retry mechanism
        loopCount=0
        sleepTime=15
        maxLoopCount=500
        while not self.isInterruptionRequested():
            try:
                
                if not self.appConfig.read_config('isBiometricEnabled'):
                    self.error.emit("Biometric attendance is not enabled in portal")
                else:
                    if self.clients:
                        for ipaddress in self.clients:
                            client =  ZkClient(ipaddress=ipaddress,timeout=60)
                            if client.isConnected: 
                                posted_records = 0
                                failed_records = 0
                                # a large timeout is mandatory to read a lot of records
                                clt =  ZkClient(ipaddress=ipaddress,timeout=90)
                                data = clt.getDateAttendance() or []
                                if data:
                                    for row in data: 
                                        
                                        if self.isInterruptionRequested():
                                            break
                                        # process checkin log
                                        if row.punch==0:
                                            if (self.isPostableCheckin(row)):
                                                if self.apiHelper.postAttendance(row,'checkin'):
                                                    self.postedCheckIns[f"cin_{str(row.user_id)}"] =  row.timestamp
                                                    posted_records += 1
                                                else:
                                                    failed_records += 1
                                        # process checkout log
                                        if row.punch==1:
                                            if (self.isPostableCheckout(row)):
                                                if self.apiHelper.postAttendance(row,'checkout'):
                                                    self.postedCheckOuts[f"cout_{str(row.user_id)}"] =  row.timestamp
                                                    posted_records += 1
                                                else:
                                                    failed_records += 1
                                        # process overtime in
                                        if row.punch==4:
                                            if (self.isPostableOvertimeIn(row)):
                                                if self.apiHelper.postAttendance(row,'overtimein'):
                                                    self.postedOvertimeIns[f"otin_{str(row.user_id)}"] =  row.timestamp
                                                    posted_records += 1
                                                else:
                                                    failed_records += 1
                                        # process overtime out
                                        if row.punch==5:
                                            if (self.isPostableOvertimeOut(row)):
                                                if self.apiHelper.postAttendance(row,'overtimeout'):
                                                    self.postedOvertimeOuts[f"otout_{str(row.user_id)}"] =  row.timestamp
                                                    posted_records += 1
                                                else:
                                                    failed_records += 1

                                    if posted_records > 0: 
                                        self.progress.emit(f"{ipaddress}: {str(posted_records)} record(s) synchronized with portal...",'blue')

                                    if failed_records > 0: 
                                        self.progress.emit(f"{ipaddress}: {str(failed_records)} record(s) are failed to synchronize with portal...",'red')
                            else:
                                self.progress.emit(f"{ipaddress} is not responding while posting attendance records",'orange')

            except Exception as e:
                Logger.error(f"{ipaddress or ''}: Attendance posting thread error: {e}")
                self.error.emit("Attendance posting is not working properly")
            finally:      
                loopCount += 1   
                # wait before next iteration
                time.sleep(sleepTime) 
                # reset after maxLoopCount iterations
                if(loopCount>maxLoopCount):
                    loopCount=0
                    self.postedCheckIns ={}
                    self.postedCheckOuts ={}
                    self.postedOvertimeIns ={}
                    self.postedOvertimeOuts ={}

class AttendancePostingManager:
    def __init__(self,ref):
        self.ref = ref
        self.thread = None
        self.is_running = False

        
    def start(self):
        clients = self.ref.clients
        if self.is_running:
            return
        self.thread = AttendancePostingWorker(clients=clients)
        self.thread.finished.connect(self.on_thread_finished)
        self.thread.progress.connect(self.on_thread_progress)
        self.thread.error.connect(self.on_thread_error)
        self.thread.start()
        self.is_running = True
        
    def stop(self):
        if self.thread is not None and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()
            self.is_running = False
        
    def on_thread_finished(self):
        self.is_running = False
        
    def on_thread_progress(self,message='',color=''):
        self.postDeviceLog(message,color)
        
    def on_thread_error(self,message=''):
        self.postDeviceLog(message,'red')
        
    # post a log in the device options
    def postDeviceLog(self,text='',color=''):
        if not color:
            self.ref.connectionActivityBrowser.append(str(text))
        else:
            self.ref.connectionActivityBrowser.append('<span style="color:'+str(color)+';">'+str(text)+'</span>')



# //////////////////////////////////////////////////////////////////////////////////////////////////
# live attendance 
# //////////////////////////////////////////////////////////////////////////////////////////////////

class LiveAttendanceWorker(QThread):

    # Signal to communicate with the main thread
    finished = pyqtSignal()
    error = pyqtSignal(str)
    capture = pyqtSignal(User)
    progress = pyqtSignal(str,str)

    def __init__(self,ipaddress=None):
        super().__init__()
        self.ipaddress = ipaddress             
        self.apiHelper = APIHelper()

    def run(self): 
        while not self.isInterruptionRequested():
            try:
                client =  ZkClient(ipaddress=self.ipaddress)
                if client.isConnected: 
                    for attendance in client.conn.live_capture(10):
                        if self.isInterruptionRequested():
                            break
                        if attendance is None:
                            time.sleep(1)
                        else:
                            data = self.apiHelper.loadUser(attendance.user_id)
                            if not data:
                                self.progress.emit(f"[UID:{attendance.user_id}] record not found",'orange')
                            else:
                                # download the image if not already exist in the directory
                                if data.imageLink and data.image:
                                    Helper.download_image(data.imageLink, data.image)
                                self.capture.emit(User(
                                    id=data.id or '',
                                    name=data.name or '',
                                    fatherName=data.fatherName or '',
                                    computerNumber=data.computerNumber or '',
                                    image=data.image or '',
                                    fee=data.fee or '',
                                    pay=data.pay or '',
                                    note=data.note or '',
                                    type=data.type or '',
                                    balance=data.balance or ''
                                ))
                else:
                    self.progress.emit(f"{self.ipaddress} is not responding",'orange')
            except Exception as e:
                Logger.error(f"{self.ipaddress}: Live Attendance thread error: {e}")
                self.error.emit("Live Attendance is not working properly")
            finally:                            
                for _ in range(5):
                    if self.isInterruptionRequested():
                        break
                    time.sleep(1) # wait before next iteration

class LiveAttendanceManager:
    def __init__(self,ref):
        self.ref = ref
        self.threads = {}
        self.is_running = False

        
    def start(self):
        clients = self.ref.clients
        if self.is_running:
            return
        i=0
        for ipaddress in clients:
            self.threads[i]=LiveAttendanceWorker(ipaddress=ipaddress)
            self.threads[i].finished.connect(self.on_thread_finished)
            self.threads[i].progress.connect(self.on_thread_progress)
            self.threads[i].capture.connect(self.on_attendance_capture)
            self.threads[i].error.connect(self.on_thread_error)
            self.threads[i].start()
            self.is_running = True
            i += 1
        
    def stop(self):
        for thread in self.threads.values():
            if thread is not None and thread.isRunning():
                thread.requestInterruption()
                thread.wait()
        self.threads = {}
        self.is_running = False
        
    def on_thread_finished(self):
        self.is_running = False
        
    def on_thread_progress(self,message='',color=''):
        self.postDeviceLog(message,color)
        
    def on_thread_error(self,message=''):
        self.postDeviceLog(message,'red')
        
    def on_attendance_capture(self,user):
        try:
            image_path = os.path.join(DATA_DIR, "downloads", user.image)
            self.ref.userName.setText(str(user.name))
            self.ref.userFatherName.setText(str(user.fatherName))
            self.ref.userComputerNo.setText(str(user.computerNumber))
            self.ref.userType.setText(str(user.type))
            self.ref.userFee.setText(str(user.fee))
            self.ref.userBalance.setText(str(user.balance))
            self.ref.specialNoteLabel.setText(user.note)
            self.display_image(image_path)            
        except Exception as e:
            Logger.error(f"Live attendance UI update error: {e}")
        
    # post a log in the device options
    def postDeviceLog(self,text='',color=''):
        if not color:
            self.ref.connectionActivityBrowser.append(str(text))
        else:
            self.ref.connectionActivityBrowser.append('<span style="color:'+str(color)+';">'+str(text)+'</span>')

    def display_image(self, path):
        if os.path.exists(path):
            pixmap = QPixmap(path)
            if pixmap.isNull():
                Logger.error(f"Live attendance image load failed (null pixmap): {path}")
                self.ref.userImageLabel.clear()
                self.ref.userImageLabel.setText("Image not found")
                return
            self.ref.userImageLabel.setPixmap(pixmap.scaled(
                self.ref.userImageLabel.width(),
                self.ref.userImageLabel.height(),
                Qt.AspectRatioMode.KeepAspectRatio
            ))
        else:
            self.ref.userImageLabel.clear()
            self.ref.userImageLabel.setText("Image not found")

