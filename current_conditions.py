#!/usr/bin/env python
"""

See https://www.weather.gov/jetstream/gis
https://radar.weather.gov/GIS.html
https://radar.weather.gov/ridge/Overlays/
https://mesonet.agron.iastate.edu/GIS/legends/TR0.gif

Jesse Hamner, 2019--2020

"""

from __future__ import print_function

import sys
import os
import logging
import weather_functions as wf
from imagery import Imagery
from alerts import Alerts
from radar import Radar
from obs import Observation
from forecast import Forecast
import weathersvg as wsvg

# Pull settings in from two YAML files:
SETTINGS_DIR = os.path.dirname(os.path.realpath(__file__))
# OUTPUT_DIR = os.path.join(os.environ['HOME'], 'Library/Caches/weatherwidget/')


def main():
  """
  - Parse user-specified data from YaML
  - Check to see that the needed graphics are available. If not, get them.
  - Get the radar imagery, complete with warnings graphics
  - Get today's hazardous weather outlook statement and parse it
  - Check for FTM outage notifications
  - Get, parse, and write out current weather conditions to specified locations.
  - TODO: should run the getweather.sh shell script, that overlays/composites
    the weather graphics. At present, that shell script calls this script
    and runs the overlays with -bash-.
  - Check for and acquire current multi-band GOES-x imagery of a given resolution.
  """
  if os.path.exists('weatherwidget.log'):
    os.remove('weatherwidget.log')
  logging.basicConfig(filename='weatherwidget.log', level=logging.INFO,
                      format='%(asctime)s %(levelname)s %(threadName)-10s %(message)s',)

  data = wf.load_settings_and_defaults(SETTINGS_DIR, 'settings.yml', 'defaults.yml')
  if not data:
    logging.error('Unable to load settings files. These are required.')
    sys.exit('settings files are required and could not be loaded successfully.')

  logging.info('Checking for radar outage.')
  wf.outage_check(data)

  logging.info('Retrieving current weather observations.')
  right_now = Observation(data)
  right_now.get_current_conditions()
  right_now.get_backup_obs(use_json=False)
  right_now.merge_good_observations()
  logging.debug('Merged current conditions: %s', right_now.con1.obs)
  sum_con = right_now.conditions_summary()

  if right_now.con1.obs and sum_con:
    text_conditions, nice_con = right_now.format_current_conditions()
    logging.debug('Current conditions from primary source: %s', nice_con)
    wf.write_json(some_dict=nice_con,
                  outputdir=data['output_dir'],
                  filename='current_conditions.json'
                 )
  else:
    logging.error('Something went wrong getting the current conditions. Halting.')
    return 1

  wf.write_text(os.path.join(data['output_dir'], 'current_conditions.txt'), text_conditions)

# Get radar image:
  current_radar = Radar(data)
  current_radar.check_assets()
  current_radar.get_radar()
  current_radar.get_warnings_box()
  if current_radar.problem:
    logging.error('Unable to retrieve weather radar image. Halting now.')

  # Hazardous Weather Outlook and alerts:
  today_alerts = Alerts(data)
  today_alerts.get_alerts()

  # Get hydrograph image.
  if wf.get_hydrograph(abbr=data['river_gauge_abbr'],
                       hydro_url=data['defaults']['water_url'],
                       outputdir=data['output_dir']).ok:
    logging.info('Requesting hydrograph for station %s, gauge "%s".',
                 data['radar_station'], data['river_gauge_abbr'])
  else:
    logging.error('Failed to get hydrograph information.')
    return 1

  forecast_obj = Forecast(data=data)
  forecast_obj.get_forecast()
  forecastdict = forecast_obj.parse_forecast()
  if forecastdict is None:
    logging.error('Unable to parse forecast!')
    return 1
  forecast_obj.write_forecast(outputdir=data['output_dir'])
  # Area forecast discussion:
  forecast_obj.get_afd()

  wf.write_json(some_dict=forecastdict,
                outputdir=data['output_dir'],
                filename='forecast.json'
               )
  wsvg.make_forecast_icons(forecastdict, outputdir=data['output_dir'])

  # Satellite imagery:
  current_image = Imagery(band='GEOCOLOR', data=data)
  current_image.get_current_image()
  current_image.get_forecast_map()
  current_image.get_national_temp_map()

  logging.info('Finished program run.')

  return 0


if __name__ == '__main__':
  sys.exit(main())
