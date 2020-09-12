# -*- coding: utf-8 -*-
'''
Weather functions to be used with the NWS radar and weather information
download script.

Jesse Hamner, 2019-2020
'''

from __future__ import print_function

import os
import re
import datetime
import json

from time import sleep
from outage import Outage
import requests
import yaml
import pytz
from bs4 import BeautifulSoup
requests.packages.urllib3.disable_warnings()

def prettify_timestamp(timestamp):
  """
  Make a more user-readable time stamp for current conditions.
  """
  posix_timestamp = datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S+00:00')
  # print('Input timestamp: {0}'.format(timestamp))
  # print('Posix timestamp: {0}'.format(posix_timestamp))
  timetext = datetime.datetime.strftime(posix_timestamp, '%Y-%m-%d, %H:%M:%S UTC')
  # print('Nicely formatted text: {0}'.format(timetext))
  return timetext


def sanity_check(value, numtype='float'):
  """
  Check for an actual value in the argument. If it has one, return a
  formatted text string.
  If it has no value, return a missing value.
  """
  # print('Input value: {0}'.format(value))
  if numtype != 'float':
    try:
      return str('{0:.0f}'.format(float(value)))
    except TypeError:
      return -9999.9

  try:
    return str('{0:6.2f}'.format(float(value)))
  except TypeError:
    return -9999.9


def quick_doctext(doctext, indicator, value, unit=''):
  """
  Convenience function to standardize the output format of a string.
  """
  unitspace = ' '
  if unit == '%':
    unitspace = ''
  return str('{0}\n{1} {2}{3}{4}'.format(doctext, indicator, value, unitspace, unit))


def get_metar(base_url, station):
  """
  Hit up https://w1.weather.gov/data/METAR/XXXX.1.txt
  and pull down the latest current conditions METAR data.
  """
  metar = requests.get(os.path.join(base_url, station),
                       verify=False, timeout=10)
  if metar.status_code != 200:
    print('Response from server was not OK: {0}'.format(metar.status_code))
    return None
  return metar.text


def outage_check(data, filename='outage.txt'):
  """
  Quality assurance check on the weather service :-)
  """

  outage_checker = Outage(data)
  outage_checker.check_outage()
  outage_result = outage_checker.parse_outage()
  outfilepath = os.path.join(data['output_dir'], filename)
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
    except OSError as exc:
      print('OSError-- {0}: {1}'.format(outfilepath, exc))

  return outage_result


def write_json(some_dict, outputdir='/tmp', filename='unknown.json'):
  """
  Write an individual dictionary to a JSON output file.
  """
  filepath = os.path.join(outputdir, filename)
  with open(filepath, 'w') as out_obj:
    print('writing json to {0}'.format(filepath))
    try:
      out_obj.write(json.dumps(some_dict))
      print('raw dict: {0}'.format(some_dict))
      return True
    except Exception as exc:
      print('Ugh: {0}'.format(exc))
      return False


def write_dict(filepath, some_dict):
  """
  Write out a dict to a text file.
  """
  with open(filepath, 'w') as current_alerts:
    for key, value in some_dict.iteritems():
      print('Key for this alert entry: {0}'.format(key))
      current_alerts.write('{0}: {1}\n'.format(key, value))

  return True


def write_text(filepath, some_text):
  """
  Write a text string out to a file.
  """
  with open(filepath, 'w') as text_file:
    print('writing text to {0}'.format(filepath))
    text_file.write(some_text)
  text_file.close()
  return True


def pull_beaufort_scale():
  """
  Pull in the Beaufort scale information, if needed.
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
        row.append(re.sub(r'\s{2,}', ' ', j.text))
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
    except Exception as exc:
      summary[key] = 'none'
      print('Error trying to read summary for key {0}: {1}'.format(key, exc))

  return summary


def wind_direction(azimuth, data):
  """
  Convert "wind coming from an azimuth" to cardinal directions
  """
  try:
    azimuth = float(azimuth)
  except Exception as exc:
    print('Unable to convert azimuth to a numerical value: {0}.\nReturning None.'.format(exc))
    return None

  plusminus = data['defaults']['plusminus'] # 11.25 degrees

  for az_deg, val in data['defaults']['azdir'].iteritems():
    az_deg = float(az_deg)
    if (az_deg - plusminus < azimuth) and (az_deg + plusminus >= azimuth):
      return val

  return 'None'


def get_hydrograph(abbr,
                   hydro_url='https://water.weather.gov/resources/hydrographs/',
                   outputdir='/tmp'):
  """
  Retrieve hydrograph image (png) of the current time and specified location
  Can find these abbreviations at
  https://water.weather.gov/ahps2/hydrograph.php

  Raw data output in XML for a location (here, "cart2"):
  https://water.weather.gov/ahps2/hydrograph_to_xml.php?gage=cart2&output=xml

  """
  filename = '{0}_hg.png'.format(abbr.lower())
  retval = requests.get(os.path.join(hydro_url, filename), verify=False)
  print('retrieving: {0}'.format(retval.url))
  print('return value: {0}'.format(retval))
  if retval.status_code == 200:
    cur1 = open(os.path.join(outputdir, 'current_hydrograph.png'), 'wb')
    cur1.write(retval.content)
    cur1.close()

  return retval


def get_today_vars(timezone='America/Chicago'):
  """
  Get various strings from today's date for use in GOES image retrieval.
  """
  today = datetime.datetime.now()
  utcnow = datetime.datetime.utcnow()
  local_tz = pytz.timezone(timezone)
  return_dict = dict(doy=datetime.datetime.strftime(today, '%j'),
                     year=datetime.datetime.strftime(today, '%Y'),
                     day=datetime.datetime.strftime(today, '%d'),
                     mon=datetime.datetime.strftime(today, '%b'),
                     hour=datetime.datetime.strftime(today, '%H'),
                     minute=datetime.datetime.strftime(today, '%M'),
                     timezone=timezone,
                     offset=local_tz.utcoffset(today).total_seconds()/3600,
                     now=today,
                     utcnow=utcnow,
                     utcdoy=datetime.datetime.strftime(utcnow, '%j'),
                     utcyear=datetime.datetime.strftime(utcnow, '%Y')
                    )
  return return_dict


def htable_current_conditions(con_dict,
                              tablefile='current_conditions.html',
                              outputdir='/tmp/'):
  """
  Write out a simple HTML table of the current conditions.
  """

  try:
    with open(os.path.join(outputdir, tablefile), 'w') as htmlout:
      htmlout.write('<table>\n')
      for key, value in con_dict.iteritems():
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


def load_yaml(directory, filename):
  """
  Load a YAML file in and return the dictionary that is created.
  """
  try:
    with open(os.path.join(directory, filename), 'r') as iyaml:
      return yaml.load(iyaml.read(), Loader=yaml.Loader)
  except Exception as exc:
    print('EXCEPTION -- unable to open yaml settings file: {0}'.format(exc))
    return None


def convert_units(value, from_unit, to_unit, missing=-9999.9):
  """
  As elsewhere, this function depends on use of specific unit conventions,
  as labeled in the settings.yml document (and comments).
  """
  convertme = {'m_s-1':
               {'kph': lambda x: float(x) * 3.6,
                'mph': lambda x: float(x) * 2.23694,
                'kt': lambda x: float(x) * 1.94384
               },
               'kph':
               {'m_s-1': lambda x: float(x) * 0.2778,
                'mph': lambda x: float(x) * 0.62137,
                'kt': lambda x: float(x) * 0.54
               },
               'km_h-1':
               {'m_s-1': lambda x: float(x) * 0.2778,
                'mph': lambda x: float(x) * 0.62137,
                'kt': lambda x: float(x) * 0.54
               },
               'mph':
               {'m_s-1': lambda x: float(x) * 0.4470389,
                'kph': lambda x: float(x) * 1.60934,
                'kt': lambda x: float(x) * 0.869
               },
               'kt':
               {'m_s-1': lambda x: float(x) * 0.514443,
                'mph': lambda x: float(x) * 1.1508,
                'kph': lambda x: float(x) * 1.852
               },
               'mb':
               {'Pa': lambda x: float(x) * 100.0,
                'kPa': lambda x: float(x) * 0.10,
                'bar': lambda x: float(x) * 1000.0,
                'inHg': lambda x: float(x) * 0.02953
               },
               'Pa':
               {'mb': lambda x: float(x) * 1E-2,
                'kPa': lambda x: float(x) * 1E-3,
                'bar': lambda x: float(x) * 1E-5,
                'inHg': lambda x: float(x) * 0.0002953
               },
               'kPa':
               {'mb': lambda x: float(x) * 1E5,
                'Pa': lambda x: float(x) * 1E3,
                'bar': lambda x: float(x) * 0.01,
                'inHg': lambda x: float(x) * 0.2953
               },
               'inHg':
               {'mb': lambda x: float(x) * 33.86390607,
                'Pa': lambda x: float(x) * 3386.390607,
                'bar': lambda x: float(x) * 0.03386390607,
                'kPa': lambda x: float(x) * 3.386390607
               },
               'C':
               {'F': lambda x: (float(x) * 9.0/5.0) + 32.0,
                'R': lambda x: (float(x) * 9.0/5.0) + 491.67,
                'K': lambda x: float(x) + 273.15
               },
               'F':
               {'C': lambda x: (float(x) - 32.0) * 5.0 / 9.0,
                'R': lambda x: float(x) + 491.67,
                'K': lambda x: ((float(x) - 32.0) * 5.0 / 9.0) + 273.15
               },
               'percent':
               {'percent': lambda x: x
               }
              }

  percents = ['percent', 'pct', '%', 'Percent']
  if value == '' or value == 'None' or value is None:
    return missing
  if from_unit in percents or to_unit in percents:
    return value

  if value == missing:
    return missing
  try:
    return convertme[from_unit][to_unit](value)
  except ValueError:
    return None

  return None


def beaufort_scale(data, speed, units='mph'):
  """
  Determine the Beaufort scale ranking of a given wind speed.
  Gusts are NOT used to determine scale rank.
  """
  blist = data['defaults']['beaufort_scale']
  if speed is None or speed == 'None':
    print('Input speed {0} cannot be converted to Beaufort. Returning None.'.format(speed))
    return None
  print('input speed value: {0} {1}'.format(speed, units))
  if units != 'mph':
    speed = convert_units(speed, from_unit=units, to_unit='mph')
  print('output speed value: {0} mph'.format(speed))
  speed = int(speed)
  print('integer speed value: {0} mph'.format(speed))

  for i in blist.keys():
    print('Key: {0}\tmin speed: {1}\tmax speed: {2}'.format(i, blist[i][0], blist[i][1]))
    if int(blist[i][0]) <= speed and speed <= int(blist[i][1]):
      print('Speed ({0} mph) between {1} & {2}. Returning {3}'.format(speed,
                                                                      blist[i][0],
                                                                      blist[i][1],
                                                                      i))
      return int(i)

  return None


def make_request(url, retries=1, payload=False, use_json=True):
  """
  Uniform function for requests.get().
  """
  while retries:
    if payload:
      try:
        response = requests.get(url, params=payload, verify=False, timeout=10)
      except requests.exceptions.ReadTimeout as exc:
        print('Request timed out: {0}. Returning -None-'.format(exc))
    else:
      try:
        response = requests.get(url, verify=False, timeout=10)
      except requests.exceptions.ReadTimeout as exc:
        print('Request timed out: {0}. Returning -None-'.format(exc))
        sleep(2)
        retries = retries - 1
        continue

    try:
      if response:
        pass
    except Exception as exc:
      print('No response to HTTP query. Returning -None-.')

    if response.status_code == 200:
      if use_json is True:
        try:
          return response.json()
        except Exception as exc:
          print('Unable to decode JSON: {0}'.format(exc))
      else:
        try:
          return response.text
        except Exception as exc:
          print('Unable to decode response text: {0}'.format(exc))
    else:
      print('Response from server was not OK: {0}'.format(response.status_code))

    retries = retries - 1

  print('Unsuccessful response ({0}). Returning -None-'.format(response.status_code))
  return None


def populate_alert_counties(somedict):
  """
  Takes in a dict, formatted with state name(s) as the key, with a list
  of county names as the value.
  Returns a populated dictionary with records in the format:
  'countyname': [1, 'CountyAbbr', 'ZoneAbbr', 'StateAbbr']
  """
  returndict = {}

  for key, values in somedict.iteritems():
    statezonelist = get_zonelist(key, 'zone')
    statecountylist = get_zonelist(key, 'county')

    for county in values:
      cabbr = parse_zone_table(county, statecountylist)
      zabbr = parse_zone_table(county, statezonelist)
      returndict[county] = [1, cabbr, zabbr, key]

  return returndict


def get_zonelist(stateabbr, zoneorcounty):
  """
  go to alerts.weather.gov/cap/ and retrieve the forecast zone / county for
  the given name of the county. There are other zone names than only county
  names, like "Central Brewster County", "Chisos Basin", "Coastal Galveston",
  or even "Guadalupe Mountains Above 7000 Feet", so the user can also list
  these as "counties".
  """
  page = '{0}.php'.format(stateabbr)
  rooturl = 'https://alerts.weather.gov/cap/{0}'.format(page)
  x_value = 0
  if zoneorcounty == 'zone':
    x_value = 2
  if zoneorcounty == 'county':
    x_value = 3
  if x_value == 0:
    return None
  payload = {'x': x_value}
  # print('Retrieving: {0} -- with payload {1}'.format(rooturl, payload))
  returned_table = make_request(url=rooturl, payload=payload, use_json=False)
  if returned_table:
    parsed_table = BeautifulSoup(returned_table, 'lxml')
    parsed_table1 = parsed_table.find_all('table')[3]
    rows = parsed_table1.find_all('tr')
    return rows
  return None


def parse_zone_table(county, rows):
  """
  find the zone or county abbreviation within a returned table that includes
  a county name or area name to match.
  """
  for i in rows:
    cells = i.find_all('td')
    if len(cells) > 1:
      if cells[2].text.lower() == county.lower():
        # print('{0}: {1}'.format(cells[2].text.strip(), cells[1].text.strip()))
        return cells[1].text.strip()

  return None
