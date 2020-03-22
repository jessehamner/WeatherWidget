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

SETTINGS_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'settings.yml')
with open(SETTINGS_PATH, 'r') as iyaml:
  data = yaml.load(iyaml.read(), Loader=yaml.Loader)
ALERT_COUNTIES = data['alert_counties']
ALERT_ZONE = data['alert_zone']
ALERT_COUNTY = data['alert_county']
GOES_SECTOR = data['goes_sector']
GOES_RES = data['goes_res']
GOES_SAT = data['goes_sat']
ALERTS_DICT = data['alerts_dict']

GOES_BANDS = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11',
              '12', '13', '14', '15', '16', 'AirMass', 'GEOCOLOR',
              'NightMicrophysics', 'Sandwich', 'DayCloudPhase']

GOES_DOWNLOAD = 'https://cdn.star.nesdis.noaa.gov/GOES{sat}/ABI/SECTOR/{sector}/{band}/'
GOES_IMG = '{year}{doy}{timeHHMM}_GOES{sat}-ABI-{sector}-{band}-{resolution}.jpg'
GOES_DIR_DATE_FORMAT = 'DD-Mmm-YYYY'
# OUTPUT_DIR = os.path.join(os.environ['HOME'], 'Library/Caches/weatherwidget/')

HWO_DICT = {
    'site': data['hwo_site'],
    'issuedby': data['nws_abbr'],
    'product': 'HWO',
    'format': 'txt',
    'version': 1,
    'glossary': 0
    }

FTM_DICT = {
    'site': 'NWS',
    'issuedby': data['radar_station'],
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
  data['today_vars'] = wf.get_today_vars(data['timezone'])
  data['bands'] = GOES_BANDS
  data['goes_url'] = GOES_DOWNLOAD
  data['goes_img'] = GOES_IMG
  outage_text = wf.check_outage(HWO_URL, FTM_DICT)
  returned_message = wf.parse_outage(outage_text)
  outfilepath = os.path.join(data['output_dir'], 'outage.txt')
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
  conditions = wf.get_current_conditions(CUR_URL, data['station'])
  sum_con = wf.conditions_summary(conditions)
  if conditions and sum_con:
    nice_con = wf.format_current_conditions(sum_con)
  else:
    print('ERROR: something went wrong getting the current conditions. Halting.')
    return 1

  with open(os.path.join(data['output_dir'], 'current_conditions.txt'), 'w') as curr_con:
    curr_con.write(nice_con)
  curr_con.close()

  if wf.get_weather_radar(RADAR_URL, data['radar_station']) is None:
    print('Unable to retrieve weather radar image. Halting now.')
    return 1

  wf.get_warnings_box(WARNINGS_URL, data['radar_station'])
  # hwo_statement = wf.get_hwo(HWO_URL, HWO_DICT)
  hwo_today = wf.split_hwo(wf.get_hwo(HWO_URL, HWO_DICT))
  if hwo_today is not None:
    hwo = re.sub('.DAY ONE', 'Hazardous Weather Outlook', hwo_today)
    #print(hwo)
    with open(os.path.join(data['output_dir'], 'today_hwo.txt'), 'w') as today_hwo:
      today_hwo.write(hwo)
    today_hwo.close()

  if wf.get_hydrograph(abbr=data['river_gauge_abbr'], hydro_url=WATER_URL).ok:
    print('Got hydrograph for {0} station, gauge "{1}".'.format(data['radar_station'],
                                                                data['river_gauge_abbr']))
  else:
    print('Cannot get hydrograph for specified gauge ({0}).'.format(data['river_gauge_abbr']))
    return 1

  forecastxml = wf.get_forecast(lon=data['lon'],
                                lat=data['lat'],
                                fmt=['24', 'hourly'],
                                url=FORECAST_URL)
  forecastdict = wf.parse_forecast(forecastxml)
  wf.write_forecast(fc_dict=forecastdict, outputdir=data['output_dir'])

  alert_dict = {}
  print('Getting alerts for the following counties: {0}.'.format(data['alert_counties']))
  alert_dict = wf.get_current_alerts(ALERTS_URL, data, alert_dict)
  if not alert_dict:
    os.remove(os.path.join(data['output_dir'], 'alerts_text.txt'))
  else: 
    with open(os.path.join(data['output_dir'], 'alerts_text.txt'), 'w') as current_alerts:
      for key, value in alert_dict.iteritems():
        print('Key for this alert entry: {0}'.format(key))
        current_alerts.write('{0}\n'.format(value['warning_summary']))

  goes_list = wf.get_goes_list(data=data, band='GEOCOLOR')
  band_timestamps = wf.get_goes_timestamps(data, goes_list)
  current_timestamp = band_timestamps[-1]
  current_image = wf.get_goes_image(data, current_timestamp, band='GEOCOLOR')
  print('retrieved {0}'.format(current_image))


  return 0


if __name__ == '__main__':
  sys.exit(main())
