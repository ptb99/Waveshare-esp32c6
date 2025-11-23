##
## CircuitPython code for a basic clock on TFT display
##

import asyncio
import board
import keypad
import adafruit_logging as logging
import traceback

import wifi
import socketpool
import adafruit_ntp
import adafruit_connection_manager
import adafruit_requests

#import terminalio
#from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.bitmap_label import Label


## config knobs;
DEBUG = False
#DEBUG = True

TZ_OFFSET = 0 ## use AF service to get offset
#TZ_OFFSET = -7 # for PDT
#TZ_OFFSET = -8 # for PST

LARGE_FONT =  "fonts/NotoSans-CondensedMedium-72.pcf"
FG_COLORS = [0x0000FF, 0xFF00FF, 0xFF0000, 0xFFFF00, 0x00FF00, 0x00FFFF]


## UI buttons (BOOT and RESET) - can only use "BOOT"
BUTTON = board.BUTTON


class ColorSelect():
    def __init__(self):
        self.color_wheel = FG_COLORS[:]

    def get(self):
        return self.color_wheel[0]

    def rotate_left(self):
        self.color_wheel = self.color_wheel[1:] + [self.color_wheel[0]]

    def rotate_right(self):
        self.color_wheel = [self.color_wheel[-1]] + self.color_wheel[0:-1]


def get_time_string(ts):
    return f'{ts.tm_hour:02d}:{ts.tm_min:02d}:{ts.tm_sec:02d}'


## Network setup and ntp object
def get_ntp_handle(*, dhcpname=None, tz_offset=0):
    logger = logging.getLogger('main')

    # Get wifi details and more from a secrets.py file
    try:
        from secrets import secrets
    except ImportError:
        logger.error("WiFi secrets are kept in secrets.py, please add them there!")
        raise

    mac = ':'.join(f'{i:02x}' for i in wifi.radio.mac_address)
    logger.info(f"My MAC addr: {mac}")

    if dhcpname:
        wifi.radio.hostname = dhcpname
    wifi.radio.connect(secrets["ssid"], secrets["password"])

    logger.info("Connected to %s!"%secrets["ssid"])
    logger.info(f"My IP address is {wifi.radio.ipv4_address}")

    # create socket pool
    pool = socketpool.SocketPool(wifi.radio)
    ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)

    # get DST-adjusted offset from Adafruit service
    if tz_offset == 0:
        requests = adafruit_requests.Session(pool, ssl_context)
        url = f'https://io.adafruit.com/api/v2/{secrets["aio_username"]}/' + \
            f'integrations/time/strftime?x-aio-key={secrets["aio_key"]}&fmt=%25z'
        with requests.get(url) as response:
            logger.info(f"strftime GET returned status: {response.status_code}")
            # check status_code == 200??
            val = int(response.text)/100
            logger.info(f"tz_offset: {response.text} ->  {int(val)}")
            tz_offset = int(val)

    # NTP handle
    ntp = adafruit_ntp.NTP(pool, tz_offset=tz_offset, cache_seconds=600)
          # default server = "0.adafruit.pool.ntp.org"
          # cache_seconds = poll NTP no more often than (what is optimal?)
    return ntp


class MyDisplay:
    def __init__(self, disp, font, color_wheel):
        self.display = disp
        time_text = '00:00:00'

        self.font = bitmap_font.load_font(font)
        self.color_wheel = color_wheel

        # Create the text label
        # label_dir = DWR because default display is portrait (vs landscape)
        self.text_area = Label(self.font, text=time_text,
                               label_direction="DWR",
                               color=self.color_wheel.get())

        # Set the location (Note display is in portrait mode)
        self.text_area.x = 50
        self.text_area.y = 100

        # display.show() is now replaced by setting .root_group
        self.display.root_group = self.text_area

    def update_text(self, text):
        self.text_area.text = text
        fgcolor = self.color_wheel.get()
        self.text_area.color = fgcolor
        self.display.refresh()
        # logger = logging.getLogger('main')
        # logger.debug(f'update_text with {text} and color {fgcolor:x}')


async def handle_button(pin, color_wheel):
    """Handle UI button: run through a set of FG colors."""
    logger = logging.getLogger('main')
    with keypad.Keys(
        (pin, ), value_when_pressed=True, pull=True
    ) as keys:
        while True:
            event = keys.events.get()
            if event and event.pressed:
                # rotate down
                color_wheel.rotate_right()
                fgcolor = color_wheel.get()
                logger.info(f'key DOWN - rotate left - color {fgcolor:x}')
            # Let another task run.
            await asyncio.sleep(0)


## main program
async def main():
    logger = logging.getLogger('main')
    ntp_hndl = get_ntp_handle(dhcpname='esp32clock')
    color_wheel = ColorSelect()
    disp = MyDisplay(board.DISPLAY, LARGE_FONT, color_wheel)

    button_task = asyncio.create_task(
        handle_button(BUTTON, color_wheel)
    )

    while True:
        try:
            #now = time.localtime()
            now = ntp_hndl.datetime
            time_text = get_time_string(now)
            logger.debug(f'Time = {time_text}')
            disp.update_text(time_text)
            await asyncio.sleep(1)

        except OSError as e:
            # NTP error
            logger.error(f'OSError: {e}')
            # prob a timeout to NTP server, just try again

        except Exception as e:
            # This works to print a stack trace
            logger.error(f'Unexpected exception: {e}')
            traceback.print_exception(e)
            # re-raise the error and hang the program
            raise

    await asyncio.gather(button_task)


## actual exec here:
if __name__ == '__main__':
    logger = logging.getLogger('main')
    if DEBUG:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    #main()
    asyncio.run(main())
