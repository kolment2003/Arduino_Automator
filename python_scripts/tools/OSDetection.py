# general libraries
from enum import Enum
from sys import platform as _platform

OSType = Enum('InterfaceType', 'windows linux osx unrecognized')


class OSDetection:
    """
    Class to help detect system os
    """
    @staticmethod
    def get_os_type():
        if _platform == "linux" or _platform == "linux2":
            detected_os = OSType.linux
        elif _platform == "win32":
            detected_os = OSType.windows
        elif _platform == "darwin":
            detected_os = OSType.osx
        else:
            detected_os = OSType.unrecognized
        return detected_os
