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
requests.packages.urllib3.disable_warnings()
from bs4 import BeautifulSoup


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


def format_current_conditions(cur):
  """
  Take in the dictionary of current conditions and return a text document.
  """
  temp_unit = "F"
  if cur['temperature']['unitCode'] == 'unit:degC':
    temp_unit = "C"

  pressure_unit = re.sub('unit:', '', cur['barometricPressure']['unitCode'])
  
  doctext = str('Conditions as of {}'.format(cur['timestamp'],
      temp_unit))
  doctext = str('{}\nTemperature: {:3.0f} {}'.format(doctext,
      cur['temperature']['value'], temp_unit))
  doctext = str('{}\nDewpoint: {:3.0f} {}'.format(doctext,
      cur['dewpoint']['value'], temp_unit))
  doctext = str('{}\nRel. Humidity: {:3.0f}%'.format(doctext,
      cur['relativeHumidity']['value']))

  heat_index = "None"
  if cur['heatIndex']['value']:
    heat_index = str('{:3.0f} {}'.format(cur['heatIndex']['value'], temp_unit))
  doctext = str('{}\nHeat Index: {}'.format(doctext,
      cur['heatIndex']['value'], heat_index))

  doctext = str('{}\nPressure: {:6.0f} {}'.format(doctext,
      cur['barometricPressure']['value'], pressure_unit))

  wind_direction_unit = re.sub('unit:', '', cur['windDirection']['unitCode'])
  if wind_direction_unit == 'degree_(angle)':
    wind_direction_unit = 'degree azimuth'

  doctext = str('{}\nWind Direction: {:3.0f} {}'.format(doctext,
      cur['windDirection']['value'], wind_direction_unit))

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
