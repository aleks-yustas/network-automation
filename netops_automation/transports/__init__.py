from netops_automation.transports.ftp import FtpTransport
from netops_automation.transports.telnet import TelnetTransport
from netops_automation.transports.tftp import TftpTransport

TRANSPORTS = {
    "ftp": FtpTransport,
    "telnet": TelnetTransport,
    "tftp": TftpTransport,
}

