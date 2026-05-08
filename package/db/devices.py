from package.utils.db import DbHelper

class DevicesModel(DbHelper):    
    tblName = 'devices'

    def __init__(self, debug=False):
        self.tableName = self.tblName
        super().__init__('', debug)


    def add_device(self, name, ipaddress,vendor='',  port='', serial_number=''):
        # check if ipaddress already exist
        if(self.records('*', f"ipaddress='{ipaddress}'",None,True) > 0):
            return None 
        # add a new record
        data = {
            'name': name,
            'ipaddress': ipaddress,
            'port': port,
            'vendor': vendor,
            'serial_number': serial_number
        }
        return self.add(data)


    def save_device(self, rid, name='', ipaddress='', port='', serial_number=''):
        # Update existing record
        data = {}        
        if name: data['name'] = name
        if ipaddress: data['ipaddress'] = ipaddress
        if port: data['port'] = port
        if serial_number: data['serial_number'] = serial_number

        self.save(rid,data)
