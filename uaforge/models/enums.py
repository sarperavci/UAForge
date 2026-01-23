from enum import Enum, unique


@unique
class DeviceType(str, Enum):
    DESKTOP = "desktop"
    MOBILE = "mobile"
    TABLET = "tablet"


@unique
class OSType(str, Enum):
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    ANDROID = "android"
    IOS = "ios"
    CHROME_OS = "cros"
    UNKNOWN = "unknown"


@unique
class BrowserFamily(str, Enum):
    CHROME = "chrome"
    FIREFOX = "firefox"
    SAFARI = "safari"
    EDGE = "edge"
    OPERA = "opera"
    UNKNOWN = "unknown"


@unique
class EngineType(str, Enum):
    BLINK = "Blink"       # Chrome, Edge, Opera
    GECKO = "Gecko"       # Firefox
    WEBKIT = "WebKit"     # Safari
    TRIDENT = "Trident"   # IE
