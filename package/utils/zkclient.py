"""
zkclient.py  ─  Backward Compatibility Bridge
==============================================
This file exists ONLY for backward compatibility.
All existing thread files import ZkClient and ZkHelper from here.

The real implementation lives in:
    package/services/vendors/zkteco/zk_manager.py

DO NOT add new logic here. Import from zk_manager directly in new code.
"""

from package.services.vendors.zkteco.zk_manager import ZkClient, ZkHelper

__all__ = ["ZkClient", "ZkHelper"]
