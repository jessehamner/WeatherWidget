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
# import lxml
import pytz
from bs4 import BeautifulSoup
requests.packages.urllib3.disable_warnings()


def prettify_timestamp(timestamp):
  """
  Make a more user-readable time stamp for current conditions.
  """
  posix_timestamp = datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S+00:00')
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
  return True


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


def format_current_conditions(cur, cardinal_directions=True):
  """
  Take in the dictionary of current conditions and return a text document.
  """
  temp_unit = 'F'
  if cur['temperature']['unitCode'] == 'unit:degC':
    temp_unit = 'C'

  doctext = str('Conditions as of {}'.format(prettify_timestamp(cur['timestamp'])))
  # temp_value = sanity_check(cur['temperature']['value'], 'int')
  doctext = quick_doctext(doctext,
                          'Temperature:',
                          sanity_check(cur['temperature']['value'], 'int'),
                          temp_unit)

  # dewpoint_value = sanity_check(cur['dewpoint']['value'], 'int')
  doctext = quick_doctext(doctext,
                          'Dewpoint:',
                          sanity_check(cur['dewpoint']['value'], 'int'),
                          temp_unit)

  # rh_value = sanity_check(cur['relativeHumidity']['value'], 'int')
  doctext = quick_doctext(doctext,
                          'Rel. Humidity:',
                          sanity_check(cur['relativeHumidity']['value'], 'int'),
                          '%')

  heat_index_value = sanity_check(cur['heatIndex']['value'], 'int')
  if heat_index_value == "None":
    heat_index_string = heat_index_value
  else:
    heat_index_string = str('{} {}'.format(heat_index_value, temp_unit))
  doctext = quick_doctext(doctext,
                          'Heat Index:',
                          heat_index_string,
                          temp_unit)

  pressure_unit = re.sub('unit:', '', cur['barometricPressure']['unitCode'])
  pressure_value = sanity_check(cur['barometricPressure']['value'])
  print('Pressure value: {0}'.format(pressure_value))
  if pressure_unit == 'Pa' and pressure_value != "None":
    pressure_value = float(pressure_value) / 1000.0
    pressure_unit = 'kPa'
  doctext = quick_doctext(doctext, 'Pressure:', pressure_value, pressure_unit)

  wind_dir_unit = re.sub('unit:', '', cur['windDirection']['unitCode'])
  if wind_dir_unit == 'degree_(angle)':
    wind_dir_unit = 'degree azimuth'

  wind_azimuth = sanity_check(cur['windDirection']['value'], 'int')
  if wind_azimuth == 'None':
    wind_dir_unit = ''
  if cardinal_directions and wind_azimuth:
    if wind_azimuth == 'None':
      wind_string = 'No data'
    else:
      wind_string = str('out of the {}'.format(wind_direction(wind_azimuth)))
  else:
    wind_string = str('{} {}'.format(wind_azimuth, wind_dir_unit))

  doctext = quick_doctext(doctext, 'Wind Direction:', wind_string, '')

  wind_speed_unit = re.sub('unit:', '', cur['windSpeed']['unitCode'])
  wind_speed_value = sanity_check(cur['windSpeed']['value'], 'int')
  if wind_speed_unit == 'm_s-1' and wind_speed_value != 'None':
    wind_speed_value = (float(wind_speed_value) / 1000.0) * 3600.0
    wind_speed_unit = 'km / hr'

  doctext = quick_doctext(doctext, 'Wind Speed:', wind_speed_value, wind_speed_unit)

  return doctext


def get_weather_radar(url, station, outputdir='/tmp'):
  """
  Using the NWS radar station abbreviation, retrieve the current radar image
  and world file from the NWS.
  """
  response1 = requests.get(url.format(station=station, image='N0R_0.gfw'),
                           verify=False)
  if response1.status_code != 200:
    print('Response from server was not OK: {0}'.format(response1.status_code))
    return None
  cur1 = open(os.path.join(outputdir, 'current_image.gfw'), 'w')
  cur1.write(response1.text)
  cur1.close()

  response2 = requests.get(url.format(station=station, image='N0R_0.gif'),
                           verify=False)
  if response2.status_code != 200:
    print('Response from server was not OK: {0}'.format(response2.status_code))
    return None

  cur2 = open(os.path.join(outputdir, 'current_image.gif'), 'wb')
  cur2.write(response2.content)
  cur2.close()

  return True


def get_warnings_box(url, station, outputdir='/tmp'):
  """
  Retrieve the severe weather graphics boxes (suitable for overlaying)
  from the NWS for the specified locale.
  """
  warnings = 'Warnings'
  response = requests.get(url.format(station=station,
                                     warnings=warnings),
                          verify=False)
  cur = open(os.path.join(outputdir, 'current_warnings.gif'), 'wb')
  cur.write(response.content)
  cur.close()

  return 0


def get_hwo(url, params_dict, outputfile='current_hwo.txt', outputdir='/tmp'):
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

      cur = open(os.path.join(outputdir, outputfile), 'w')
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

  try:
    response = requests.get(url, params=params_dict, verify=False)
  except requests.exceptions.ConnectionError as e:
    print('ConnectioError: {0}'.format(e))
    return None
  
  html = response.text
  #print('Response text: {0}'.format(html))
  soup = BeautifulSoup(html, 'html.parser')
  
  try:
    pres = soup.body.find_all('pre')
  except TypeError:
    return None

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


def is_county_relevant(counties_list, xml_entry, tagname='areaDesc'):
  """
  Check to see if an xml tag contains items from a user-specified list.
  """
  entry_counties = xml_entry.find(tagname)
  clist = entry_counties.text.split(';')
  for county in clist:
    print('Checking county {0}'.format(county))
    if county.strip() in counties_list:
      return county.strip()

  return None


def get_current_alerts(url, data_dict, alert_dict):
  """
  Get current watches, warnings, or advisories for a county or zone.
  Check https://alerts.weather.gov/cap/wwaatmget.php?x=TXC121&y=1 as example.
  For abbreviations, see https://alerts.weather.gov/
  The ATOM and CAP (XML) feeds are updated about every two minutes.
  ATOM XML feed for Texas: https://alerts.weather.gov/cap/tx.php?x=0
  Complete CAP feeds are linked within the ATOM XML feed.
  
  Each entry contains a space-delimited list of counties in several formats.
  Under <cap:areaDesc>, there is an English-language list of semicolon-
    delimited county names.

  Under <cap:geocode>, there are two <valueName> tags:
  FIPS6 = three digit state FIPS code (prepended by zero if less than 100),
    concatenated with the FIPS county code for that state. For instance, 
    Denton County, Texas is 048121 (Texas is "048")

  UGC = Two-letter alpha state abbreviation, concatenated with a county number
    that is NOT the FIPS number for that county.
    Denton County, Texas is TXZ103, for instance.
  
  """
  if data_dict['alert_counties'] is None:
    print('No counties in submitted parameters. Returning -None-')
    return None

  params_dict = {'x': data_dict['alert_county'], 'y': 1}
  response = requests.get(url, params=params_dict, verify=False)
  if response.status_code == 200 and response.headers['Content-Type'] == 'text/xml':
    # Parse the feed for relevant content:
    entries = BeautifulSoup(response.text, 'xml').find('feed').find_all('entry')
  else:
    print('ERROR: Response from NWS alerts server is: {0}'.format(response.status_code))
    return None

  sum_str = '{sev} {event_type}, {st_date} - {en_date}\nSummary: {summary}\n\n'
  for entry in entries:
    print('Now checking alerts xml.')
    warning_county = is_county_relevant(data_dict['alert_counties'],
                                        entry,
                                        tagname='areaDesc')
    if warning_county:
      # print('Found warning for {0} county.'.format(warning_county))
      # print('Text of this warning entry is: {0}'.format(entry.prettify()))
      event_id = entry.find('id').text
      summary = entry.find('summary').text
      summary = re.sub(r'\*', '\n', summary)
      
      event_type = entry.find( 'event', text=True )
      if event_type:
        print('Event_type info: {0}'.format(event_type.text))
        event_type = event_type.text
      else:
        print('No cap:event tags in entry?')
      
      startdate = entry.find( 'effective', text=True )
      if startdate:
        # print('Startdate: {0}'.format(startdate.text))
        startdate = startdate.text
      
      enddate = entry.find('expires').string
      category = entry.find('category').string
      severity = entry.find('severity').text
      certainty = entry.find('certainty').text
      warning_summary = sum_str.format(event_type = event_type,
                                       st_date = startdate,
                                       en_date = enddate,
                                       sev = severity,
                                       summary = summary)
      # print('Warning summary:\n{0}'.format(warning_summary))

      eventdict = {'event_type': event_type,
                   'startdate': startdate,
                   'enddate': enddate,
                   'severity': severity,
                   'certainty': certainty,
                   'summary': summary,
                   'event_id': event_id,
                   'warning_summary': warning_summary}
      alert_dict[event_id] = eventdict
      # print('Event dictionary: {0}'.format(alert_dict[event_id]))

  return alert_dict


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
                   output_path='/tmp'):
  """
  Retrieve hydrograph image (png) of the current time and specified location
  Can find these abbreviations at
  https://water.weather.gov/ahps2/hydrograph.php

  Raw data output in XML for a location (here, "cart2"):
  https://water.weather.gov/ahps2/hydrograph_to_xml.php?gage=cart2&output=xml

  """
  filename = '{0}_hg.png'.format(abbr.lower())
  retval = requests.get(os.path.join(hydro_url, filename))
  print('retrieving: {0}'.format(retval.url))
  print('return value: {0}'.format(retval))
  if retval.status_code == 200:
    cur1 = open(os.path.join(output_path, 'current_hydrograph.png'), 'wb')
    cur1.write(retval.content)
    cur1.close()

  return retval


def get_forecast(lon, lat, url, fmt=['24', 'hourly'], days=7):
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
  time_format = " ".join(fmt)
  payload = {'lon': lon, 'lat': lat, 'format': time_format, 'numDays': days}

  retval = requests.get(url=url, params=payload, verify=False)
  # print('Returned info: {0}'.format(retval.text))

  return retval


def parse_forecast(rxml):
  """
  Use bs4 to parse the XML returned from the AWS forecast request.

  """
  bs_object = BeautifulSoup(rxml.text, 'xml')
  params = bs_object.find('parameters')
  temps = params.find_all('temperature')
  dates = get_dates(bs_object)
  highs = []
  lows = []
  for temp in temps[0].find_all('value'):
    highs.append(temp.string)
  for temp in temps[1].find_all('value'):
    lows.append(temp.string)

  pcp = concat_precip(params)
  forecasts = []
  summaries = []
  weather = params.find('weather')
  weather_conditions = weather.find_all('weather-conditions')
  for forecast in weather_conditions:
    summary = forecast['weather-summary']
    summaries.append(summary)
    if forecast.find_all('value'):
      shortcast = ''
      for value in forecast.find_all('value'):
        shortcast = '{0} {1}'.format(shortcast, concat_forecast(value))

      forecasts.append(shortcast)

  return dict(highs=highs, lows=lows, precip=pcp, forecasts=forecasts,
              summaries=summaries, dates=dates)


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
      thestring = ' 0% '
    else:
      thestring = '{0} /{1}'.format(part1, part2)

    days.append(thestring)

  return days


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
                     offset=local_tz.utcoffset(today).total_seconds()/3600
                    )
  return return_dict


def get_goes_list(data, band='NightMicrophysics'):
  """
  GOES images post every 5 minutes, but there is no guarantee that you will
  know the minute of the image when concatenating the filename.
  Therefore, this function pulls a list from the specified directory and
  returns the list of files from today with the specified resolution for use.
  """
  sector = data['goes_sector']
  sat = data['goes_sat']
  res = data['goes_res']
  url = data['goes_url'].format(sat=sat, sector=sector, band=band)
  # print('Checking url: {0}'.format(url))
  filelist = BeautifulSoup(requests.get(url).text, 'html')
  links = filelist.find_all("a", attrs={"href": True})
  files = []
  todaystring = '{0}{1}'.format(data['today_vars']['year'], data['today_vars']['doy'])
  # print('Links: {0}'.format(links))
  myimage = re.compile('ABI-{0}-{1}-{2}'.format(sector, band, res))
  # print('Keying on {0}'.format(myimage))
  for i in links:
    if i.has_attr("href"):
      filename = i['href']
      # print('Checking file: "{0}"'.format(filename))
    try: 
      if myimage.search(filename):
          if re.search(res, filename) and re.search(todaystring, filename):
            files.append(filename)
    except KeyError, AttributeError:
      pass

  return files


def get_goes_image(data, band='NightMicrophysics'):
  """
  Retrieve current GOES weather imagery. Not complete yet.
  """

  url = data['goes_url'].format(sat=data['goes_sat'],
                             sector=data['goes_sector'],
                             band=band)
  
  image = data['goes_img'].format(year=data['today_vars']['year'],
                                  doy=data['today_vars']['doy'],
                                  timeHHMM='1806',
                                  sat=data['goes_sat'],
                                  sector=data['goes_sector'],
                                  band=band,
                                  resolution=data['goes_res']
                                 )
  # image = '20200651806_GOES16-ABI-sp-NightMicrophysics-2400x2400.jpg' 
  returned_val = requests.get(os.path.join(url, image)) 
  with open(image, 'wb') as satout:
    satout.write(bytearray(returned_val.content))

  return image
