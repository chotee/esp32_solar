import utime
import machine
from machine import Pin, ADC
import network
import socket

authfile = "auth.txt"
server_host = '192.168.8.129'
server_port = 2300

led_pin = machine.Pin(5, machine.Pin.OUT)
sta_if = network.WLAN(network.STA_IF)
conns = []
config = {}
bat_pin = ADC(Pin(36))
sol_pin = ADC(Pin(37))

ADC_MAX_VOLTAGE = 1.1
ADC_MAX_VALUE   = 2**12

def setup():
    print("Setup Starting")
    config["ess_id"], config["ess_pass"] = read_auth()
    sta_if.active(True)


def main():
    print("Main Starting")
    operative = False
    while True:  # Main repetitive loop.
        while not is_system_operative():
            prepare_loop()
        if not operative:
            operative_setup()
            operative = True
        operative_loop()


def toggle(pin):
    pin(not pin())


def operative_setup():
    print("System Now Operative.")
    conns[0].send("Start\n")


def prepare_loop():
    """
    The loop that gets called when the system is not yet ready
    """
    if config["ess_id"]:
        if not sta_if.isconnected():
            print("Connecting to '%s' with password" % config["ess_id"])
            sta_if.connect(config["ess_id"], config["ess_pass"])
        elif len(conns) == 0:
            try:
                addr_info = socket.getaddrinfo(server_host, server_port)
                addr = addr_info[0][-1]
                s = socket.socket()
                s.connect(addr)
            except OSError as exc:
                print("Failing to connect: %s" % exc)
            else:
                conns.append(s)
        else:
            print("Shouldn't get here.")
    for x in range(4):  # blink 4 times.
        toggle(led_pin)
        utime.sleep_ms(150)


def operative_loop():
    """
    The normal work loop
    """
    toggle(led_pin)
    utime.sleep_ms(500)
    bat_v = pin_to_voltage(bat_pin, 4.3)
    sol_v = pin_to_voltage(sol_pin, 7.8)
    conns[0].send("bat: %.3f, solar: %.3f, t: %dms\n" % (bat_v, sol_v, utime.ticks_ms()))


def pin_to_voltage(pin, multi):
    value = pin.read()
    return (value * ADC_MAX_VOLTAGE * multi) / ADC_MAX_VALUE


def is_system_operative():
    """
    Returns True if the system is ready to do it's normal operation
    :return: True if working, False otherwise.
    :rtype: bool
    """
    if not sta_if.isconnected():
        return False
    if len(conns) == 0:
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
