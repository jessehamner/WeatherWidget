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
import weather_functions as wf
from imagery import Imagery
from moon_phase import MoonPhase
from alerts import Alerts
from radar import Radar
from obs import WeatherDict, Observation
from forecast import Forecast
import weathersvg as wsvg

# Pull settings in from two YAML files:
SETTINGS_DIR = os.path.dirname(os.path.realpath(__file__))
# OUTPUT_DIR = os.path.join(os.environ['HOME'], 'Library/Caches/weatherwidget/')


def main():
  """
  - Parse user-specified data from YaML
  - Check to see that the needed graphics are available. If not, get them.
  - Get the radar image, plus the legend overlay.
  - Get the warnings boxes graphic
  - Get today's hazardous weather outlook statement and parse it
  - Check for FTM outage notifications
  - Get and parse current weather conditions.
  - Cache current data to specified locations.
  - TODO: should run the getweather.sh shell script, that overlays/composites
    the weather graphics. At present, that shell script calls this script
    and runs the overlays with -bash-.
  - Acquire multi-band GOES-x imagery from today, checking to see if
    there is a new image and comparing it to the list of files from today,
    of the specified resolution.
  - TODO: Make animated gifs of last 24 hours of a few bands of images
  - TODO: use Flask API as a microservice for JSON data payloads
  - TODO: derived variables with metpy (especially from METAR string vars)
  """
  data = wf.load_yaml(SETTINGS_DIR, 'settings.yml')
  defaults = wf.load_yaml(SETTINGS_DIR, 'defaults.yml')
  if not (data and defaults):
    sys.exit('settings files are required and could not be loaded successfully.')
  data['defaults'] = defaults
  data['today_vars'] = wf.get_today_vars(data['timezone'])
  data['bands'] = data['defaults']['goes_bands']

  # Check for outage information
  wf.outage_check(data)

  # Get and digest current conditions
  right_now = Observation(data)
  right_now.get_current_conditions()
  right_now.get_backup_obs(use_json=False)
  right_now.merge_good_observations()
  print('Merged current conditions: {0}'.format(right_now.con1.obs))
  sum_con = right_now.conditions_summary()

  if right_now.con1.obs and sum_con:
    text_conditions, nice_con = right_now.format_current_conditions()
    print('Current conditions from primary source: {0}'.format(nice_con))
    html_table = wf.htable_current_conditions(nice_con,
                                              'current_conditions.html',
                                              outputdir=data['output_dir'])
    wf.write_json(some_dict=nice_con,
                  outputdir=data['output_dir'],
                  filename='current_conditions.json'
                 )
  else:
    print('ERROR: something went wrong getting the current conditions. Halting.')
    return 1

  wf.write_text(os.path.join(data['output_dir'], 'current_conditions.txt'), text_conditions)

# Get radar image:
  current_radar = Radar(data)
  current_radar.check_assets()
  current_radar.get_radar()
  current_radar.get_warnings_box()
  if current_radar.problem:
    print('Unable to retrieve weather radar image. Halting now.')

  # Hazardous Weather Outlook and alerts:
  today_alerts = Alerts(data)
  today_alerts.get_alerts()

  # Get hydrograph image.
  if wf.get_hydrograph(abbr=data['river_gauge_abbr'],
                       hydro_url=data['defaults']['water_url'],
                       outputdir=data['output_dir']).ok:
    print('Requesting hydrograph for station {0}, gauge "{1}".'.format(data['radar_station'],
                                                                       data['river_gauge_abbr']))
  else:
    print('...Failed.')
    return 1

  forecast_obj = Forecast(data=data)
  forecast_obj.get_forecast()
  forecastdict = forecast_obj.parse_forecast()
  forecast_obj.write_forecast(outputdir=data['output_dir'])
  # Area forecast discussion:
  afd_dict = forecast_obj.get_afd()

  wf.write_json(some_dict=forecastdict,
                outputdir=data['output_dir'],
                filename='forecast.json'
               )
  wsvg.make_forecast_icons(forecastdict, outputdir=data['output_dir'])

  # Satellite imagery:
  current_image = Imagery(band='GEOCOLOR', data=data)
  current_image.get_current_image()

  # Moon phase and icon name for the moon phase:
  moon_icon = MoonPhase(data)
  moon_icon_name = moon_icon.get_moon_phase()

  return 0


if __name__ == '__main__':
  sys.exit(main())
