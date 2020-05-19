"""
obs.py: download and consolidate current conditions data for a given location.
"""

from __future__ import print_function

import os
import re
import logging
import requests
from bs4 import BeautifulSoup
import weather_functions as wf


class WeatherDict(object):
  """
  A dictionary capable of holding relevant data for current weather
  observations.
  """
  
  def __init__(self, data=''):
    self.data = data
    self.obs = dict(temperature=dict(units='', value='', label=''),
                    dewpoint=dict(units='', value='', label=''),        
                    humidity=dict(units='%', value='', label=''),
                    pressure=dict(units='', value='', label=''),
                    weather='',
                    wind=dict(units='', value='', label=''),
                    wind_direction=dict(units='', value='', label=''),
                    gusts=dict(units='', value='', label=''),
                    windchill=dict(units='', value='', label=''),
                    heatindex=dict(units='', value='', label=''),
                    location=dict(lon=0.0, lat=0.0, zip=00000, state='', label=''),
                    wind_cardinal='',
                    textdescription='',
                    metar='',
                    timestamp='',
                    beaufort='',
                   )



class Observation(object):
  """
  Download, parse, error-check, and produce outputs of current conditions
  observations from the NWS for a given location.
  """

  def __init__(self, data=''):
    self.data = data
    self.defaults = data['defaults']
    self.problem = False
    self.observations = WeatherData(data=data) 
    self.backup_obs = WeatherData(data=data)
    self.conditions = ''
    self.metar = ''
    self.con1 = WeatherDict()
    self.con2 = WeatherDict()


  def get_current_conditions(self):
    """
    Take the JSON object from the NWS station and produce a reduced set of
    information for display.
    """
    try:
      response = requests.get(self.defaults['cur_url'].format(station=self.data['station']),
                              verify=False, timeout=10)
    except requests.exceptions.ReadTimeout as e:
      print('Request timed out. Returning -None-')
      self.problem = True
      return None

    if response.status_code == 200:
      try:
        self.observations = response.json()
        return self.observations
      except Exception as e:
        self.problem = True
        print('Unable to decode JSON: {0}'.format(e))
        return None
    print('Response from server was not OK: {0}'.format(response.status_code))
    self.problem = True
    return None


  def sanity_check(self, value, numtype='float'):
    """
    Check for an actual value in the argument. If it has one, return a
    formatted text string.
    If it has no value, return a text string of "None".
    """
    # print('Input value: {0}'.format(value))
    if numtype != 'float':
      try:
        return str('{0:.0f}'.format(float(value)))
      except TypeError:
        return 'None'
  
    try:
      return str('{0:6.2f}'.format(float(value)))
    except TypeError:
      return 'None'


  def quick_doctext(self, doctext, indicator, value, unit=''):
    """
    Convenience function to standardize the output format of a string.
    """
    unitspace = ' '
    if unit == '%':
      unitspace = ''
    return str('{0}\n{1} {2}{3}{4}'.format(doctext, indicator, value, unitspace, unit))


  def get_backup_obs(self):
    """
    Something strange is happening with the data for at least one location --
    the raw message contains complete information, but the returned dictionary
    has missing data. Trying a backup XML feed from w1.weather.gov.
    """
    url = self.data['defaults']['backup_current_obs_url'].format(obs_loc = self.data['station'])
    retpage = requests.get(url, verify=False, timeout=10)
    if retpage.status_code != 200:
      return False

    bsbackup = BeautifulSoup(retpage.text, 'lxml').find('current_observation')
  
    fields = ['location', 'station_id', 'latitude', 'longitude', 'observation_time',
              'observation_time_rfc822', 'weather', 'temperature_string', 'temp_f',
              'temp_c', 'relative_humidity', 'wind_string', 'wind_dir', 'wind_degrees',
              'wind_mph', 'wind_kt', 'pressure_string', 'pressure_mb', 'pressure_in',
              'dewpoint_string', 'dewpoint_f', 'dewpoint_c', 'visibility_mi',
              'two_day_history_url', 'ob_url']

    for f in fields:
      try:
        self.backup_obs[f] = bsbackup.find(f).text
      except:
        self.backup_obs[f] = ''

    self.con2['location'] = {'lon': self.backup_obs['longitude'],
                             'lat': self.backup_obs['latitude'],
                             'label': self.backup_obs['location']
                            }

    self.con2['temperature'] = {'value': self.backup_obs['temp_c'], 
                                'units': 'C',
                                'label': 'Temperature'
                               }

    self.con2['dewpoint'] = {'value': self.backup_obs['dewpoint_c'], 
                             'units': 'C',
                             'label': 'Dewpoint'
                            }

    self.con2['humidity'] = {'value': self.backup_obs['relative_humidity'], 
                             'units': '%',
                             'label': 'Rel. Humidity'
                            }

    self.con2['pressure'] = {'value': self.backup_obs['pressure_mb'], 
                             'units': 'mb',
                             'label': 'Pressure'
                            }

    self.con2['weather'] = self.backup_obs['weather']

    self.con2['wind'] = {'value': self.backup_obs['wind_kt'], 
                         'units': 'kt',
                         'label': 'Wind Speed'
                        }

    self.con2['wind_direction'] = {'value': self.backup_obs['wind_degrees'], 
                                   'units': 'degrees',
                                   'label': 'Wind Direction'
                                  }

    self.con2['wind_cardinal'] = 'Out of the {0}'.format(wind_direction(self.backup_obs['wind_degrees']))

    self.con2['timestamp'] = self.backup_obs['observation_time_rfc822']

    self.con2['windchill'] = {'value': self.wind_chill(self.backup_obs['temp_f'],
                                                       self.backup_obs['wind_mph']),
                              'units': 'F',
                              'label': 'Wind Chill'
                             }

    return self.backup_obs 


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
    try: 
      windchill = 35.74 + (0.6215 * temp_f)
    except:
      return None
      
    try:
      windchill = windchill - (35.75 * (wind_mph ** 0.16)) + (0.4275 * temp_f * (wind_mph ** 0.16))
      return windchill
    except:
      return None
    



  def get_metar(self, base_url, station):
    """
    Hit up https://w1.weather.gov/data/METAR/XXXX.1.txt
    and pull down the latest current conditions METAR data.
    """
    metar = requests.get(os.path.join(base_url, station),
                         verify=False, timeout=10)
    if metar.status_code != 200:
      print('Response from server was not OK: {0}'.format(response1.status_code))
      return None
    self.metar = metar.text
    return metar.text


  def merge_good_observations(self):
    """
    Find missing data in current_conditions and replace/augment it with
    data from backup_dict.
    If all else fails, and if there's a current_conditions['rawMessage'],
    it should be possible to use python-metar to parse the raw message and
    fill in remaining gaps.
    """

    matchup = {'barometricPressure': ['pressure_mb', 'mb'],
               'dewpoint': ['dewpoint_c', 'unit:degC'],
               'temperature': ['temp_c', 'unit:degC'],
               'relativeHumidity': ['relative_humidity', None],
               'windDirection': ['wind_degrees', None],
               'windSpeed': ['wind_kt', 'kt']
               }

    ccp = self.observations['properties']
    for key, alt_key in matchup.iteritems():
      print('key: {0}\tvalue: {1}'.format(key, alt_key))
      print('existing value: {0}'.format(ccp[key]['value']))
      if (ccp[key]['value'] is None) or (ccp[key]['value'] == 'None'):
        print('Testing {0}'.format(self.backup_obs[alt_key[0]]))
        try:
          if self.backup_obs[alt_key[0]]:
            if alt_key[1] is None:
              ccp[key] = self.backup_obs[alt_key[0]]
            # If units are equivalent, ignore and move on:
            elif alt_key[1] == ccp[key]['unitCode']:
              ccp[key] = self.backup_obs[alt_key[0]]
              continue
            else:
            # Must otherwise convert units:
              # convert wind speed in knots to wind speed in m/sec

              # convert pressure from millibars to Pa (mb x 100 = Pa):
              if alt_key[1] == 'mb':
                if ccp[key]['unitCode'] == 'unit:Pa':
                  ccp[key]['value'] = self.backup_obs[alt_key[0]] * 100
                if ccp[key]['unitCode'] == 'unit:inHg':
                  ccp[key]['value'] = self.backup_obs[alt_key[0]] * (1000 / 29.53)

              if alt_key[1] == 'kt':
                if ccp[key]['unitCode'] == 'unit:m_s-1':
                  ccp[key]['value'] = self.backup_obs[alt_key[0]] * 0.514444
                if ccp[key]['unitCode'] == 'unit:mph':
                  ccp[key]['value'] = self.backup_obs[alt_key[0]] * 1.15078

        except Exception as e:
          print('Something barfed: {0}'.format(e))
          continue

    return self.observations


  def format_current_conditions(self, cur, cardinal_directions=True):
    """
    Take in the dictionary of current conditions and return a text document.
    """
    ccdict = {}
    temp_unit = 'F'
    if cur['temperature']['unitCode'] == 'unit:degC':
      temp_unit = 'C'

    ordered = ['temperature', 'dewpoint', 'relativeHumidity', 'heatIndex',
               'barometricPressure', 'windDirection', 'windSpeed', 'windGust']

    doctext = str('Conditions as of {}'.format(prettify_timestamp(cur['timestamp'])))
    key1 = 'temperature'
    ccdict[key1] = [sanity_check(cur[key1]['value'], 'int'), temp_unit, 'Temperature']
    self.con1['temperature'] = ccdict[key1]

    key1 = 'dewpoint'
    ccdict[key1] = [sanity_check(cur[key1]['value'], 'int'), temp_unit, 'Dewpoint']
    self.con1['dewpoint'] = ccdict[key1]

    key1 = 'relativeHumidity'
    ccdict[key1] = [sanity_check(cur[key1]['value'], 'int'), '%', 'Rel. Humidity']
    self.con1['humidity'] = ccdict[key1]

    key1 = 'heatIndex'
    heat_index_value = sanity_check(cur[key1]['value'], 'int')
    if heat_index_value == "None":
      ccdict[key1] = [heat_index_value, '', 'Heat Index']
    else:
      ccdict[key1] = [heat_index_value, temp_unit, 'Heat Index']
    self.con1['heatindex'] = ccdict[key1]


    key1 = 'barometricPressure'
    pressure_unit = re.sub('unit:', '', cur[key1]['unitCode'])
    pressure_value = sanity_check(cur[key1]['value'])
    print('Pressure value: {0}'.format(pressure_value))
 
    if pressure_unit == 'Pa' and pressure_value != "None":
      pressure_value = float(pressure_value) / 1000.0
      pressure_unit = 'kPa'
 
    ccdict[key1] = [pressure_value, pressure_unit, 'Pressure']
    self.con1['pressure'] = ccdict[key1]
 
    key1 = 'windDirection'
    wind_dir_unit = re.sub('unit:', '', cur[key1]['unitCode'])
    if wind_dir_unit == 'degree_(angle)':
      wind_dir_unit = 'degree azimuth'
 
    wind_azimuth = sanity_check(cur[key1]['value'], 'int')
    if wind_azimuth == 'None':
      wind_dir_unit = ''
    if cardinal_directions and wind_azimuth:
      if wind_azimuth == 'None':
        ccdict[key1] = ['No data', '', 'Wind Direction']
      else:
        ccdict[key1] = ['out of the {}'.format(wind_direction(wind_azimuth)), '', 'Wind Direction']
    else:
      ccdict[key1] = [wind_azimuth, wind_dir_unit, 'Wind Direction']
 
    self.con1['wind_direction'] = ccdict[key1]
    self.con1['wind_cardinal'] = 'Out of the {0}'.format(wind_direction(wind_azimuth))
    

    key1 = 'windSpeed'
    wind_speed_unit = re.sub('unit:', '', cur[key1]['unitCode'])
    wind_speed_value = sanity_check(cur[key1]['value'], 'int')
    if wind_speed_unit == 'm_s-1' and wind_speed_value != 'None':
      wind_speed_value = (float(wind_speed_value) / 1000.0) * 3600.0
      wind_speed_unit = 'km / hr'
 
    ccdict[key1] = [wind_speed_value, wind_speed_unit, 'Wind Speed']
    self.con1['wind'] = ccdict[key1]
 
    key1 = 'windGust'
    wind_gust_unit = re.sub('unit:', '', cur[key1]['unitCode'])
    wind_gust_value = sanity_check(cur[key1]['value'], 'int')
    if wind_gust_value == 'None' or wind_gust_value is None:
      wind_gust_unit = ''
    elif wind_gust_unit == 'm_s-1':
      wind_gust_value = (float(wind_gust_value) / 1000.0) * 3600.0
      wind_gust_unit = 'km / hr'
    else:
      wind_gust_unit = '--'
      if not wind_gust_value:
        wind_gust_value = 'No Data'

    ccdict[key1] = [wind_gust_value, wind_gust_unit, 'Wind Gusts']
    self.con1['gusts'] = ccdict[key1]
 
    for entry in ordered:
      doctext = quick_doctext(doctext,
                              '{0}:'.format(ccdict[entry][2]),
                              ccdict[entry][0], ccdict[entry][1]
                             )
 
    return doctext, ccdict


  def write_json(some_dict, outputdir='/tmp', filename='unknown.json'):
    """
    Write an individual dictionary to a JSON output file.
    """
    with open(os.path.join(outputdir, filename), 'w') as out_obj:
      try:
        out_obj.write(json.dumps(some_dict))
        return True
      except:
        return False


  def beaufort_scale(forecast_dict = ''):
    """
  
    """
    b_url = 'https://www.weather.gov/mfl/beaufort'
    pagerequest = requests.get(b_url)
    if pagerequest.status_code != 200:
      print('Response from server was not OK: {0}'.format(pagerequest.status_code))
      return None
    beaufort_page = BeautifulSoup(requests.get(b_url).text, 'html')
    btable = beaufort_page.find('table')
    tablerows = btable.find_all('tr')
    dataset = []
    for i in tablerows:
        row = []
        cells = i.find_all('td')
        for j in cells:
          if re.search(r'\d{1,}-\d{1,}', j.text):
            vals = j.text.split('-')
            row.extend(vals)
          else:
            row.append(re.sub('\s{2,}', ' ', j.text))
        dataset.append(row)
 
    return dataset


  def conditions_summary(conditions):
    """
    Return a dict of consumer-level observations, say, for display on a
    smart mirror or tablet.
    """
    keys = ['timestamp', 'dewpoint', 'barometricPressure', 'windDirection',
            'windSpeed', 'windGust', 'precipitationLastHour', 'temperature',
            'relativeHumidity', 'heatIndex']
    summary = dict()
    for key in keys:
      try:
        summary[key] = conditions['properties'][key]
      except:
        summary[key] = 'none'

    return summary


  def wind_direction(self, azimuth):
    """
    Convert "wind coming from an azimuth" to cardinal directions
    """
    try:
      azimuth = float(azimuth)
    except:
      print('Unable to convert azimuth to a numerical value. Returning None.')
      return None

    plusminus = 11.25
    azdir = {'0.0': 'N',
             '22.5': 'NNE',
             '45.0': 'NE',
             '67.5': 'ENE',
             '90.0': 'E',
             '112.5': 'ESE',
             '135.0': 'SE',
             '157.5': 'SSE',
             '180.0': 'S',
             '202.5': 'SSW',
             '225.0': 'SW',
             '247.5': 'WSW',
             '270.0': 'W',
             '292.5': 'WNW',
             '315.0': 'NW',
             '337.5': 'NNW'}

    for az_deg, val in azdir.iteritems():
      az_deg = float(az_deg)
      if (az_deg - plusminus < azimuth) and (az_deg + plusminus >= azimuth):
        return val
  
    return 'None'


  def htable_current_conditions(self, tablefile='current_conditions.html'):
    """
    Write out a simple HTML table of the current conditions.
    """
  
    try:
      with open(os.path.join(self.data['output_dir'], tablefile), 'w') as htmlout:
        htmlout.write('<table>\n')
        for key, value in self.observations['properties'].iteritems():
          print('{0}: {1}'.format(key, value))
          htmlout.write('<tr><td>{0}</td><td>{1} {2}</td></tr>\n'.format(value[2],
                                                                         value[0],
                                                                         value[1])
                       )
        htmlout.write('</table>\n')
      return True
    except KeyError as e:
      print('Exception: {0}'.format(e))
      return False


  def wind_direction_icon(self, sourcepath='static/icons/weather-icons-master/svg'):
    """
    Generate the html for the appropriately rotated SVG file for 
    the wind direction.
    """

    filename = 'wi-wind-deg.svg'
    fp = os.path.join(sourcepath, filename)
    

    img_html = '''<img src="{0}" width="40" height="40" fill="white"
        transform="rotate(100,20,20)" />'''.format(fp)
    print(img_html)

    return img_html
