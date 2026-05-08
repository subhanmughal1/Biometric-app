"""
Backward compatibility shim.
The real MainWindow is now in package/views/mainwindow.py (MVC architecture).
This file re-exports it so any old import paths keep working.
"""
from package.views.mainwindow import MainWindow

__all__ = ["MainWindow"]
