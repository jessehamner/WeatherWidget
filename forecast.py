"""
forecast.py: download forecast data for a given location.
Make icons of expected precip and temperature values.
Write out JSON.
"""

from __future__ import print_function

import os
import re
import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from weather_functions import write_json
import weathersvg as wsvg


class DayForecast(object):
  """
  Store one day's forecast and do useful stuff with the information.
  """

  def __init__(self, output_dir, idx, parsed_xml, icon_dict):
    self.fcd = dict(high=None, low=None, precip_morning=0, precip_evening=0,
                    shortcast='No forecast', forecast_string='',
                    night_forecast_string='', day='Noneday',
                    date=None, icon='na.svg', idx=idx)
    self.idx = idx
    self.parsed_xml = parsed_xml
    self.icon_dict = icon_dict
    self.output_dir = output_dir
    self.offset = ''


  def make_forecast_icons(self):
    """
    Write out SVG icons of the day's temps and precip chances.
    """
    filelabel = 'today_{fctype}_plus_{day}.svg'
    logging.info('Making temperature and precipitation forecast icons for day %s', self.idx)
    wsvg.high_low_svg(self.fcd['high'],
                      self.fcd['low'],
                      filelabel.format(fctype='temp', day=self.idx),
                      outputdir=self.output_dir
                     )
    wsvg.precip_chance_svg(int(self.fcd['precip_morning']),
                           int(self.fcd['precip_evening']),
                           filename=filelabel.format(fctype='precip', day=self.idx),
                           outputdir=self.output_dir
                          )

    return True


  def populate_day_dict(self):
    """
    Populate a single day's forecast dict.
    """
    params = self.parsed_xml.find('parameters')
    if params:
      logging.debug('Found parameters tag in parsed XML forecast')
    else:
      logging.error('Parsed XML contains no parameters. Returning None!')
      logging.debug(self.parsed_xml)
      return None
    temps = params.find_all("temperature")
    for temp in range(0, len(temps)):
      if temps[temp].attrs['type'] == "maximum":
        self.fcd['high'] = temps[temp].find_all("value")[self.idx].text
        continue
      self.fcd['low'] = temps[temp].find_all("value")[self.idx].text

    precip = params.find('probability-of-precipitation')
    self.fcd['precip_morning'] = precip.find_all("value")[self.idx].text
    self.fcd['precip_evening'] = precip.find_all("value")[self.idx + 1].text
    self.fcd['shortcast'] = params.find_all("weather-conditions")[self.idx].attrs['weather-summary']

    parseable_time = self.parsed_xml.find('time-layout').find_all("start-valid-time")[self.idx].text
    parseable_time1, self.offset = re.sub(r'([+|-])(\d{2}):(\d{2})$',
                                          ' \\1\\2\\3',
                                          parseable_time).split()
    valid_time = datetime.strptime(parseable_time1, "%Y-%m-%dT%H:%M:%S")
    self.fcd['day'] = valid_time.strftime("%a")
    self.fcd['date'] = valid_time.strftime("%Y-%m-%d")
    self.fcd['icon'] = wsvg.assign_icon(self.fcd['shortcast'],
                                        self.icon_dict)
    self.make_forecast_icons()
    logging.debug('Day forecast: %s', self.fcd)
    return self.fcd


class Forecast(object):
  """
  Retrieve, parse, and write out forecast information.
  """

  def __init__(self, data=''):
    self.data = data
    self.defaults = data['defaults']
    self.problem = False
    self.forecast = []
    self.afd = []
    self.offset = ''
    self.parsed_xml = ''


  def get_afd(self, fmt='txt'):
    """
    Area forecast discussion. Fairly advanced information and not useful for
    most dashboards, but nice as a drill-down option.
    The all-text AFD includes sections for
    - .SHORT TERM...
    - .LONG TERM...
    - .AVIATION...
    - .PRELIMINARY POINT TEMPS/POPS...
    - .[three-letter NWS abbreviation] WATCHES/WARNINGS/ADVISORIES...

    """
    afdreturn = dict(short_term='', long_term='')
    recordsplit = '&&'
    args = {'site':self.data['nws_abbr'],
            'issuedby': self.data['nws_abbr'],
            'product': 'AFD',
            'format': fmt,
            'version': '1',
            'glossary': '0'
           }

    try:
      response = requests.get(self.defaults['afd_url'],
                              params=args,
                              verify=True,
                              timeout=10)
    except requests.exceptions.ReadTimeout:
      logging.error('Request timed out. Returning -None-')
      return None

    if response.status_code != 200:
      logging.error('Response from server was not OK: %s', response.status_code)
      logging.debug('Response: %s', response.text)
      return None

    afd = BeautifulSoup(response.text, 'lxml').find('body').find('pre').text
    logging.debug('Response text (HTML body/pre/text):\n%s', afd)

    afd_groups = re.split(re.escape(recordsplit), afd, re.M)
    if len(afd_groups) < 5:
      logging.warn('There should be five or six sections in the Area Forecast Discussion!')
      logging.warn('Returning None.')
      return None
    else:
      logging.debug('There are %s entries in the Area Forecast Discussion.', len(afd_groups))

    indicator = self.defaults['afd_divisions'][0]
    short_term = afd_groups[0]
    afdreturn['short_title'], afdreturn['short_term'] = self.tidy_afd_text(short_term, indicator)

    indicator = self.defaults['afd_divisions'][1]
    long_term = afd_groups[1]
    afdreturn['long_title'], afdreturn['long_term'] = self.tidy_afd_text(long_term, indicator)

    write_json(afdreturn, outputdir=self.data['output_dir'], filename='afd.json')
    return afdreturn


  def tidy_afd_text(self, text, upperlabel):
    """
    Take the text and do some basic regexing on it, plus extract potential
    label/header text.
    """
    fctxt = re.sub(r'^.+.?(' + re.escape(upperlabel) +  ')', '\\1', text, re.M, re.DOTALL)
    fctxt = re.sub(r'\n+\d+\n+$', '', fctxt, re.M)
    label = self.get_forecast_header(fctxt)
    fctxt = re.sub(r'' + re.escape(upperlabel) + '.+.?\/\n{2}?', '', fctxt, re.M, re.DOTALL)
    fctxt = re.sub(r'\n(?!\n)', ' ', fctxt)
    fctxt = re.sub(r'\`', "'", fctxt)
    fctxt = re.sub(r'^\s+', '', fctxt)
    fctxt = re.sub(r'\.\s+\.\s*', '.', fctxt)
    fctxt = re.sub(r'\n+$', '', fctxt)
    return label, fctxt


  def get_forecast_header(self, text):
    """
    Pull out the forcast timing information label, ignoring the labels that
    say "NEW". These labels are denoted with forward slashes.
    """

    headers = [re.sub(r'\/', '', r.group()) for r in re.finditer(r'\/.+.?\/', text)]

    try:
      if headers[1]:
        return headers[1]
      if headers[0]:
        return headers[0]
      return ''

    except Exception as exc:
      logging.error('Cannot match a forecast time frame header in %s. (%s)', headers, exc)
    return ''


  def get_forecast(self, fmt=None):
    """
    https://digital.weather.gov/xml/sample_products/browser_interface/
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
    payload = {'lon': self.data['lon'],
               'lat': self.data['lat'],
               'format': time_format,
               'numDays': self.data['defaults']['forecast_days']
              }
    try:
      retval = requests.get(url=self.data['defaults']['forecast_url'],
                            params=payload,
                            verify=True,
                            timeout=10
                           )
    except requests.exceptions.ReadTimeout as exc:
      logging.error('Request timed out or could not be found: %s.', exc)
      return None

    if retval.status_code == 200:
      self.data['forecast_xml'] = retval.text
      logging.info('Forecast request returned HTTP response code: %s', retval)
      self.parsed_xml = BeautifulSoup(self.data['forecast_xml'], 'xml')

      if self.parsed_xml.find('error'):
        logging.warn('Server returned 200 but had errors:\n%s', self.parsed_xml)
        logging.info('Submitted:\nURL: %s\nPayload: %s',
                     self.data['defaults']['forecast_url'], str(payload))
        return None

      return retval
    logging.error('Cannot retrieve forecast -- server returned %s', retval)
    return None


  def parse_forecast(self):
    """
    Use bs4 to parse the XML returned from the AWS forecast request.
    """
    for idx in range(0, self.data['defaults']['forecast_days']):

      today = DayForecast(output_dir=self.data['output_dir'],
                          idx=idx,
                          parsed_xml=self.parsed_xml,
                          icon_dict=self.data['defaults']['icon_match']
                         )
      logging.info('Populating the day\'s forecast dictionary for day %s', idx)
      if today.populate_day_dict():
        self.forecast.append(today.fcd)
      else:
        logging.warn('Error parsing forecast XML. Forecast is NONE.')
        return None

    return self.forecast


  def concat_forecast(self, bs_obj):
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


  def write_forecast(self, outputdir='/tmp/', filename='forecast.txt'):
    """
    Write out a nicely formatted text file using the retrieved and summarized
    forecast information.
    """
    fcst = self.forecast
    with open(os.path.join(outputdir, filename), 'w') as fc_text:
      fc_text.write('  Forecast:\n')
      fc_text.write('-'*50 + '\n')
      for i in range(0, 3):
        precip_str = '{0:3d}% / {1:3d}%'.format(int(fcst[i]['precip_morning']),
                                                int(fcst[i]['precip_evening']))
        line = '{0}  {1:3d}  {2:3d}  {3:10s}  {4}'.format(fcst[i]['day'],
                                                          int(fcst[i]['high']),
                                                          int(fcst[i]['low']),
                                                          precip_str,
                                                          fcst[i]['shortcast'],
                                                         )
        fc_text.write('{0}\n'.format(line))

      return True



class ZoneForecast(object):
  """
  Pull the Zone forecast for the next 5-7 days and parse it into a text
  forecast for each day and night. Return an ordered list.
  Zone lists can be found on the NWS website.
  Zone forecasts are provided by regional NWS stations, like FWD.
  https://forecast.weather.gov/product.php?site=NWS&product=ZFP&issuedby=FWD
  """

  def __init__(self, data):

    self.zonef = list()
    self.data = data
    self.zone = data['forecast_zone']
    self.issuedby = data['nws_abbr']
    self.output_dir = data['output_dir']
    self.forecasturl = data['defaults']['afd_url']
    self.relevant = list()
    self.parsed_xml = ''

  def get(self):
    """
    A roll-up (convenience) function to "just get everything."
    """
    self.get_zone_forecast()
    self.parse_zone_forecast()
    self.write_zone_forecast()
    return True


  def get_zone_forecast(self):
    """
    Retrieve and extract the zone forecast product text.
    """
    payload = {'site': 'NWS', 'product':'ZFP', 'issuedby': self.issuedby}
    try:
      retval = requests.get(url=self.forecasturl,
                            params=payload,
                            verify=True,
                            timeout=10
                           )
    except requests.exceptions.ReadTimeout as exc:
      logging.error('Request timed out or could not be found: %s.', exc)
      return None

    if retval.status_code == 200:
      zone_forecast = retval.text
      logging.info('Forecast request returned HTTP response code: %s', retval)
      self.parsed_xml = BeautifulSoup(zone_forecast, 'lxml')

      if self.parsed_xml.find('error'):
        logging.warn('Server returned 200 but had errors:\n%s', self.parsed_xml)
        logging.info('Submitted:\nURL: %s\nPayload: %s',
                     self.data['defaults']['afd_url'], str(payload))
        return None
    relevant = self.parsed_xml.find("pre").text
    logging.debug('The forecast text has %s characters', len(relevant))
    rlist = relevant.split('''$$''')
    for i in rlist:
      if re.search(self.zone, i):
        logging.debug('Found requested forecast: %s', i)
        self.relevant.append(i)
        break

    return self.relevant


  def parse_zone_forecast(self):
    """
    Pull the forecast text out, then assign each element into a list of
    neatly filtered forecasts.
    """
    lines = self.relevant[0]
    lines = re.sub(r'\n', 'LINEBREAK', lines)
    lines = re.sub(r'\.([\w\s]+)\.\.\.', '\n\nONEDAY\\1ONEDAY', lines)
    # logging.debug('Forecast text: %s', lines)
    forecasts = lines.split('\n')
    for eachf in forecasts:
      if re.search(r'^\s*$', eachf):
        continue
      eachf = re.sub('LINEBREAK', ' ', eachf)
      if re.search(r'^ONEDAY([\w\s]+)ONEDAY', eachf):
        day = re.search(r'^ONEDAY([\w\s]+)ONEDAY', eachf).group(1)
        forecast = re.sub(day, '', eachf)
        forecast = re.sub('ONEDAY', '', forecast)
        forecast = re.sub(r'\s*$', '', forecast)
        logging.info('%s: %s', day, forecast)
        if re.search(r'^\s*$', forecast):
          continue
        self.zonef.append([day, forecast])

    return True


  def write_zone_forecast(self):
    """
    Write out the zone forecast to a discrete json file.
    """
    logging.info('Writing zone forecast out to zoneforecast.json.')
    write_json(self.zonef, outputdir=self.output_dir, filename='zoneforecast.json')
    return True
