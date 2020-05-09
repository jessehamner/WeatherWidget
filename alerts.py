"""
alerts.py: download and sort alerts from NOAA / All Hazards.
Also download hazardous weather outlook.
Return a nice dictionary.
"""

from __future__ import print_function

import os
import re
import logging
import requests
from bs4 import BeautifulSoup
import weather_functions as wf


class Alerts(object):
  """
  download and parse alerts, hazards, and spotter activation info.
  """

  def __init__(self,
               data='',
               outputfile='current_hwo.txt',
               outputalertsfile = 'alerts_text.txt'):
    """
    Instantiate the Alerts object and set up common variables.
    """
    self.data = data
    self.defaults = self.data['defaults']
    self.hwo_text = ''
    self.outputfile = outputfile
    self.outputalertsfile = outputalertsfile
    self.hwo_dict = dict(today='', daystwothroughseven='', spotter='')
    self.alert_dict = dict()
    self.hwo_today = ''


  def get_alerts(self):
    """
    Do each step needed to fully populate the dict.
    get HWO
    parse and split HWO
    get current alerts
    parse alerts into alerts, (severe) watches, and (severe) warnings

    """
    self.hwo_today, self.hwo_dict = self.split_hwo(self.get_hwo())
    if self.hwo_today is not None:
      hwo = re.sub('.DAY ONE', 'Hazardous Weather Outlook', self.hwo_today)
      with open(os.path.join(self.data['output_dir'], 'today_hwo.txt'), 'w') as today_hwo:
        today_hwo.write(hwo)
      today_hwo.close()
    wf.write_json(some_dict=self.hwo_dict,
                  outputdir=self.data['output_dir'],
                  filename='hwo.json'
                 )

    print('Getting alerts for the following counties: {0}.'.format(self.data['alert_counties']))
    self.alert_dict = self.get_current_alerts()
    alertpath = os.path.join(self.data['output_dir'], self.outputalertsfile)
    if not self.alert_dict:
      try:
        if os.path.exists(alertpath):
          os.remove(alertpath)
      except OSError:
        pass

    else:
      wf.write_json(some_dict=self.alert_dict,
                    outputdir=self.data['output_dir'],
                    filename='alerts.json')
      with open(alertpath, 'w') as current_alerts:
        for key, value in self.alert_dict.iteritems():
          print('Key for this alert entry: {0}'.format(key))
          current_alerts.write('{0}\n'.format(value['warning_summary']))

    return True


  def get_hwo(self):
    """
    Get the HTML-only Hazardous Weather Outlook. The raw text of this statement
    is available inside

    <body>
      <div id="local"> <div id="localcontent">
      <pre class="glossaryProduct">
      (Text is here)
      </pre>
    """
    params_dict = {'site': self.data['hwo_site'],
                   'issuedby': self.data['nws_abbr'],
                   'product': 'HWO',
                   'format': 'txt',
                   'version': 1,
                   'glossary': 0
                  }

    response = requests.get(self.defaults['hwo_url'],
                            params=params_dict,
                            verify=False,
                            timeout=10)
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    pres = soup.body.find_all('pre')
    for pretag in pres:
      self.hwo_text = pretag.get_text()
      if len(self.hwo_text) > 200:

        cur = open(os.path.join(self.data['output_dir'], self.outputfile), 'w')
        cur.write(self.hwo_text)
        cur.close()
        return self.hwo_text

    return None


  def split_hwo(self, bodytext):
    """
    Pull out today's hazardous weather outlook and spotter activation notice.
    Return a slightly more compact text block of the two paragraphs.

    """
    returntext = ''
    # print('Raw body text of HWO: \n{0}'.format(bodytext))

    dayone = re.search(r'(\.DAY ONE.*?)(\.DAYS TWO THROUGH SEVEN)', bodytext, re.DOTALL)
    if dayone:
      hwotext = re.sub(r'\n\n$', '', dayone.group(1))
      self.hwo_dict['today'] = hwotext
      self.hwo_dict['today'] = re.sub(r'\.{1,}DAY ONE[\.]{1,}', '', self.hwo_dict['today'])
      self.hwo_dict['today'] = re.sub('\n', ' ', self.hwo_dict['today'])
      self.hwo_dict['daystwothroughseven'] = re.sub(r'\n{2,}$', '', dayone.group(2))
      self.hwo_dict['daystwothroughseven'] = re.sub(r'\.DAYS TWO THROUGH SEVEN', '',
                                                    self.hwo_dict['daystwothroughseven'])
      self.hwo_dict['daystwothroughseven'] = re.sub('\n', ' ',
                                                    self.hwo_dict['daystwothroughseven'])

    spotter = re.search(r'(\.SPOTTER INFORMATION STATEMENT.*?)(\s*\$\$)',
                        bodytext, re.DOTALL)
    if spotter:
      spottext = re.sub(r'\n\n$', '', spotter.group(1))
      self.hwo_dict['spotter'] = re.sub(r'\.{1,}SPOTTER INFORMATION STATEMENT[\.]{1,}',
                                        '', spottext)
      self.hwo_dict['spotter'] = re.sub('\n', ' ', self.hwo_dict['spotter'])

    if hwotext:
      returntext = '{0}{1}\n\n'.format(returntext, hwotext)
    if spottext:
      returntext = '{0}{1}\n\n'.format(returntext, spottext)

    returntext = re.sub(r'\n\n$', '', returntext)
    return returntext, self.hwo_dict



  def get_current_alerts(self):
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
    if self.data['alert_counties'] is None:
      print('No counties in submitted parameters. Returning -None-')
      return None

    county_params_dict = {'x': self.data['alert_county'], 'y': 1}

    try:
      response = requests.get(self.data['defaults']['alerts_url'],
                              params=county_params_dict,
                              verify=False, timeout=10)
    except e:
      print('Exception when requesting current alerts: {0}'.format(e))
      return None

    if response.status_code == 200 and response.headers['Content-Type'] == 'text/xml':
      # Parse the feed for relevant content:
      entries = BeautifulSoup(response.text, 'xml').find('feed').find_all('entry')
    else:
      print('ERROR: Response from NWS alerts server is: {0}'.format(response.status_code))
      return None

    sum_str = '{sev} {event_type}, {st_date} - {en_date}\nSummary: {summary}\n\n'
    for entry in entries:
      print('Now checking alerts xml.')
      warning_county = self.is_county_relevant(entry,
                                               tagname='areaDesc')
      if warning_county:
        # print('Found warning for {0} county.'.format(warning_county))
        # print('Text of this warning entry is: {0}'.format(entry.prettify()))
        event_id = entry.find('id').text
        summary = entry.find('summary').text
        summary = re.sub(r'\*', '\n', summary)

        event_type = entry.find('event', text=True)
        if event_type:
          print('Event_type info: {0}'.format(event_type.text))
          event_type = event_type.text
        else:
          print('No cap:event tags in entry?')

        startdate = entry.find('effective', text=True)
        if startdate:
          # print('Startdate: {0}'.format(startdate.text))
          startdate = startdate.text

        enddate = entry.find('expires').string
        # category = entry.find('category').string
        severity = entry.find('severity').text
        certainty = entry.find('certainty').text
        warning_summary = sum_str.format(event_type=event_type,
                                         st_date=startdate,
                                         en_date=enddate,
                                         sev=severity,
                                         summary=summary)
        # print('Warning summary:\n{0}'.format(warning_summary))

        eventdict = {'event_type': event_type,
                     'startdate': startdate,
                     'enddate': enddate,
                     'severity': severity,
                     'certainty': certainty,
                     'summary': summary,
                     'event_id': event_id,
                     'warning_summary': warning_summary
                    }
        self.alert_dict[event_id] = eventdict

    return self.alert_dict


  def is_county_relevant(self, xml_entry, tagname='areaDesc'):
    """
    Check to see if an xml tag contains items from a user-specified list.
    """
    entry_counties = xml_entry.find(tagname)
    if not entry_counties:
      return None

    try:
      if not entry_counties.text:
        return None
      clist = entry_counties.text.split(';')
      if not clist:
        return None
    except AttributeError as e:
      print('Attribute Error: {0}. Returning None.'.format(e))
      return None

    for county in clist:
      print('Checking county {0}'.format(county))
      if county.strip() in self.data['alert_counties']:
        return county.strip()

    return None


  def parse_alerts(self):
    """
    Format alerts into a better architected dictionary.
    

    """
    alerts = dict(hwo=dict(spotter='', dayone='', daytwo=''),
                  alerts=dict(issues=[]),
                  watches=dict(issues=[]),
                  warnings=dict(issues=[])
                 )

    return True
