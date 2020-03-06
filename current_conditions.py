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
import yaml
import weather_functions as wf

with open('settings.yml', 'r') as iyaml:
  data = yaml.load(iyaml.read(), Loader=yaml.Loader)
ALERT_COUNTIES = data['alert_counties']
STATION = data['station']
ALERT_ZONE = data['alert_zone']
ALERT_COUNTY = data['alert_county']
RADAR_STATION = data['radar_station']
NWS_ABBR = data['nws_abbr']
GOES_SECTOR = data['goes_sector']
GOES_RES = data['goes_res']
GOES_SAT = data['goes_sat']
ALERTS_DICT = data['alerts_dict']
HWO_SITE = data['hwo_site']
LON = data['lon']
LAT = data['lat']
RIVER_GAUGE_ABBR = data['river_gauge_abbr']
OUTPUT_DIR = data['output_dir']

GOES_BANDS = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11',
              '12', '13', '14', '15', '16', 'AirMass', 'GEOCOLOR',
              'NightMicrophysics', 'Sandwich', 'DayCloudPhase']

GOES_DOWNLOAD = 'https://cdn.star.nesdis.noaa.gov/GOES{sat}/ABI/SECTOR/{sector}/{band}/'
GOES_IMG = '{year}{doy}{timeHHMM}_GOES{sat}-ABI-{sector}-{band}-{resolution}.jpg'
GOES_DIR_DATE_FORMAT = 'DD-Mmm-YYYY'
# OUTPUT_DIR = os.path.join(os.environ['HOME'], 'Library/Caches/weatherwidget/')

HWO_DICT = {
    'site': HWO_SITE,
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

CUR_URL = 'https://api.weather.gov/stations/{station}/observations/current'
RADAR_URL = 'https://radar.weather.gov/ridge/RadarImg/N0R/{station}_{image}'
WARNINGS_URL = 'https://radar.weather.gov/ridge/Warnings/Short/{station}_{warnings}_0.gif'
HWO_URL = 'https://forecast.weather.gov/product.php'
ALERTS_URL = 'https://alerts.weather.gov/cap/wwaatmget.php'
WATER_URL = 'https://water.weather.gov/resources/hydrographs'
FORECAST_URL = os.path.join('https://graphical.weather.gov',
                            'xml/sample_products/browser_interface',
                            'ndfdBrowserClientByDay.php'
                           )
WEATHER_URL_ROOT = 'https://radar.weather.gov/ridge/Overlays'
SHORT_RANGE_COUNTIES = 'County/Short/{radar}_County_Short.gif'
SHORT_RANGE_HIGHWAYS = 'Highways/Short/{radar}_Highways_Short.gif'
SHORT_RANGE_MED_CITIES = 'Cities/Short/{radar}_City_250K_Short.gif'
SHORT_RANGE_LRG_CITIES = 'Cities/Short/{radar}_City_1M_Short.gif'
SHORT_RANGE_SML_CITIES = 'Cities/Short/{radar}_City_25K_Short.gif'
SHORT_RANGE_RING = 'RangeRings/Short/{radar}_RangeRing_Short.gif'
SHORT_RANGE_RIVERS = 'Rivers/Short/{radar}_Rivers_Short.gif'
SHORT_RANGE_TOPO = 'Topo/Short/{radar}_Topo_Short.jpg'
LEGEND_URL_ROOT = 'https://radar.weather.gov'
LEGEND = 'Legend/N0R/{radar}_N0R_Legend_0.gif'

GRAPHICS_LIST = [SHORT_RANGE_COUNTIES, SHORT_RANGE_HIGHWAYS, SHORT_RANGE_TOPO,
                 SHORT_RANGE_MED_CITIES, SHORT_RANGE_LRG_CITIES, SHORT_RANGE_RING,
                 SHORT_RANGE_SML_CITIES, SHORT_RANGE_RIVERS]


def main():
  """
  - Parse user-specified data from YaML
  - Check to see that the needed graphics are available. If not, get them.
  - Get the radar image, plus the legend overlay.
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
  - TODO: use PythonMagick instead of post-processing via shell script

  """
  today_vars = wf.get_today_vars(data['timezone'])
  data['bands'] = GOES_BANDS
  data['goes_url'] = GOES_DOWNLOAD
  data['goes_img'] = GOES_IMG
  data['today_vars'] = today_vars
  outage_text = wf.check_outage(HWO_URL, FTM_DICT)
  returned_message = wf.parse_outage(outage_text)
  outfilepath = os.path.join(OUTPUT_DIR, 'outage.txt')
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
  wf.check_graphics([LEGEND,], LEGEND_URL_ROOT)
  conditions = wf.get_current_conditions(CUR_URL, STATION)
  sum_con = wf.conditions_summary(conditions)
  if conditions and sum_con:
    nice_con = wf.format_current_conditions(sum_con)
  else:
    print('ERROR: something went wrong getting the current conditions. Halting.')
    return 1

  with open(os.path.join(OUTPUT_DIR, 'current_conditions.txt'), 'w') as current_conditions:
    current_conditions.write(nice_con)
  current_conditions.close()

  if wf.get_weather_radar(RADAR_URL, RADAR_STATION) is None:
    print('Unable to retrieve weather radar image. Halting now.')
    return 1

  wf.get_warnings_box(WARNINGS_URL, RADAR_STATION)
  # hwo_statement = wf.get_hwo(HWO_URL, HWO_DICT)
  hwo_today = wf.split_hwo(wf.get_hwo(HWO_URL, HWO_DICT))
  if hwo_today is not None:
    hwo = re.sub('.DAY ONE', 'Hazardous Weather Outlook', hwo_today)
    #print(hwo)
    with open(os.path.join(OUTPUT_DIR, 'today_hwo.txt'), 'w') as today_hwo:
      today_hwo.write(hwo)
    today_hwo.close()

  if wf.get_hydrograph(abbr=RIVER_GAUGE_ABBR, hydro_url=WATER_URL).ok:
    print('Got hydrograph for {0} station, gauge "{1}".'.format(RADAR_STATION, RIVER_GAUGE_ABBR))
  else:
    print('Unable to retrieve hydrograph for specified gauge ({0}).'.format(RIVER_GAUGE_ABBR))
    return 1

  forecastxml = wf.get_forecast(lon=LON,
                                lat=LAT,
                                fmt=['24', 'hourly'],
                                url=FORECAST_URL)
  forecastdict = wf.parse_forecast(forecastxml)
  wf.write_forecast(fc_dict=forecastdict, outputdir=OUTPUT_DIR)

  return 0


if __name__ == '__main__':
  sys.exit(main())
