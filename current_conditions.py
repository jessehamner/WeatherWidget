#!/usr/bin/env python
"""

See https://www.weather.gov/jetstream/gis
https://radar.weather.gov/GIS.html
https://radar.weather.gov/ridge/Overlays/
https://mesonet.agron.iastate.edu/GIS/legends/TR0.gif



"""

from __future__ import print_function

import sys
import os
import json
import re
import requests
from bs4 import BeautifulSoup


STATION = 'KDTO'
CUR_URL = 'https://api.weather.gov/stations/{station}/observations/current'
RADAR_STATION = 'FWS'
NWS_ABBR = 'FWD'
RADAR_URL = 'https://radar.weather.gov/ridge/RadarImg/N0R/{station}_{image}'
WARNINGS_URL = 'https://radar.weather.gov/ridge/Warnings/Short/{station}_{warnings}_0.gif'
HWO_URL = 'https://forecast.weather.gov/product.php?site=DDC&issuedby={abbr}&product=HWO&format=txt&version=1&glossary=0'

SHORT_RANGE_COUNTIES = 'https://radar.weather.gov/ridge/Overlays/County/Short/{radar}_County_Short.gif'
SHORT_RANGE_HIGHWAYS = 'https://radar.weather.gov/ridge/Overlays/Highways/Short/{radar}_Highways_Short.gif'
SHORT_RANGE_MED_CITIES = 'https://radar.weather.gov/ridge/Overlays/Cities/Short/{radar}_City_250K_Short.gif'
SHORT_RANGE_LRG_CITIES = 'https://radar.weather.gov/ridge/Overlays/Cities/Short/{radar}_City_1M_Short.gif'
SHORT_RANGE_SML_CITIES = 'https://radar.weather.gov/ridge/Overlays/Cities/Short/{radar}_City_25K_Short.gif'
SHORT_RANGE_RING = 'https://radar.weather.gov/ridge/Overlays/RangeRings/Short/{radar}_RangeRing_Short.gif'
SHORT_RANGE_RIVERS = 'https://radar.weather.gov/ridge/Overlays/Rivers/Short/{radar}_Rivers_Short.gif'
SHORT_RANGE_TOPO = 'https://radar.weather.gov/ridge/Overlays/Topo/Short/{radar}_Topo_Short.jpg'


def get_current_conditions(url, station):
  """

  """
  response = requests.get(url.format(station=station))
  if response.status_code == 200:
    # print('Response from server: {0}'.format(response.status_code))
    # print('JSON: {0}'.format(response.json()))
    conditions = response.json() 
    return conditions
  
  return None


def get_weather_radar(url, station):
  """

  """
  response1 = requests.get(url.format(station=station, image='N0R_0.gfw'))
  response2 = requests.get(url.format(station=station, image='N0R_0.gif'))
  cur1 = open('/tmp/current_image.gif', 'wb')
  cur1.write(response2.content)
  cur1.close()

  cur2 = open('/tmp/current_image.gfw', 'w')
  cur2.write(response1.text)
  cur2.close()

  return 0


def get_warnings_box(url, station):
  """

  """
  warnings = 'Warnings'
  response = requests.get(url.format(station=station, warnings=warnings))
  cur = open('/tmp/current_warnings.gif', 'wb')
  cur.write(response.content)
  cur.close()
  
  return 0


def get_hwo(url, abbr):
  """
  Get the HTML-only Hazardous Weather Outlook. The raw text of this statement
  is available inside

  <body>
    <div id="local"> <div id="localcontent">
    <pre class="glossaryProduct">
    (Text is here)
    </pre>
  """

  response = requests.get(url.format(abbr=abbr))
  html = response.text
  soup = BeautifulSoup(html, 'html.parser')
  # body = soup.body
  # print(body)
  
  pres = soup.body.find_all('pre')
  for p in pres:
    hwo_text = p.get_text()
    if len(hwo_text) > 200:
      #print('{0}'.format(p.get_text()))

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
  bodytext = re.sub('(\.DAY ONE.*.?)\n\n', '\g<1>\n', bodytext)

  bodytext = re.sub('(\.SPOTTER INFORMATION STATEMENT.*.?)\n\n', '\g<1>\n', bodytext)

  # print('body text of HWO: {0}'.format(bodytext))
  hwolist = bodytext.split('\n\n')
  for i in hwolist:
    if re.search('\.DAY ONE', i):
      returntext = '{0}{1}\n\n'.format(returntext, i)
    if re.search('\.SPOTTER INFORMATION STATEMENT', i):
      returntext = '{0}{1}\n\n'.format(returntext, i)

  if returntext:
    return returntext

  return None


def print_current_conditions(conditions):
  """

  """

  for key, value in conditions.iteritems():
    if isinstance(value, dict):
      print('Key: {0}'.format(key))
      for k1, v1 in value.iteritems():
        print('{1}: {2}'.format(key, k1, v1))

    elif isinstance(value, list):
      for i in value:
        print('  Item: {0}'.format(i))

    else:
      print('  Key: {0}\n    Value: {1}'.format(key, value))

  return 0


def main():
  """

  """

  conditions = get_current_conditions(CUR_URL, STATION)
  #print_current_conditions(conditions)

  get_weather_radar(RADAR_URL, RADAR_STATION)
  get_warnings_box(WARNINGS_URL, RADAR_STATION)
  hwo_statement = get_hwo(HWO_URL, NWS_ABBR)
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
