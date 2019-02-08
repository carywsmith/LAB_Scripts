import fcntl
import os
import subprocess
# Equivalent of the _IO('U', 20) constant in the linux kernel.
USBDEVFS_RESET = ord('U') << (4 * 2) | 20

def get_sinistro_usb():
    """
    Gets the devfs path to a Sinistro USB by scraping the output of the lsusb command

    The lsusb command outputs a list of USB devices attached to a computer
    in the format:
        Bus 002 Device 009: ID 16c0:0483 Van Ooijen Technische Informatica Teensyduino Serial
    The devfs path to these devices is:
        /dev/bus/usb/<busnum>/<devnum>
    So for the above device, it would be:
        /dev/bus/usb/002/009
    This function generates that path.
    """

    proc = subprocess.Popen(['lsusb'], stdout=subprocess.PIPE)
    out = proc.communicate()[0]
    lines = out.split(b'\n')
    for line in lines:
        if (b'Cypress Semiconductor Corp.') in line:
            parts = line.split()
            bus = parts[1]
            dev = parts[3][:3]
            return '/dev/bus/usb/%s/%s' % (str(bus, 'utf-8'), str(dev, 'utf-8'))


def send_reset(dev_path):
    """
        Sends the USBDEVFS_RESET IOCTL to a USB device.

        dev_path - The devfs path to the USB device (under /dev/bus/usb/)
                    See get_sinistro_usb for example of how to obtain this.
    """
    fd = os.open(dev_path, os.O_WRONLY)
    try:
        fcntl.ioctl(fd, USBDEVFS_RESET, 0)
    finally:
        os.close(fd)


def reset_sinistro_usb():
    send_reset(get_sinistro_usb())
