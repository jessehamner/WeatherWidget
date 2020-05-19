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
import re
import yaml
import numpy as np
import weather_functions as wf
from imagery import Imagery
from moon_phase import Moon_phase
from alerts import Alerts
from outage import Outage
from radar import Radar
from obs import WeatherDict, Observation

# Pull settings in from two YAML files:
SETTINGS_DIR = os.path.dirname(os.path.realpath(__file__))
data = wf.load_yaml(SETTINGS_DIR, 'settings.yml')
defaults = wf.load_yaml(SETTINGS_DIR, 'defaults.yml')
if not (data and defaults):
  sys.exit('settings files are required and could not be loaded successfully.')

data['defaults'] = defaults
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
  data['today_vars'] = wf.get_today_vars(data['timezone'])
  data['bands'] = data['defaults']['goes_bands']

  # Check for outage information
  outage_checker = Outage(data) 
  outage_checker.check_outage()
  outage_result = outage_checker.parse_outage()
  outfilepath = os.path.join(data['output_dir'], 'outage.txt')
  if outage_result is None:
    print('No outages detected. Proceeding.')
    try:
      os.unlink(outfilepath)
    except OSError:
      print('file does not exist: {0}'.format(outfilepath))

  else:
    print('There is outage text: {0}'.format(outage_result))
    try:
      cur = open(outfilepath, 'w')
      cur.write(outage_result)
      cur.close()
    except OSError as e:
      print('OSError-- {0}: {1}'.format(outfilepath, e))

  # Get and digest current conditions
  conditions = wf.get_current_conditions(defaults['cur_url'], data['station'])
  if conditions:
    print('Current conditions, nearly raw: {0}'.format(conditions))
  else:
    print('Unable to retrieve current conditions from primary location. Using backup data source.')
  backup_obs = wf.get_backup_obs(data, station_abbr=data['station'])
  print('Backup conditions, nearly raw: {0}'.format(backup_obs))

  conditions = wf.merge_good_observations(backup_obs, conditions)

  sum_con = wf.conditions_summary(conditions)

  if conditions and sum_con:
    text_conditions, nice_con = wf.format_current_conditions(sum_con)
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

  with open(os.path.join(data['output_dir'], 'current_conditions.txt'), 'w') as curr_con:
    curr_con.write(text_conditions)
  curr_con.close()

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

  
  if wf.get_hydrograph(abbr=data['river_gauge_abbr'],
                       hydro_url=data['defaults']['water_url'],
                       outputdir=data['output_dir']).ok:
    print('Got hydrograph for {0} station, gauge "{1}".'.format(data['radar_station'],
                                                                data['river_gauge_abbr']))
  else:
    print('Cannot get hydrograph for specified gauge ({0}).'.format(data['river_gauge_abbr']))
    return 1

  forecastxml = wf.get_forecast(lon=data['lon'],
                                lat=data['lat'],
                                fmt=None,
                                url=data['defaults']['forecast_url'])
  forecastdict = wf.parse_forecast(forecastxml)
  wf.write_forecast(fc_dict=forecastdict, outputdir=data['output_dir'])
  wf.write_json(some_dict=forecastdict, 
                outputdir=data['output_dir'],
                filename='forecast.json' 
               )
  wf.make_forecast_icons(forecastdict, outputdir=data['output_dir'])

  # Satellite imagery: 
  current_image = Imagery(band='GEOCOLOR', data=data)
  current_image.get_current_image()

  # Moon phase and icon name for the moon phase:
  moon_icon = Moon_phase(data)
  moon_icon_name = moon_icon.get_moon_phase()
  
  return 0


if __name__ == '__main__':
  sys.exit(main())
