'''
Weather functions to be used with the NWS radar and weather information
download script.

Jesse Hamner, 2019-2020
'''

from __future__ import print_function

import os
import re
import datetime
import requests
from bs4 import BeautifulSoup
requests.packages.urllib3.disable_warnings()


def prettify_timestamp(timestamp):
  """
  Make a more user-readable time stamp for current conditions.
  """
  posix_timestamp = datetime.datetime.strptime(timestamp,'%Y-%m-%dT%H:%M:%S+00:00')
  #print('Input timestamp: {0}'.format(timestamp))
  #print('Posix timestamp: {0}'.format(posix_timestamp))
  timetext = datetime.datetime.strftime(posix_timestamp, '%Y-%m-%d, %H:%M:%S UTC')
  #print('Nicely formatted text: {0}'.format(timetext))
  return timetext


def check_graphics(graphics_list, root_url, dest='/tmp', radar='FWS'):
  """
  Ensure that the needed graphics are available in /tmp/ -- and if needed.
  (re-) download them from the NWS.
  """

  for suf in graphics_list:
    filename = '{0}'.format(suf.format(radar=radar))
    filename = filename.split('/')[-1]
    localpath = os.path.join(dest, filename)
    if os.path.isfile(localpath) is False:
      print('Need to retrieve {0}'.format(filename))
      graphic = requests.get(os.path.join(root_url, suf.format(radar=radar)),
                             verify=False)
      with open(os.path.join(dest, filename), 'wb') as output:
        output.write(graphic.content)
      output.close()


def get_current_conditions(url, station):
  """
  Take the JSON object from the NWS station and produce a reduced set of
  information for display.
  """
  response = requests.get(url.format(station=station), verify=False)
  if response.status_code == 200:
    conditions = response.json()
    return conditions
  print('Response from server was not OK: {0}'.format(response.status_code))
  return None


def sanity_check(value, numtype='float'):
  """
  Check for an actual value in the argument. If it has one, return a formatted
  text string. If it has no value, return a text string of "None".
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


def format_current_conditions(cur, cardinal_directions=True):
  """
  Take in the dictionary of current conditions and return a text document.
  """
  temp_unit = "F"
  if cur['temperature']['unitCode'] == 'unit:degC':
    temp_unit = "C"

  doctext = str('Conditions as of {}'.format(prettify_timestamp(cur['timestamp'])))
  temp_value = sanity_check(cur['temperature']['value'], 'int')
  doctext = str('{}\nTemperature: {} {}'.format(doctext, temp_value, temp_unit))

  dewpoint_value = sanity_check(cur['dewpoint']['value'], 'int')
  doctext = str('{0}\nDewpoint: {1} {2}'.format(doctext, dewpoint_value, temp_unit))

  rh_value = sanity_check(cur['relativeHumidity']['value'], 'int')
  doctext = str('{}\nRel. Humidity: {}%'.format(doctext, rh_value))

  heat_index_value = sanity_check(cur['heatIndex']['value'], 'int')
  if heat_index_value == "None":
    heat_index_string = heat_index_value
  else:
    heat_index_string = str('{} {}'.format(heat_index_value, temp_unit))
  doctext = str('{}\nHeat Index: {}'.format(doctext, heat_index_string))

  pressure_unit = re.sub('unit:', '', cur['barometricPressure']['unitCode'])
  pressure_value = sanity_check(cur['barometricPressure']['value'])
  doctext = str('{}\nPressure: {} {}'.format(doctext, pressure_value, pressure_unit))

  wind_dir_unit = re.sub('unit:', '', cur['windDirection']['unitCode'])
  if wind_dir_unit == 'degree_(angle)':
    wind_dir_unit = 'degree azimuth'
  
  wind_azimuth = sanity_check(cur['windDirection']['value'], 'int')
  if cardinal_directions and wind_azimuth:
    wind_string = str('out of the {}'.format(wind_direction(wind_azimuth)))
  else: 
    wind_string = str('{} {}'.format(wind_azimuth, wind_dir_unit))
  doctext = str('{}\nWind Direction: {}'.format(doctext, wind_string))
  
  wind_speed_unit = re.sub('unit:', '', cur['windSpeed']['unitCode'])
  wind_speed_value = sanity_check(cur['windSpeed']['value'], 'int')
  if wind_speed_unit == 'm_s-1' and wind_speed_value != 'None':
    wind_speed_value = (float(wind_speed_value) / 1000.0) * 3600.0
    wind_speed_unit = 'km / hr'
  doctext = str('{}\nWind speed: {} {}'.format(doctext, wind_speed_value, wind_speed_unit))

  return doctext


def get_weather_radar(url, station):
  """
  Using the NWS radar station abbreviation, retrieve the current radar image
  and world file from the NWS.
  """
  response1 = requests.get(url.format(station=station, image='N0R_0.gfw'),
                           verify=False)
  if response1.status_code != 200:
    print('Response from server was not OK: {0}'.format(response1.status_code))
    return None
  cur1 = open('/tmp/current_image.gfw', 'w')
  cur1.write(response1.text)
  cur1.close()

  response2 = requests.get(url.format(station=station, image='N0R_0.gif'),
                           verify=False)
  if response2.status_code != 200:
    print('Response from server was not OK: {0}'.format(response2.status_code))
    return None

  cur2 = open('/tmp/current_image.gif', 'wb')
  cur2.write(response2.content)
  cur2.close()

  return True


def get_warnings_box(url, station):
  """
  Retrieve the severe weather graphics boxes (suitable for overlaying)
  from the NWS for the specified locale.
  """
  warnings = 'Warnings'
  response = requests.get(url.format(station=station, warnings=warnings),
                          verify=False)
  cur = open('/tmp/current_warnings.gif', 'wb')
  cur.write(response.content)
  cur.close()

  return 0


def get_hwo(url, params_dict, outputfile='current_hwo.txt'):
  """
  Get the HTML-only Hazardous Weather Outlook. The raw text of this statement
  is available inside

  <body>
    <div id="local"> <div id="localcontent">
    <pre class="glossaryProduct">
    (Text is here)
    </pre>
  """

  response = requests.get(url, params=params_dict, verify=False)
  html = response.text
  soup = BeautifulSoup(html, 'html.parser')
  pres = soup.body.find_all('pre')
  for pretag in pres:
    hwo_text = pretag.get_text()
    if len(hwo_text) > 200:
      #print('{0}'.format(pretag.get_text()))

      cur = open(os.path.join('/tmp/', outputfile), 'w')
      cur.write(hwo_text)
      cur.close()
      return hwo_text

  return None


def split_hwo(bodytext):
  """
  Pull out today's hazardous weather outlook and spotter activation notice.
  Return a slightly more compact text block of the two paragraphs.

  """
  returntext = ''
  #print('Raw body text of HWO: \n{0}'.format(bodytext))

  dayone = re.search(r'(\.DAY ONE.*?)(\.DAYS TWO THROUGH SEVEN)', bodytext, re.DOTALL)
  if dayone:
    hwotext = re.sub(r'\n\n$', '', dayone.group(1))

  #bodytext = re.sub(r'(\.DAY ONE.*?)\n\n', r'\g<1>\n', bodytext)
  #bodytext = re.sub(r'(\.SPOTTER INFORMATION STATEMENT.*?)\n\n', r'\g<1>\n', bodytext)
  spotter = re.search(r'(\.SPOTTER INFORMATION STATEMENT.*?)(\s*\$\$)', bodytext, re.DOTALL)
  if spotter:
    spottertext = re.sub(r'\n\n$', '', spotter.group(1))

  if hwotext:
    returntext = '{0}{1}\n\n'.format(returntext, hwotext)
  if spottertext:
    returntext = '{0}{1}\n\n'.format(returntext, spottertext)

  returntext = re.sub(r'\n\n$', '', returntext)
  return returntext


def print_current_conditions(conditions):
  """
  Print the entire JSON of observations from the 'conditions' dictionary.
  """
  if isinstance(conditions, dict):
    print('conditions returned as a dictionary. Going ahead.')
  for key, value in conditions.iteritems():
    if isinstance(value, dict):
      print('Key: {0}'.format(key))
      for key1, val1 in value.iteritems():
        print('{0}: {1}'.format(key1, val1))

    elif isinstance(value, list):
      for i in value:
        print('  Item: {0}'.format(i))

    else:
      print('  Key: {0}\n    Value: {1}'.format(key, value))

  return 0


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


def check_outage(url, params_dict):
  """
  Check a webpage for information about any outages at the radar site.
  The product is called a 'Free Text Message' (FTM).
  'https://forecast.weather.gov/product.php?site=NWS
  &issuedby=FWS&product=FTM&format=CI&version=1&glossary=0'
  The information is identical to the HWO call.
  """

  response = requests.get(url, params=params_dict, verify=False)
  html = response.text
  #print('Response text: {0}'.format(html))
  soup = BeautifulSoup(html, 'html.parser')
  pres = soup.body.find_all('pre')
  for pretag in pres:
    ftm_text = pretag.get_text()
    # print('ftm_text: {0}'.format(ftm_text))
    if len(ftm_text) > 100:
      return ftm_text.split('\n')
  return None


def parse_outage(bodytext):
  """
  Read the outage text, if any, and determine:
  - should it be displayed (i.e. is it timely and current?)
  - what text is relevant (but default to "all of the text")
  """
  if not bodytext:
    print('No outage text seen. Returning -None-')
    return None
  message_date = ''
  return_text = ''
  for line in bodytext:
    line.strip()
    if re.search(r'^\s*$', line):
      continue
    if re.search(r'^\s*FTM|^000\s*$|^NOUS', line):
      continue
    #print('line: {0}'.format(line))
    if re.search('MESSAGE DATE:', line, flags=re.I):
      message_date = re.sub(r'MESSAGE DATE:\s+', '', line, flags=re.I)
      print('Date of issue: {0}'.format(message_date))
      dateobj = datetime.datetime.strptime(message_date, '%b %d %Y %H:%M:%S')
      today = datetime.datetime.now()
      if (today - dateobj) > datetime.timedelta(days=1):
        print('Alert is older than one day -- ignoring.')
        return None
      else:
        return_text = str('{0}\nNWS FTM NOTICE:'.format(return_text))

    else:
      return_text = str('{0} {1}'.format(return_text, line))

  if message_date:
    return_text = re.sub('  ', ' ', return_text)
    return return_text.strip()
  return None


def get_current_alerts(url, params_dict):
  """
  Get current watches, warnings, or advisories for a county or zone.
  Check https://alerts.weather.gov/cap/wwaatmget.php?x=TXC121&y=1 as example.
  For abbreviations, see https://alerts.weather.gov/
  The ATOM and CAP feeds are updated about every two minutes.
  """

  response = requests.get(url, params=params_dict, verify=False)
  if response.status_code == 200:
    conditions = response.text
    return conditions
  print('Response from server was not OK: {0}'.format(response.status_code))
  return None

  # Parse the feed for relevant content:

  # Write a simple formatted text file to /tmp/:


def wind_direction(azimuth):
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

  for az, val in azdir.iteritems():
    az = float(az)
    if (az - plusminus < azimuth) and (az + plusminus >= azimuth):
      return val

  return 'None'
