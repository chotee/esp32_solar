import utime
import machine
import network

authfile = "auth.txt"

led_pin = machine.Pin(5, machine.Pin.OUT)
sta_if = network.WLAN(network.STA_IF)
config = {}


def setup():
    print("Setup Starting")
    config["ess_id"], config["ess_pass"] = read_auth()
    sta_if.active(True)


def main():
    print("Main Starting")
    operative = False
    while True:  # Main repetitive loop.
        while not system_operative():
            prepare_loop()
        if not operative:
            operative_setup()
            operative = True
        operative_loop()


def operative_setup():
    print("System Now Operative.")


def prepare_loop():
    """
    The loop that gets called when the system is not yet ready
    """
    if config["ess_id"]:
        print("Connecting to '%s' with password" % config["ess_id"])
        sta_if.connect(config["ess_id"], config["ess_pass"])
    led_pin.value(1)
    utime.sleep_ms(150)
    led_pin.value(0)
    utime.sleep_ms(150)


def operative_loop():
    """
    The normal work loop
    """
    led_pin.value(1)
    utime.sleep_ms(500)
    led_pin.value(0)
    utime.sleep_ms(500)


def system_operative():
    """
    Returns True if the system is ready to do it's normal operation
    :return: True if working, False otherwise.
    :rtype: bool
    """
    if not sta_if.isconnected():
        return False
    return True


def read_auth():
    ess_id = None
    ess_pass = None
    try:
        fd = open(authfile, 'r')
        ess_id = fd.readline()[:-1]
        ess_pass = fd.readline()[:-1]
        fd.close()
    except OSError as exc:
        print("Failed to read '%s': '%s'" % (authfile, exc))
    return ess_id, ess_pass


setup()
main()
