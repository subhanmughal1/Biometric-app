from posixpath import exists
from PyQt6 import QtCore
from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot, QMutex
from package.utils.zkclient import ZkHelper,ZkClient
from package.utils.logger import Logger
from package.utils.api import APIHelper
from package.utils.helper import Helper


# //////////////////////////////////////////////////////////////////////////////////////////////////
# data cleaning 
# //////////////////////////////////////////////////////////////////////////////////////////////////

class DataCleaningWorker(QThread):

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
                if client.clearData():
                    self.progress.emit('All data removed from the device.','green')
                else:
                    self.progress.emit('Device not responding.','red')
            else:
                self.progress.emit('select a device first.','red')

        except Exception as e:
            Logger.error(f"{self.ipAddress}: Data cleaning thread error: {e}")
            self.error.emit("Data cleaning is not working properly")
        finally:            
            self.finished.emit()

class DataCleaningManager:
    def __init__(self,ref,ipAddress=None):
        self.ref = ref
        self.thread = None
        self.is_running = False
        self.ipAddress = ipAddress
        
    def start(self,ipAddress=None):
        self.ipAddress=ipAddress
        if self.is_running:
            return
        self.thread = DataCleaningWorker(ipAddress=ipAddress)
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
# data sync 
# //////////////////////////////////////////////////////////////////////////////////////////////////

class DataSyncWorker(QThread):

    # Signal to communicate with the main thread
    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(str,str)

    def __init__(self,ipAddress=None,type=''):
        super().__init__()
        self.type = type
        self.ipAddress = ipAddress

    def _to_int_uid(self, value):
        try:
            if value is None:
                return None
            v = str(value).strip()
            if v == "":
                return None
            i = int(v)
            return i if i > 0 else None
        except Exception:
            return None
    
    def _to_str_id(self, value):
        if value is None:
            return ""
        return str(value).strip()

    def run(self):        
        client = None
        device_disabled = False
        try:
            if self.isInterruptionRequested():
                return
            client =  ZkClient(ipaddress=self.ipAddress)

            if not client.isConnected:
                self.progress.emit('select a device first.','red')
                return
            
            # disable interaction
            try:
                client.conn.disable_device() 
                device_disabled = True
            except Exception as e:
                # not fatal, but good to know
                self.progress.emit(f"Warning: could not disable device - {str(e)}","yellow")
            
            if self.isInterruptionRequested():
                return

            apiHelper = APIHelper()
            currentUsers = client.getUsers() or []
            existing_uids = set()
            existing_user_ids = set()
            for cu in currentUsers:
                if self.isInterruptionRequested():
                    return
                cu_uid = self._to_int_uid(getattr(cu,'uid',None))
                if cu_uid:
                    existing_uids.add(cu_uid)
                
                cu_user_id = self._to_str_id(getattr(cu, "user_id", None))
                if cu_user_id:
                    existing_user_ids.add(cu_user_id)    

            users = apiHelper.loadUsers(type=self.type) or []
            if self.isInterruptionRequested():
                return
            
            if not users:
                self.progress.emit(f"No users found in the portal.","red")
                return

            total = 0
            added = 0
            skipped_existing = 0
            skipped_invalid = 0
            failed = 0

            for user in users:
                if self.isInterruptionRequested():
                    break

                total += 1
                uid = self._to_int_uid(getattr(user,"bioId",None))

                if not uid:
                    skipped_invalid += 1
                    self.progress.emit(f"Skipped user (invalid UID): {getattr(user,'label','')}", "orange")
                    continue
                
                uid_str = str(uid)

                # Skip if already present by either uid or user_id
                if (uid in existing_uids) or (uid_str in existing_user_ids):
                    skipped_existing += 1
                    continue

                
                name = str(getattr(user, 'label', '') or '')
                if len(name) > 24:
                    name = name[:24]
                
                ok = False
                try:
                    ok = client.saveUser(uid,name)
                except Exception as e:
                    Logger.error(f"{self.ipAddress}: saveUser error uid={uid} name='{name}': {e}")

                if ok:
                    added += 1
                    existing_uids.add(uid)      # prevent duplicates in same run
                    self.progress.emit(f"{getattr(user,'label','User')} saved successfully", "green")
                else:
                    failed += 1
                    self.progress.emit(f"Unable to save {getattr(user,'label','User')} [uid:{uid}]", "red")


                if self.isInterruptionRequested():
                    break
                
                # Download image only when relevant (or keep if you want always)
                try:
                    if user.imageLink:
                        Helper.download_image(user.imageLink, user.image)
                except Exception as e:
                    Logger.error(f"{self.ipAddress}: image download failed uid={uid}: {e}")

            if not self.isInterruptionRequested():
                if added == 0 and failed == 0 and skipped_existing > 0 :
                    self.progress.emit("Data is already synchronized.", "blue")
                else:
                    self.progress.emit(
                        f"Sync done — Total:{total}, Added:{added}, Existing:{skipped_existing}, Invalid:{skipped_invalid}, Failed:{failed}",
                        "blue"
                    )

        except Exception as e:
            Logger.error(f"{self.ipAddress}: Data sync thread error: {e}")
            self.error.emit(f"Data sync is not working properly. Double check your institute URL and API key.")
        finally:   
            # Re-enable device if we disabled it
            if client and device_disabled:
                try:
                    client.conn.enable_device()
                except Exception:
                    pass         
            
            # Close/disconnect client if supported
            if client:
                for m in ("disconnect", "close", "logout"):
                    fn = getattr(client, m, None)
                    if callable(fn):
                        try:
                            fn()
                            break
                        except Exception:
                            pass
            self.finished.emit()

class DataSyncManager:
    def __init__(self,ref,ipAddress=None):
        self.ref = ref
        self.thread = None
        self.is_running = False
        self.ipAddress = ipAddress
        
    def start(self,ipAddress=None,type=''):
        self.ipAddress=ipAddress
        if self.is_running:
            return
        self.thread = DataSyncWorker(ipAddress=ipAddress,type=type)
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

