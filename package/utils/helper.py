import os,sys
import requests
from pathlib import Path
from PyQt6 import QtCore
from PyQt6.QtWidgets import QMessageBox
from package.utils.logger import Logger
from main import DATA_DIR


class Helper():

    # restart the app   
    @staticmethod
    def restart():
        QtCore.QCoreApplication.quit()
        QtCore.QProcess.startDetached(sys.executable, sys.argv)

    # download an image and save into a a directory   
    @staticmethod
    def download_image(url, file_name, save_dir=None, reDownload=False):
        try:
            if not url or not file_name:
                return None
            if save_dir is None:
                save_dir = os.path.join(DATA_DIR, "downloads")
            # Create the directory if it doesn't exist
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)

            # Construct the full file path
            file_path = os.path.join(save_dir, file_name)

            # Check if the file already exists BEFORE making a network request
            if not reDownload and os.path.exists(file_path):
                return file_path  # Return the path of the existing file

            # Defensive: avoid directory traversal or odd filenames
            file_name = os.path.basename(str(file_name))
            file_path = os.path.join(save_dir, file_name)

            # Send a GET request to the URL
            response = requests.get(url, stream=True, timeout=(5, 30))
            response.raise_for_status()  # Raise an error for bad status codes

            content_type = (response.headers.get("Content-Type") or "").lower()
            if content_type and not content_type.startswith("image/"):
                Logger.error(f"Failed to download image: non-image content-type '{content_type}' url={url}")
                return None

            tmp_path = file_path + ".tmp"
            bytes_written = 0
            with open(tmp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    f.write(chunk)
                    bytes_written += len(chunk)

            if bytes_written <= 0:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
                Logger.error(f"Failed to download image: empty response url={url}")
                return None

            try:
                os.replace(tmp_path, file_path)
            except Exception:
                # Fallback if replace fails for any reason
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    os.rename(tmp_path, file_path)
                except Exception as e:
                    Logger.error(f"Failed to download image: unable to move tmp file into place: {e}")
                    return None

            Logger.info(f"Image successfully downloaded: {file_path}")
            return file_path
        except requests.exceptions.RequestException as e:
            Logger.error(f"Failed to download image: {e}")
            return None

class Alert():
    # restart the app   
    @staticmethod 
    def show(self,message="",title="Info",icon=QMessageBox.Icon.Information):
        # Create a QMessageBox
        msg_box = QMessageBox(self)
        msg_box.setIcon(icon)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        # Adjust size
        msg_box.setGeometry(0, 0, 600, 300)  # Set width to 400 and height to 200

        # Center the QMessageBox relative to the main window
        main_geometry = self.geometry()
        main_center = main_geometry.center()
        msg_box_geometry = msg_box.frameGeometry()
        msg_box_geometry.moveCenter(main_center)
        msg_box.move(msg_box_geometry.topLeft())

        msg_box.exec()