import os,json
from main import DATA_DIR



class ConfigHelper:

    appName = "Biometric Attendance Software"
    appAuthor = "Mozzine Technologies"
    
    def __init__(self, config_file='config.json'):

        # Project Root
        self.config_file = os.path.join(DATA_DIR, config_file)

        # Create the config file if it doesn't exist
        if not os.path.exists(self.config_file):
            with open(self.config_file, 'w') as file:
                json.dump({
                    "deviceIPs" : ["192.168.1.201"],
                    "schoolURL" : "",
                    "baseURL" : "",
                    "apiKey" : "",
                    "campusId" : "",
                    "schoolName" : "Demo School ",
                    "providerName" : "",
                    "providerEmail" : "",
                    "providerWebsite" : "",
                    "biometricTarget" : "",
                    "isBiometricEnabled" : True,
                }, file)
    
    def write_config(self, key, value):
        # Writes a configuration to the file.
        data = self._read_all()
        data[key] = value
        with open(self.config_file, 'w') as file:
            json.dump(data, file, indent=4)
    

    def update_configs(self, updates):
        # Updates multiple configurations at once.
        if not isinstance(updates, dict):
            raise ValueError("Updates must be a dictionary of key-value pairs.")
        data = self._read_all()
        data.update(updates)  # Update multiple key-value pairs
        with open(self.config_file, 'w') as file:
            json.dump(data, file, indent=4)
    
    def read_config(self, key, default=None):
        # Reads a configuration value.
        data = self._read_all()
        return data.get(key, default)
    

    def delete_config(self, key):
        # Deletes a configuration by key.
        data = self._read_all()
        if key in data:
            del data[key]
            with open(self.config_file, 'w') as file:
                json.dump(data, file, indent=4)

    def _read_all(self):
        # Reads all configurations from the file.
        with open(self.config_file, 'r') as file:
            return json.load(file)
        
    def list_configs(self):
        # Lists all configuration keys.
        data = self._read_all()
        return list(data.keys())
