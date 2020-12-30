"""
obs.py: download and consolidate current conditions data for a given location.
"""

from __future__ import print_function

import os
import sys
import re
import logging
from bs4 import BeautifulSoup
import weather_functions as wf
import weathersvg as wsvg
import moon_phase


class WeatherDict(object):
  """
  A dictionary capable of holding relevant data for current weather
  observations.
  """

  def __init__(self, data=''):
    self.data = data
    self.obs = dict(temperature=dict(units='', value='', label='Temperature'),
                    dewpoint=dict(units='', value='', label='Dewpoint'),
                    humidity=dict(units='%', value='', label='Rel. Humidity'),
                    pressure=dict(units='', value='', label='Pressure'),
                    weather='',
                    wind=dict(units='', value='', label='Wind Speed'),
                    wind_direction=dict(units='degrees', value='', label='Wind Direction'),
                    gusts=dict(units='', value='', label='Gusts'),
                    windchill=dict(units='', value='', label='Wind Chill'),
                    heatindex=dict(units='', value='', label='Heat Index'),
                    location=dict(lon=0.0, lat=0.0, zip=00000, state='', label='Location'),
                    wind_cardinal='',
                    textdescription='',
                    metar='',
                    timestamp='',
                    beaufort=0,
                    weather_icon='',
                    moon_icon=''
                   )


class Observation(object):
  """
  Download, parse, error-check, and produce outputs of current conditions
  observations from the NWS for a given location.
  """

  def __init__(self, data=''):
    self.data = data
    self.backup_obs = WeatherDict(data=data)
    self.metar = ''
    self.con1 = WeatherDict(data=data)
    self.con2 = WeatherDict(data=data)
    self.matchup = ['pressure', 'dewpoint', 'temperature', 'humidity',
                    'wind_direction', 'heatindex', 'windchill', 'wind',
                    'gusts']
    self.textonly = ['weather', 'metar', 'textdescription', 'timestamp', 'beaufort']


  def get_current_conditions(self):
    """
    Take the JSON object from the NWS station and produce a reduced set of
    information for display.
    """
    cur_url = self.data['defaults']['cur_url'].format(station=self.data['station'])
    returned_json = wf.make_request(url=cur_url)

    if returned_json is None:
      logging.error('No usable reply from %s', self.data['defaults']['cur_url'])
      return None

    if 'properties' in returned_json.keys():
      con1 = self.con1.obs
      self.parse_primary_obs(returned_json=returned_json)

      logging.debug('Determining cardinal wind direction, if possible.')
      logging.info('Wind azimuth: %s', con1['wind_direction']['value'])
      wdstring = self.wind_direction(con1['wind_direction']['value'])
      if wdstring is None or wdstring == 'None':
        logging.debug('Unable to determine cardinal wind direction.')
        con1['wind_cardinal'] = 'No Data'
      else:
        logging.debug('Wind is out of the %s.', wdstring)
        con1['wind_cardinal'] = 'Out of the {0}'.format(wdstring)

      con1['beaufort'] = wf.beaufort_scale(self.data,
                                           speed=con1['wind']['value'],
                                           units=con1['wind']['units'])
      logging.info('Beaufort wind speed scale: %s', con1['beaufort'])

      con1['moon_icon'] = self.moonphase()

      return con1
    else:
      return None


  def parse_primary_obs(self, returned_json):
    """
    Parse the primary URL for current conditions. Return a dict.
    """
    other = {'textDescription': 'textdescription',
             'rawMessage': 'metar',
             'timestamp': 'timestamp',
             'presentWeather': 'weather'
            }

    useful = {'heatIndex': ['heatindex', 'temperature'],
              'relativeHumidity': ['humidity', 'percent'],
              'temperature': ['temperature', 'temperature'],
              'dewpoint': ['dewpoint', 'temperature'],
              'barometricPressure': ['pressure', 'pressure'],
              'windChill': ['windchill', 'temperature'],
              'windSpeed': ['wind', 'velocity'],
              'windGust': ['gusts', 'velocity']
             }
    tempdict = returned_json['properties']
    con1 = self.con1.obs
    for key, val in useful.iteritems():
      from_unit = re.sub(r'unit:\s*', '', tempdict[key]['unitCode'])
      from_unit = re.sub(r'^deg', '', from_unit)
      from_value = wf.sanity_check(tempdict[key]['value'])

      if from_value is None or from_value == self.data['defaults']['missing']:
        con1[val[0]]['value'] = 'None'
        con1[val[0]]['units'] = ''
      else:
        print('Converting {0} to {1} for {2} data'.format(from_unit,
                                                          self.data['units'][val[1]],
                                                          val[0])
             )
        sys.stdout.write('{0} Input: {1}'.format(val[0], from_value))
        con1[val[0]]['value'] = wf.convert_units(value=from_value,
                                                 from_unit=from_unit,
                                                 to_unit=self.data['units'][val[1]])
        sys.stdout.write('\tOutput: {0}'.format(con1[val[0]]['value']))
        con1[val[0]]['units'] = self.data['units'][val[1]]
        sys.stdout.write('\tUnits: {0}\n'.format(self.data['units'][val[1]]))

    for key, val in other.iteritems():
      con1[val] = tempdict[key]

    con1['wind_direction'] = {'value': tempdict['windDirection']['value'],
                              'units': 'degrees',
                              'label': 'Wind Direction'
                             }
    return con1


  def get_backup_obs(self, use_json=False):
    """
    Something strange is happening with the data for at least one location --
    the raw message contains complete information, but the returned dictionary
    has missing data. Trying a backup XML feed from w1.weather.gov.
    """
    url = self.data['defaults']['backup_current_obs_url'].format(obs_loc=self.data['station'])
    retpage = wf.make_request(url=url, use_json=use_json)
    if not retpage:
      self.backup_obs.obs = None
      logging.error('No weather observation was obtained from %s', url)
      return None
    
    bsbackup = BeautifulSoup(retpage, 'lxml').find('current_observation')
    logging.debug('Returned page from %s:\n%s', url, bsbackup.text )

    fields = ['location', 'station_id', 'latitude', 'longitude', 'observation_time',
              'observation_time_rfc822', 'weather', 'temperature_string', 'temp_f',
              'temp_c', 'relative_humidity', 'wind_string', 'wind_dir', 'wind_degrees',
              'wind_mph', 'wind_kt', 'pressure_string', 'pressure_mb', 'pressure_in',
              'dewpoint_string', 'dewpoint_f', 'dewpoint_c', 'visibility_mi',
              'two_day_history_url', 'ob_url']

    for field in fields:
      try:
        self.backup_obs.obs[field] = bsbackup.find(field).text
      except Exception as exc:
        logging.error('Exception: %s', exc)
        self.backup_obs.obs[field] = ''

    con2 = self.con2.obs
    units = self.data['units']
    con2['location'] = {'lon': self.backup_obs.obs['longitude'],
                        'lat': self.backup_obs.obs['latitude'],
                        'label': self.backup_obs.obs['location']
                       }

    converted_temp1 = wf.convert_units(value=self.backup_obs.obs['temp_c'],
                                       from_unit='C',
                                       to_unit=units['temperature'])
    con2['temperature'] = {'value': converted_temp1,
                           'units': units['temperature'],
                           'label': 'Temperature'
                          }

    converted_temp2 = wf.convert_units(value=self.backup_obs.obs['dewpoint_c'],
                                       from_unit='C',
                                       to_unit=units['temperature'])
    con2['dewpoint'] = {'value': converted_temp2,
                        'units': units['temperature'],
                        'label': 'Dewpoint'
                       }

    con2['humidity'] = {'value': self.backup_obs.obs['relative_humidity'],
                        'units': '%',
                        'label': 'Rel. Humidity'
                       }

    converted_p1 = wf.convert_units(value=self.backup_obs.obs['pressure_mb'],
                                    from_unit='mb',
                                    to_unit=units['pressure'])
    con2['pressure'] = {'value': converted_p1,
                        'units': units['pressure'],
                        'label': 'Pressure'
                       }

    con2['weather'] = self.backup_obs.obs['weather']

    converted_windspeed = wf.convert_units(value=self.backup_obs.obs['wind_kt'],
                                           from_unit='kt',
                                           to_unit=units['velocity'])
    con2['wind'] = {'value': converted_windspeed,
                    'units': units['velocity'],
                    'label': 'Wind Speed'
                   }

    con2['beaufort'] = wf.beaufort_scale(self.data,
                                         speed=con2['wind']['value'],
                                         units=con2['wind']['units']
                                        )
    con2['wind_direction'] = {'value': self.backup_obs.obs['wind_degrees'],
                              'units': 'degrees',
                              'label': 'Wind Direction'
                             }

    logging.debug('Wind dir (backup data) is %s degrees.', self.backup_obs.obs['wind_degrees'])
    wind_dir = self.wind_direction(self.backup_obs.obs['wind_degrees'])
    logging.debug('Wind direction is out of the %s', wind_dir)
    if wind_dir == 'None' or wind_dir is None:
      con2['wind_cardinal'] = 'No data'
    else:
      con2['wind_cardinal'] = 'Out of the {0}'.format(wind_dir)
      logging.debug('Setting backup data wind direction to "%s"', con2['wind_cardinal'])

    con2['timestamp'] = self.backup_obs.obs['observation_time_rfc822']
    con2['windchill'] = {'value': self.wind_chill(self.backup_obs.obs['temp_f'],
                                                  self.backup_obs.obs['wind_mph']),
                         'units': 'F',
                         'label': 'Wind Chill'
                        }

    return self.con2.obs


  def wind_chill(self, temp_f, wind_mph):
    """
    Really should use MetPy for this.

    The NWS wind chill formula uses deg-F and mph.
    It has four components:

    35.74
    + (0.6215 * temp_f)
    - (35.75 * (wind_mph ** 0.16))
    + (0.4275 * temp_f * (wind_mph ** 0.16))

    """
    if temp_f == self.data['defaults']['missing']:
      logging.warn('No temperature data to use. Returning -None-')
      return None

    logging.info('Finding wind chill for %s, with wind at %s mph', temp_f, wind_mph)
    try:
      wind_ch = 35.74 + (0.6215 * float(temp_f))
    except Exception as exc:
      logging.error('Exception computing first wind chill component! %s', exc)
      return None

    try:
      wind_ch = float(wind_ch) - (35.75 * (float(wind_mph) ** 0.16)) + (0.4275 * float(temp_f) * (float(wind_mph) ** 0.16))
      logging.info('Wind chill computed to be %s degrees.', wind_ch)
      return int(wind_ch)
    except Exception as exc:
      logging.error('Exception computing second portion of wind chill! %s', exc)
      return None


  def get_metar(self):
    """
    Hit up https://w1.weather.gov/data/METAR/XXXX.1.txt
    and pull down the latest current conditions METAR data.
    """
    combined_url = os.path.join(self.data['defaults']['metar_url'],
                                '{0}.1.txt'.format(self.data['station'])
                               )
    return wf.make_request(url=combined_url, use_json=False, payload=False)


  def merge_good_observations(self):
    """
    Find missing data in current_conditions and replace/augment it with
    data from backup_dict.
    If all else fails, and if there's a current_conditions['rawMessage'],
    it should be possible to use python-metar to parse the raw message and
    fill in remaining gaps.
    """

    ccp = self.con1.obs
    con2 = self.con2.obs
    for key in self.matchup:
      logging.debug('key: %s', key)
      logging.debug('existing value: %s', ccp[key]['value'])
      if (ccp[key]['value'] is None) or (ccp[key]['value'] == 'None'):
        logging.debug('Testing %s', con2[key]['value'])
        try:
          if con2[key]['value']:
            ccp[key] = con2[key]
            logging.debug('Set value for %s in ccp to %s', key, con2[key])

        except Exception as exc:
          logging.error('Unable to compare or set value %s or %s: %s',
                        con2[key]['value'], ccp[key]['value'], exc)
          continue

    for key in self.textonly:
      if ccp[key] is None or ccp[key] == 'None':
        if con2[key]:
          ccp[key] = con2[key]
          logging.debug('Replaced missing value for %s in ccp with %s', key, con2[key])

    ccp['weather_icon'] = wsvg.assign_icon(ccp['textdescription'],
                                           self.data['defaults']['icon_match'])

    ccp['moon_icon'] = self.moonphase()

    return self.con1.obs


  def format_current_conditions(self):
    """
    Take in the dictionary of current conditions and return a text document.
    """
    cur = self.con1.obs
    ordered = ['temperature', 'dewpoint', 'humidity', 'heatindex', 'windchill',
               'pressure', 'wind_direction', 'wind', 'gusts']

    doctext = str('Conditions as of {0}'.format(wf.prettify_timestamp(cur['timestamp'])))
    for entry in ordered:
      print('Checking key: {0}'.format(entry))
      print('Stored dict: {0}'.format(cur[entry]))
      doctext = wf.quick_doctext(doctext,
                                 '{0}:'.format(cur[entry]['label']),
                                 cur[entry]['value'], cur[entry]['units']
                                )

    doctext = wf.quick_doctext(doctext,
                               '{0}:'.format('Weather'),
                               cur['weather'],
                               ''
                              )
    doctext = wf.quick_doctext(doctext,
                               '{0}:'.format('Wind'),
                               cur['wind_cardinal'],
                               ''
                              )
    return doctext, cur


  def conditions_summary(self):
    """
    Return a dict of consumer-level observations, say, for display on a
    smart mirror or tablet.
    """
    keys = ['dewpoint', 'pressure', 'wind_direction',
            'wind', 'gusts', 'temperature',
            'humidity', 'heatindex']
    summary = dict()
    summary['timestamp'] = self.con1.obs['timestamp']
    for key in keys:
      trump = self.con1.obs[key]  # because it's a tiny dict, that's why
      try:
        summary[key] = '{0}: {1} {2}'.format(trump['label'],
                                             trump['value'],
                                             trump['units'])
      except Exception as exc:
        logging.error('Exception: %s', exc)
        summary[key] = 'none'

    return summary


  def wind_direction(self, azimuth):
    """
    Converts 'wind coming from an azimuth, in degrees', to cardinal directions.
    """
    try:
      azimuth = float(azimuth)
      logging.debug('Converted azimuth to %s', azimuth)  
    except Exception as exc:
      logging.error('Cannot convert azimuth %s to numeric. Returning None. (%s)', azimuth, exc)
      return None

    plusminus = self.data['defaults']['plusminus']  # 11.25
    azdir = self.data['defaults']['azdir']
    #if(azimuth > 360 - plusminus):
    #  azimuth = azimuth - 360
    for az_deg, val in azdir.iteritems():
      az_deg = float(az_deg)
      logging.debug('Checking range %s to %s', az_deg - plusminus, az_deg + plusminus)
      if (az_deg - plusminus < azimuth) and (az_deg + plusminus >= azimuth):
        logging.info('Wind azimuth %s degrees converts to %s', azimuth, val)
        return val

    return 'None'


  def htable_current_conditions(self, tablefile='current_conditions.html'):
    """
    Write out a simple HTML table of the current conditions.
    """

    try:
      with open(os.path.join(self.data['output_dir'], tablefile), 'w') as htmlout:
        htmlout.write('<table>\n')
        for key, value in self.con1.obs.iteritems():
          print('{0}: {1}'.format(key, value))
          htmlout.write('<tr><td>{0}</td><td>{1} {2}</td></tr>\n'.format(value[2],
                                                                         value[0],
                                                                         value[1])
                       )
        htmlout.write('</table>\n')
      return True
    except KeyError as exc:
      print('Exception: {0}'.format(exc))
      return False


  def moonphase(self):
    """
    Get the moon phase and icon name for the moon phase.
    """
    logging.debug('Getting the moon phase.')
    moon_icon = moon_phase.MoonPhase(self.data)
    moon_icon_name = moon_icon.get_moon_phase()
    return moon_icon_name
