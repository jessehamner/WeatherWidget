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
import svgwrite
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


def check_graphics(graphics_list, root_url, outputdir='/tmp', radar='FWS'):
  """
  Ensure that the needed graphics are available in /tmp/ -- and if needed.
  (re-) download them from the NWS.
  """

  for suf in graphics_list:
    filename = '{0}'.format(suf.format(radar=radar))
    filename = filename.split('/')[-1]
    localpath = os.path.join(outputdir, filename)
    if os.path.isfile(localpath) is False:
      print('Need to retrieve {0}'.format(filename))
      graphic = requests.get(os.path.join(root_url, suf.format(radar=radar)),
                             verify=False, timeout=10)
      with open(os.path.join(outputdir, filename), 'wb') as output:
        output.write(graphic.content)
      output.close()
  return True


def get_current_conditions(url, station):
  """
  Take the JSON object from the NWS station and produce a reduced set of
  information for display.
  """
  try:
    response = requests.get(url.format(station=station), verify=False, timeout=10)
  except requests.exceptions.ReadTimeout as e:
    print('Request timed out. Returning -None-')
    return None

  if response.status_code == 200:
    conditions = response.json()
    return conditions
  print('Response from server was not OK: {0}'.format(response.status_code))
  return None


def sanity_check(value, numtype='float'):
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


def quick_doctext(doctext, indicator, value, unit=''):
  """
  Convenience function to standardize the output format of a string.
  """
  unitspace = ' '
  if unit == '%':
    unitspace = ''
  return str('{0}\n{1} {2}{3}{4}'.format(doctext, indicator, value, unitspace, unit))


def get_backup_obs(data, station_abbr):
  """
  Something strange is happening with the data for at least one location --
  the raw message contains complete information, but the returned dictionary 
  has missing data. Trying a backup XML feed from w1.weather.gov.
  """
  retpage = requests.get(data['backup_current_obs_url'].format(obs_loc = data['station']))
  if retpage.status_code != 200:
    return False

  bsbackup = BeautifulSoup(retpage.text, 'lxml').find('current_observation')
  return_dict = {}
  fields = ['location', 'station_id', 'latitude', 'longitude', 'observation_time',
            'observation_time_rfc822', 'weather', 'temperature_string', 'temp_f',
            'temp_c', 'relative_humidity', 'wind_string', 'wind_dir', 'wind_degrees',
            'wind_mph', 'wind_kt', 'pressure_string', 'pressure_mb', 'pressure_in',
            'dewpoint_string', 'dewpoint_f', 'dewpoint_c', 'visibility_mi',
            'two_day_history_url', 'ob_url']

  for f in fields:
    try:
      return_dict[f] = bsbackup.find(f).text
    except:
      return_dict[f] = ''


  return return_dict


def merge_good_observations(backup_dict, current_conditions):
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
  
  ccp = current_conditions['properties']
  for key, alt_key in matchup.iteritems():
    print('key: {0}\tvalue: {1}'.format(key, alt_key))
    print('existing value: {0}'.format(ccp[key]['value']))
    if (ccp[key]['value'] is None) or (ccp[key]['value'] == 'None'):
      print('Testing {0}'.format(backup_dict[alt_key[0]]))
      try:
        if backup_dict[alt_key[0]]:
          if alt_key[1] is None:
            ccp[key] = backup_dict[alt_key[0]]
          # If units are equivalent, ignore and move on:
          elif alt_key[1] == ccp[key]['unitCode']:
            ccp[key] = backup_dict[alt_key[0]]
            continue
          else:
          # Must otherwise convert units:
            # convert wind speed in knots to wind speed in m/sec

            # convert pressure from millibars to Pa (mb x 100 = Pa):
            if alt_key[1] == 'mb':
              if ccp[key]['unitCode'] == 'unit:Pa':
                ccp[key]['value'] = backup_dict[alt_key[0]] * 100
              if ccp[key]['unitCode'] == 'unit:inHg':
                ccp[key]['value'] = backup_dict[alt_key[0]] * (1000 / 29.53)
              
            if alt_key[1] == 'kt':
              if ccp[key]['unitCode'] == 'unit:m_s-1':
                ccp[key]['value'] = backup_dict[alt_key[0]] * 0.514444
              if ccp[key]['unitCode'] == 'unit:mph':
                ccp[key]['value'] = backup_dict[alt_key[0]] * 1.15078

      except Exception as e:
        print('Something barfed: {0}'.format(e))
        continue
            
  return current_conditions
             




def format_current_conditions(cur, cardinal_directions=True):
  """
  Take in the dictionary of current conditions and return a text document.
  """
  ccdict = {}
  temp_unit = 'F'
  if cur['temperature']['unitCode'] == 'unit:degC':
    temp_unit = 'C'

  ordered = ['temperature', 'dewpoint', 'relativeHumidity', 'heatIndex',
             'barometricPressure', 'windDirection', 'windSpeed']

  doctext = str('Conditions as of {}'.format(prettify_timestamp(cur['timestamp'])))

  key1 = 'temperature'
  ccdict[key1] = [sanity_check(cur[key1]['value'], 'int'), temp_unit, 'Temperature']

  key1 = 'dewpoint'
  ccdict[key1] = [sanity_check(cur[key1]['value'], 'int'), temp_unit, 'Dewpoint']

  key1 = 'relativeHumidity'
  ccdict[key1] = [sanity_check(cur[key1]['value'], 'int'), '%', 'Rel. Humidity']

  key1 = 'heatIndex'
  heat_index_value = sanity_check(cur[key1]['value'], 'int')
  if heat_index_value == "None":
    ccdict[key1] = [heat_index_value, '', 'Heat Index']
  else:
    ccdict[key1] = [heat_index_value, temp_unit, 'Heat Index']

  key1 = 'barometricPressure'
  pressure_unit = re.sub('unit:', '', cur[key1]['unitCode'])
  pressure_value = sanity_check(cur[key1]['value'])
  print('Pressure value: {0}'.format(pressure_value))

  if pressure_unit == 'Pa' and pressure_value != "None":
    pressure_value = float(pressure_value) / 1000.0
    pressure_unit = 'kPa'

  ccdict[key1] = [pressure_value, pressure_unit, 'Pressure']

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

  key1 = 'windSpeed'
  wind_speed_unit = re.sub('unit:', '', cur[key1]['unitCode'])
  wind_speed_value = sanity_check(cur[key1]['value'], 'int')
  if wind_speed_unit == 'm_s-1' and wind_speed_value != 'None':
    wind_speed_value = (float(wind_speed_value) / 1000.0) * 3600.0
    wind_speed_unit = 'km / hr'

  ccdict[key1] = [wind_speed_value, wind_speed_unit, 'Wind Speed']

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


def get_weather_radar(url, station, outputdir='/tmp'):
  """
  Using the NWS radar station abbreviation, retrieve the current radar image
  and world file from the NWS.
  """
  response1 = requests.get(url.format(station=station, image='N0R_0.gfw'),
                           verify=False, timeout=10)
  if response1.status_code != 200:
    print('Response from server was not OK: {0}'.format(response1.status_code))
    return None
  cur1 = open(os.path.join(outputdir, 'current_image.gfw'), 'w')
  cur1.write(response1.text)
  cur1.close()

  response2 = requests.get(url.format(station=station, image='N0R_0.gif'),
                           verify=False, timeout=10)
  if response2.status_code != 200:
    print('Response from server was not OK: {0}'.format(response2.status_code))
    return None

  cur2 = open(os.path.join(outputdir, 'current_image.gif'), 'wb')
  cur2.write(response2.content)
  cur2.close()

  return True


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


def get_warnings_box(url, station, outputdir='/tmp'):
  """
  Retrieve the severe weather graphics boxes (suitable for overlaying)
  from the NWS for the specified locale.
  """
  warnings = 'Warnings'
  response = requests.get(url.format(station=station,
                                     warnings=warnings,
                                    ),
                          verify=False, timeout=10)
  cur = open(os.path.join(outputdir, 'current_warnings.gif'), 'wb')
  cur.write(response.content)
  cur.close()

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

  for az_deg, val in azdir.iteritems():
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


def get_forecast(lon, lat, url, fmt=None, days=7):
  """
  https://graphical.weather.gov/xml/sample_products/browser_interface/
  ndfdBrowserClientByDay.php?lat=38.99&lon=-77.01&format=24+hourly&numDays=7

  These URLs and APIs are subject to change. Refresh times should be no
  more frequent than 1/hour.
  Updates occur approximately 45 minutes after the hour, so re-checking
  on the 0th minute of the hour would be appropriate.

  The returned payload will be XML.

  See also: https://www.weather.gov/documentation/services-web-api for
  another API?

  """
  if not fmt or fmt is None:
    fmt = ['24', 'hourly']
  time_format = " ".join(fmt)
  payload = {'lon': lon, 'lat': lat, 'format': time_format, 'numDays': days}

  retval = requests.get(url=url, params=payload, verify=False, timeout=10)

  return retval


def parse_forecast(rxml):
  """
  Use bs4 to parse the XML returned from the AWS forecast request.

  """
  bs_object = BeautifulSoup(rxml.text, 'xml')
  params = bs_object.find('parameters')
  temps = params.find_all('temperature')
  fc_dict = {'highs': [], 'lows': [], 'summaries':[], 'forecasts':[],
             'precip': [], 'dates': [], 'pcp_pct': []}
  fc_dict['dates'] = get_dates(bs_object)
  for temp in temps[0].find_all('value'):
    fc_dict['highs'].append(temp.string)
  for temp in temps[1].find_all('value'):
    fc_dict['lows'].append(temp.string)

  fc_dict['precip'] = concat_precip(params)
  fc_dict['pcp_pct'] = order_precip(params)
  weather = params.find('weather')
  weather_conditions = weather.find_all('weather-conditions')
  for forecast in weather_conditions:
    summary = forecast['weather-summary']
    fc_dict['summaries'].append(summary)
    if forecast.find_all('value'):
      shortcast = ''
      for value in forecast.find_all('value'):
        shortcast = '{0} {1}'.format(shortcast, concat_forecast(value))
      fc_dict['forecasts'].append(shortcast)

  return fc_dict


def concat_precip(bs_obj):
  """
  Precip chances come in 12-hour increments. List them together by day.
  """
  rainlist = []
  days = []
  for rain in bs_obj.find('probability-of-precipitation').find_all('value'):
    rainlist.append(rain.string)
  for i in range(0, len(rainlist), 2):
    try:
      part1 = '{0:3d}%'.format(int(rainlist[i]))
    except TypeError:
      part1 = ' --'
    try:
      part2 = '{0:3d}%'.format(int(rainlist[i+1]))
    except TypeError:
      part2 = ' --'

    if part1 == '  0%' and part2 == '  0%':
      thestring = '  0% '
    else:
      thestring = '{0} /{1}'.format(part1, part2)

    days.append(thestring)

  return days


def order_precip(bs_obj):
  """
  Put tuples of precipitation chances into a list and return it.
  """
  rainlist = []
  thelist = []
  for rain in bs_obj.find('probability-of-precipitation').find_all('value'):
    rainlist.append(rain.string)

  for i in range(0, len(rainlist), 2):
    try:
      part1 = '{0:3d}'.format(int(rainlist[i]))
    except TypeError:
      part1 = ' 0'
    try:
      part2 = '{0:3d}'.format(int(rainlist[i+1]))
    except TypeError:
      part2 = ' 0'
    thelist.append((part1, part2))

  return thelist


def concat_forecast(bs_obj):
  """
  Cycle through tag attrs, filter out the "none" values, and string
  together the results into a quasi-sentence forecast.
  """

  result = []
  for i in bs_obj.attrs.keys():
    if bs_obj[i] == "none":
      continue
    result.append(bs_obj[i].strip())

  return " ".join(result)


def write_forecast(fc_dict, outputdir, filename='forecast.txt'):
  """
  Write out a nicely formatted text file using the retrieved and summarized
  forecast information.
  """
  with open(os.path.join(outputdir, filename), 'w') as forecast:
    forecast.write('  Forecast:\n')
    forecast.write('-'*50 + '\n')
    for i in range(0, 6):
      line = '{0}  {1:3d}  {2:3d}  {3:10s}  {4}'.format(fc_dict['dates'][i],
                                                        int(fc_dict['highs'][i]),
                                                        int(fc_dict['lows'][i]),
                                                        fc_dict['precip'][i],
                                                        fc_dict['summaries'][i],
                                                       )
      forecast.write('{0}\n'.format(line))

    return True


def get_dates(bs_object, hourly='24hourly'):
  """
  Get the day of the week from the next seven days' forecast.
  """
  dates = []
  time_layouts = bs_object.find('data').find_all('time-layout')
  for i in time_layouts:
    if i['summarization'] == hourly:
      for j in i.find_all('start-valid-time'):
        reftime = re.sub(r'-0\d{1}:00$', ' CST', j.string)
        t_time = datetime.datetime.strptime(reftime, "%Y-%m-%dT%H:%M:%S %Z")
        dates.append(datetime.datetime.strftime(t_time, "%a"))

  return dates


def get_today_vars(timezone='America/Chicago'):
  """
  Get various strings from today's date for use in GOES image retrieval.
  """
  today = datetime.datetime.now()
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
                     utcnow=datetime.datetime.utcnow()
                    )
  return return_dict


def high_low_svg(high, low, filename, outputdir='/tmp/'):
  """
  Use svgwrite to make a simple graphic with high/low temps for the day's
  forecast.
  Unicode deg-Celsius is U+2103 (only for UTF-16)
  Unicode deg-Fahrenheit is U+2109 (only for UTF-16)
  Unicode degree symbol is U+00B0 ('\xb0') -- same as Latin-1 encoding, but is
  not available in 1963-standard 7-bit ASCII
  """

  high_coords = (2, 15)
  low_coords = (2, 36)
  dimensions = (40, 40)
  style1 = '''.{stylename} {openbrace} font: bold {fontsize}px sans-serif;
  fill:{fontcolor}; stroke:#000000; stroke-width:1px; stroke-linecap:butt;
  stroke-linejoin:miter; stroke-opacity:0.7; {closebrace}'''

  dwg = svgwrite.Drawing(os.path.join(outputdir, filename), size=dimensions)
  dwg_styles = svgwrite.container.Style(content='.background {fill: #f0f0f0f0; stroke: #f0f0f0f0;}')
  dwg_styles.append(content=style1.format(stylename='low', openbrace='{',
                                          fontsize='16', fontcolor='blue',
                                          closebrace='}'))
  dwg_styles.append(content=style1.format(stylename='high', openbrace='{',
                                          fontsize='18', fontcolor='red',
                                          closebrace='}'))
  dwg.defs.add(dwg_styles)
  high_symbol = (unicode(high) + u'\xb0')
  low_symbol = (unicode(low) + u'\xb0')
  high_text = svgwrite.text.TSpan(text=high_symbol,
                                  insert=high_coords, class_='high')
  low_text = svgwrite.text.TSpan(text=low_symbol,
                                 insert=low_coords, class_='low')
  text_block = svgwrite.text.Text('', x='0', y='0')
  text_block.add(high_text)
  text_block.add(low_text)
  dwg.add(text_block)
  dwg.save(pretty=True)

  return 0


def precip_chance_svg(morning, evening, filename, outputdir='/tmp/'):
  """
  Take the day's precip chances and produce a color-coded svg of percentages.
  """
  svg_info = {'high_coords': (8, 16),
              'low_coords': (2, 38),
              'dimensions': (55, 40),
              'colors': ['#baa87d', '#7ae6c0', '#2bb5aa', '#023dbd', '#035740'],
              'fontcolor': 'white'
             }

  bgc = svg_info['colors'][int(max(morning, evening)/100.0 * (len(svg_info['colors']) - 1))]

  if not re.search(r'%$', str(evening)):
    evening = '{0}%'.format(evening)
  if not re.search(r'%$', str(morning)):
    morning = '{0}%'.format(morning)

  style1 = '''.{stylename} {openbrace} font: bold {fontsize}px sans-serif;
  fill:{fontcolor}; stroke:#000000; stroke-width:1px; stroke-linecap:butt;
  stroke-linejoin:miter; stroke-opacity:0.5; {closebrace}'''

  dwg = svgwrite.Drawing(os.path.join(outputdir, filename),
                         size=svg_info['dimensions'])

  dwg_styles = svgwrite.container.Style(content='.background {fill: ' + bgc +
                                        '; stroke: #f0f0f0f0;}')
  dwg_styles.append(content=style1.format(stylename='morning', openbrace='{',
                                          fontsize='18', fontcolor='#f2df94',
                                          closebrace='}'))
  dwg_styles.append(content=style1.format(stylename='evening', openbrace='{',
                                          fontsize='18', fontcolor='#ffd4fb',
                                          closebrace='}'))
  dwg.defs.add(dwg_styles)
  evening_text = svgwrite.text.TSpan(text=evening,
                                     insert=svg_info['high_coords'],
                                     class_='evening')
  morning_text = svgwrite.text.TSpan(text=morning,
                                     insert=svg_info['low_coords'],
                                     class_='morning')
  frame = svgwrite.shapes.Rect(insert=(0, 0),
                               size=svg_info['dimensions'],
                               class_='background')
  text_block = svgwrite.text.Text('', x='0', y='0')
  text_block.add(evening_text)
  text_block.add(morning_text)
  dwg.add(frame)
  dwg.add(text_block)
  dwg.save(pretty=True)

  return 0


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
  except KeyError as e:
    print('Exception: {0}'.format(e))
    return False


def make_forecast_icons(fc_dict, outputdir='/tmp/'):
  """
  Write out SVG icons of the next three days of temps and precip chances.
  """
  filelabel = 'today_{fctype}_plus_{day}.svg'
  for i in range(0, 3):
    high_low_svg(fc_dict['highs'][i], fc_dict['lows'][i],
                 filelabel.format(fctype='temp', day=i),
                 outputdir=outputdir
                )
    precip_chance_svg(int(fc_dict['pcp_pct'][i][0]),
                      int(fc_dict['pcp_pct'][i][1]),
                      filename=filelabel.format(fctype='precip', day=i),
                      outputdir=outputdir
                     )

  return True


def load_yaml(directory, filename):
  """
  Load a YAML file in and return the dictionary that is created.
  """
  try:
    with open(os.path.join(directory, filename), 'r') as iyaml:
      return yaml.load(iyaml.read(), Loader=yaml.Loader)
  except Exception as e:
    print('EXCEPTION -- unable to open yaml settings file: {0}'.format(e))
    return None
