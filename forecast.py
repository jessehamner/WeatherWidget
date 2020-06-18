"""
obs.py: download and consolidate current conditions data for a given location.
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
                    day='Noneday', date=None, icon='na.svg', idx=idx)
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
    # print(today.fcd)
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
    - .WATCHES/WARNINGS/ADVISORIES...

    But this function only retrieves the short- and long-term paragraphs.
    """

    afdreturn = dict(short_term='', long_term='')
    endmarker = '&&'
    url = 'https://forecast.weather.gov/product.php'

    args = {'site':self.data['nws_abbr'],
            'issuedby': self.data['nws_abbr'],
            'product': 'AFD',
            'format': fmt,
            'version': '1',
            'glossary': '0'
           }

    try:
      response = requests.get(url, params=args, verify=False, timeout=10)
    except requests.exceptions.ReadTimeout:
      print('Request timed out. Returning -None-')
      return None

    if response.status_code != 200:
      print('Response from server was not OK: {0}'.format(response.status_code))
      return None

    afd = response.text
    afdtext = re.sub(r'\n', ' ', afd)
    afdtext = re.sub(endmarker, '\n', afdtext)
    short_term = re.search(r'\.SHORT TERM\.\.\.(.*.?)', afdtext).groups(0)[0]
    long_term = re.search(r'\.LONG TERM\.\.\.(.*.?)', afdtext).groups(0)[0]
    afdreturn['short_term'] = short_term
    afdreturn['long_term'] = long_term
    write_json(afdreturn, outputdir=self.data['output_dir'], filename='afd.json')

    return afdreturn


  def get_forecast(self, fmt=None):
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
    payload = {'lon': self.data['lon'],
               'lat': self.data['lat'],
               'format': time_format,
               'numDays': self.data['defaults']['forecast_days']
              }
    retval = requests.get(url=self.data['defaults']['forecast_url'],
                          params=payload,
                          verify=False,
                          timeout=10
                         )
    if retval.status_code == 200:
      self.data['forecast_xml'] = retval.text
      print('Returned HTTP response code: {0}'.format(retval))
      self.parsed_xml = BeautifulSoup(self.data['forecast_xml'], 'xml')
      return retval
    print('Cannot retrieve forecast -- server returned {0}'.format(retval))
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
      today.populate_day_dict()
      today.make_forecast_icons()
      self.forecast.append(today.fcd)

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
