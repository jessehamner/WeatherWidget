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
import requests
from bs4 import BeautifulSoup

RADAR_STATION = 'FWS'
NWS_ABBR = 'FWD'
HWO_DICT = {
    'site': 'DDC',
    'issuedby': NWS_ABBR,
    'product': 'HWO',
    'format': 'txt',
    'version': 1,
    'glossary': 0
    }

STATION = 'KDTO'
CUR_URL = 'https://api.weather.gov/stations/{station}/observations/current'
RADAR_URL = 'https://radar.weather.gov/ridge/RadarImg/N0R/{station}_{image}'
WARNINGS_URL = 'https://radar.weather.gov/ridge/Warnings/Short/{station}_{warnings}_0.gif'
HWO_URL = 'https://forecast.weather.gov/product.php'

WEATHER_URL_ROOT = 'https://radar.weather.gov/ridge/Overlays'
SHORT_RANGE_COUNTIES = 'County/Short/{radar}_County_Short.gif'
SHORT_RANGE_HIGHWAYS = 'Highways/Short/{radar}_Highways_Short.gif'
SHORT_RANGE_MED_CITIES = 'Cities/Short/{radar}_City_250K_Short.gif'
SHORT_RANGE_LRG_CITIES = 'Cities/Short/{radar}_City_1M_Short.gif'
SHORT_RANGE_SML_CITIES = 'Cities/Short/{radar}_City_25K_Short.gif'
SHORT_RANGE_RING = 'RangeRings/Short/{radar}_RangeRing_Short.gif'
SHORT_RANGE_RIVERS = 'Rivers/Short/{radar}_Rivers_Short.gif'
SHORT_RANGE_TOPO = 'Topo/Short/{radar}_Topo_Short.jpg'


def check_graphics(dest='/tmp', radar='FWS'):
  """
  Ensure that the needed graphics are available in /tmp/ -- and if needed.
  (re-) download them from the NWS.
  """

  for suf in [SHORT_RANGE_COUNTIES, SHORT_RANGE_HIGHWAYS, SHORT_RANGE_MED_CITIES,
              SHORT_RANGE_LRG_CITIES, SHORT_RANGE_SML_CITIES, SHORT_RANGE_RING,
              SHORT_RANGE_RIVERS, SHORT_RANGE_TOPO]:
    filename = '{0}'.format(suf.format(radar=radar))
    filename = filename.split('/')[-1]
    localpath = os.path.join(dest, filename)
    if os.path.isfile(localpath) is False:
      print('Need to retrieve {0}'.format(filename))
      graphic = requests.get(os.path.join(WEATHER_URL_ROOT, suf.format(radar=radar)))
      with open(os.path.join(dest, filename), 'wb') as output:
        output.write(graphic.content)
      output.close()


def get_current_conditions(url, station):
  """
  Take the JSON object from the NWS station and produce a reduced set of
  information for display.
  """
  response = requests.get(url.format(station=station))
  if response.status_code == 200:
    conditions = response.json()
    return conditions
  print('Response from server was not OK: {0}'.format(response.status_code))
  return None


def get_weather_radar(url, station):
  """
  Using the NWS radar station abbreviation, retrieve the current radar image
  and world file from the NWS.
  """
  response1 = requests.get(url.format(station=station, image='N0R_0.gfw'))
  if response1.status_code != 200:
    print('Response from server was not OK: {0}'.format(response1.status_code))
    return None
  cur1 = open('/tmp/current_image.gfw', 'w')
  cur1.write(response1.text)
  cur1.close()

  response2 = requests.get(url.format(station=station, image='N0R_0.gif'))
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
  response = requests.get(url.format(station=station, warnings=warnings))
  cur = open('/tmp/current_warnings.gif', 'wb')
  cur.write(response.content)
  cur.close()

  return 0


def get_hwo(url, params_dict):
  """
  Get the HTML-only Hazardous Weather Outlook. The raw text of this statement
  is available inside

  <body>
    <div id="local"> <div id="localcontent">
    <pre class="glossaryProduct">
    (Text is here)
    </pre>
  """

  response = requests.get(url, params=params_dict)
  html = response.text
  soup = BeautifulSoup(html, 'html.parser')
  pres = soup.body.find_all('pre')
  for pretag in pres:
    hwo_text = pretag.get_text()
    if len(hwo_text) > 200:
      #print('{0}'.format(pretag.get_text()))

      cur = open('/tmp/current_hwo.txt', 'w')
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
  bodytext = re.sub(r'(\.DAY ONE.*.?)\n\n', r'\g<1>\n', bodytext)

  bodytext = re.sub(r'(\.SPOTTER INFORMATION STATEMENT.*.?)\n\n', r'\g<1>\n', bodytext)

  # print('body text of HWO: {0}'.format(bodytext))
  hwolist = bodytext.split('\n\n')
  for i in hwolist:
    if re.search(r'\.DAY ONE', i):
      returntext = '{0}{1}\n\n'.format(returntext, i)
    if re.search(r'\.SPOTTER INFORMATION STATEMENT', i):
      returntext = '{0}{1}\n\n'.format(returntext, i)

  if returntext:
    return returntext

  return None


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
    summary[key] = conditions['properties'][key]

  return summary


def main():
  """
  - Check to see that the needed graphics are available. If not, get them.
  - Get the radar image
  - Get the warnings boxes graphic
  - Get today's hazardous weather outlook statement and parse it
  - Write out the files to helpful locations.
  - Next: should run the getweather.sh shell script, that overlays/composites
    the weather graphics.

  """

  check_graphics()
  conditions = get_current_conditions(CUR_URL, STATION)
  sum_con = conditions_summary(conditions)

  get_weather_radar(RADAR_URL, RADAR_STATION)
  get_warnings_box(WARNINGS_URL, RADAR_STATION)
  hwo_statement = get_hwo(HWO_URL, HWO_DICT)
  hwo_today = split_hwo(hwo_statement)
  if hwo_today is not None:
    hwo = re.sub('.DAY ONE', 'Hazardous Weather Outlook', hwo_today)
    print(hwo)
    with open('/tmp/today_hwo.txt', 'w') as today_hwo:
      today_hwo.write(hwo)
    today_hwo.close()

  return 0


if __name__ == '__main__':
  sys.exit(main())
