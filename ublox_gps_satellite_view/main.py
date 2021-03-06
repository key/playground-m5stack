# based on https://gist.github.com/TakehikoShimojima/e47e6e8ee9d1a57a20d2bca588b59b03#file-gpswatch-py
import sys
import utime, gc, _thread
from math import radians, sin, cos

import uos
from machine import RTC, UART
from m5stack import lcd, buttonC

import micropyGPS

lcd.clear()


# Init GPS
lcd.print('UART:Initializing\n', 0, 0)
gps_s = UART(2, tx=17, rx=16, baudrate=9600, timeout=200, buffer_size=256, lineend='\r\n')
# micropyGPS.MicropyGPS.supported_sentences.update({'GNGSA': micropyGPS.MicropyGPS.gpgsa})
gps = micropyGPS.MicropyGPS(9, 'dd')
lcd.print('UART:Initialized\n')

# Init RTC
lcd.print('RTC:Initializing\n')
rtc = RTC()
rtc.ntp_sync(server='hr.pool.ntp.org', tz='CET-1CEST')
lcd.print('RTC:Initialize status %s\n' % rtc.synced())

# Mount SD
result = uos.mountsd()
lcd.print('SDCard:Mount result %s\n' % result)
lcd.print('SDCard:listdir %s\n' % uos.listdir('/sd'))


def watchGPS():
    lcd.print('GPS:Start loop\n')

    n = 0
    tm_last = 0
    satellites = dict()
    satellites_used = dict()

    fp = open('/sd/gpslog.txt', 'a')
    lcd.print('fp %s\n' % fp)

    while True:
        utime.sleep_ms(100)
        length = gps_s.any()
        if length > 0:
            buf = gps_s.read(length)
            fp.write(buf)

            if buttonC.isPressed():
                lcd.clear()
                lcd.print('Button C Pressed.\n', 0, 0)
                fp.close()
                lcd.print('File closed.\n')
                lcd.print('System exit.\n')
                sys.exit()

            for val in buf:

                if 10 <= val <= 126:
                    stat = gps.update(chr(val))
                    if stat:
                        tm = gps.timestamp
                        tm_now = (tm[0] * 3600) + (tm[1] * 60) + int(tm[2])
                        print('compare time tm_now={}, tm_last={}'.format(tm_now, tm_last))
                        if (tm_now - tm_last) >= 10:
                            print('compare True')
                            n += 1
                            tm_last = tm_now
                            print('{} {}:{}:{}'.format(gps.date_string(), tm[0], tm[1], int(tm[2])))
                            str_ = '%.10f %c, %.10f %c' % (
                            gps.latitude[0], gps.latitude[1], gps.longitude[0], gps.longitude[1],
                            )
                            print(str_)
                            lcd.clear()
                            lcd.print(str_, 10, 0)
                            if gps.satellite_data_updated():
                                putSatellites(satellites, gps.satellite_data, tm_now)
                            putSatellitesUsed(satellites_used, gps.satellites_used, tm_now)
                            drawGrid()
                            drawSatellites(satellites, satellites_used)
                            if (n % 10) == 0:
                                print('Mem free:', gc.mem_free())
                                gc.collect()

def putSatellites(sats, new_sats, tm):
    for k, v in new_sats.items():  # 衛星の辞書に新しい衛星データーと現在時刻を追加する
        sats.update({k: (v, tm)})
    for k, v in sats.items():  # 衛星の辞書中で300秒以上古いものを削除する
        if tm - v[1] > 300:
            print('pop(%s)' % str(k))
            sats.pop(k)

def putSatellitesUsed(sats_used, sats, tm):
    for x in sats:
        sats_used.update({x: tm})
    for k, v in sats_used.items():
        if tm - v > 300:
            print('pop_used(%s)' % str(k))
            sats_used.pop(k)
    print(sats_used)

def drawGrid():
    for x in range(40, 121, 40):
        lcd.circle(160, 120, x, lcd.DARKGREY)
    for x in range(0, 360, 45):
        lcd.lineByAngle(160, 120, 0, 120, x, lcd.DARKGREY)
    for x in (('N', 165, 10), ('E', 295, 115), ('S', 165, 220), ('W', 15, 115)):
        lcd.print(x[0], x[1], x[2])
    for x in (('90', 155, 108), ('60', 195, 108), ('30', 235, 108), ('0', 275, 108)):
        lcd.print(x[0], x[1], x[2])

def drawSatellites(sats, sats_used):
    for k, v in sats.items():
        print(k, v[0])
        if v[0][0] != None and v[0][1] != None:
            l = int((90 - v[0][0]) / 90.0 * 120.0)
            lcd.lineByAngle(160, 120, 0, l, v[0][1])
            x = 160 + sin(radians(v[0][1])) * l
            y = 120 - cos(radians(v[0][1])) * l
            color = lcd.GREEN if k in sats_used else lcd.RED
            lcd.circle(int(x), int(y), 4, color, color)
            lcd.print(str(k), int(x) + 9, int(y) - 7)


testth = _thread.start_new_thread('GPS', watchGPS, ())
