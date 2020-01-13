#!/usr/bin/env python
"""

See https://www.weather.gov/jetstream/gis
https://radar.weather.gov/GIS.html
https://radar.weather.gov/ridge/Overlays/
https://mesonet.agron.iastate.edu/GIS/legends/TR0.gif

Jesse Hamner, 2019

"""

from __future__ import print_function

import sys
import os
import re
import weather_functions as wf

# TODO move the location params to a YAML file or something
ALERT_ZONE = 'TXZ103'
ALERT_COUNTY = 'TXC121'
RADAR_STATION = 'FWS'
NWS_ABBR = 'FWD'
GOES_SECTOR = 'sp'
GOES_RES = '2400x2400'
GOES_SAT = '16'
GOES_BANDS = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11',
              '12', '13', '14', '15', '16', 'AirMass', 'GEOCOLOR']
GOES_DOWNLOAD = 'https://cdn.star.nesdis.noaa.gov/GOES{sat}/ABI/SECTOR/{sector}/{band}'
GOES_IMG = '{year}{doy}{timeHHMM}_GOES{sat}-ABI-{sector}-{band}-{resolution}.jpg'
GOES_DIR_DATE_FORMAT = 'DD-Mmm-YYYY'

HWO_DICT = {
    'site': 'DDC',
    'issuedby': NWS_ABBR,
    'product': 'HWO',
    'format': 'txt',
    'version': 1,
    'glossary': 0
    }

FTM_DICT = {
    'site': 'NWS',
    'issuedby': RADAR_STATION,
    'product': 'FTM',
    'format': 'CI',
    'version': 1,
    'glossary': 0
    }

# Alert abbreviations can be found at https://alerts.weather.gov/
ALERTS_DICT = {'x': 'TXC121',
               'y': 1
              }

STATION = 'KDTO'
CUR_URL = 'https://api.weather.gov/stations/{station}/observations/current'
RADAR_URL = 'https://radar.weather.gov/ridge/RadarImg/N0R/{station}_{image}'
WARNINGS_URL = 'https://radar.weather.gov/ridge/Warnings/Short/{station}_{warnings}_0.gif'
HWO_URL = 'https://forecast.weather.gov/product.php'
ALERTS_URL = 'https://alerts.weather.gov/cap/wwaatmget.php'

WEATHER_URL_ROOT = 'https://radar.weather.gov/ridge/Overlays'
SHORT_RANGE_COUNTIES = 'County/Short/{radar}_County_Short.gif'
SHORT_RANGE_HIGHWAYS = 'Highways/Short/{radar}_Highways_Short.gif'
SHORT_RANGE_MED_CITIES = 'Cities/Short/{radar}_City_250K_Short.gif'
SHORT_RANGE_LRG_CITIES = 'Cities/Short/{radar}_City_1M_Short.gif'
SHORT_RANGE_SML_CITIES = 'Cities/Short/{radar}_City_25K_Short.gif'
SHORT_RANGE_RING = 'RangeRings/Short/{radar}_RangeRing_Short.gif'
SHORT_RANGE_RIVERS = 'Rivers/Short/{radar}_Rivers_Short.gif'
SHORT_RANGE_TOPO = 'Topo/Short/{radar}_Topo_Short.jpg'

GRAPHICS_LIST = [SHORT_RANGE_COUNTIES, SHORT_RANGE_HIGHWAYS, SHORT_RANGE_TOPO,
                 SHORT_RANGE_MED_CITIES, SHORT_RANGE_LRG_CITIES, SHORT_RANGE_RING,
                 SHORT_RANGE_SML_CITIES, SHORT_RANGE_RIVERS]

def main():
  """
  - Check to see that the needed graphics are available. If not, get them.
  - Get the radar image
  - Get the warnings boxes graphic
  - Get today's hazardous weather outlook statement and parse it
  - Check for FTM outage notifications
  - Get and parse current weather conditions.
  - Write out the files to helpful locations.
  - TODO: should run the getweather.sh shell script, that overlays/composites
    the weather graphics. At present, that shell script calls this script
    and runs the overlays with -bash-.
  - TODO: Acquire multi-band GOES-x imagery from today, checking to see if
    there is a new image and comparing it to the list of files from today,
    of the specified resolution.
  - TODO: Remove radar and satellite images more than two days old
  - TODO: Make animated gifs of last 36 hours of radar and a few bands of images

  """

  outage_text = wf.check_outage(HWO_URL, FTM_DICT)
  returned_message = wf.parse_outage(outage_text)
  outfilepath = os.path.join('/tmp/', 'outage.txt')
  if returned_message:
    print('There is outage text: {0}'.format(returned_message))
    cur = open(outfilepath, 'w')
    cur.write(returned_message)
    cur.close()
  else:
    try:
      os.unlink(outfilepath)
    except OSError:
      print('file does not exist: {0}'.format(outfilepath))

  wf.check_graphics(GRAPHICS_LIST, WEATHER_URL_ROOT)
  conditions = wf.get_current_conditions(CUR_URL, STATION)
  sum_con = wf.conditions_summary(conditions)
  nice_con = wf.format_current_conditions(sum_con)
  with open('/tmp/current_conditions.txt', 'w') as current_conditions:
    current_conditions.write(nice_con)
  current_conditions.close()

  wf.get_weather_radar(RADAR_URL, RADAR_STATION)
  wf.get_warnings_box(WARNINGS_URL, RADAR_STATION)
  hwo_statement = wf.get_hwo(HWO_URL, HWO_DICT)
  hwo_today = wf.split_hwo(hwo_statement)
  if hwo_today is not None:
    hwo = re.sub('.DAY ONE', 'Hazardous Weather Outlook', hwo_today)
    #print(hwo)
    with open('/tmp/today_hwo.txt', 'w') as today_hwo:
      today_hwo.write(hwo)
    today_hwo.close()

  return 0


if __name__ == '__main__':
  sys.exit(main())
