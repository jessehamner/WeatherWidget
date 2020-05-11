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
    self.alert_dict = dict()

    self.alerts = dict(hwo=dict(spotter=[], dayone=[], daytwothroughseven=[], hwo_today=''),
                       alerts=dict(issues=[]),
                       watch=dict(issues=[]),
                       warn=dict(issues=[])
                      )


  def get_alerts(self):
    """
    Do each step needed to fully populate the dict.
    get HWO
    parse and split HWO
    get current alerts
    parse alerts into alerts, (severe) watches, and (severe) warnings

    """
    nodata = 'No data'
    self.get_hwo()
    self.alerts['hwo']['hwo_today'], self.alerts['hwo'] = self.split_hwo()
    
    textfilepath = os.path.join(self.data['output_dir'], 'today_hwo.txt')
    if self.alerts['hwo']['hwo_today'] is None:
      self.alerts['hwo']['hwo_today'] = ('Hazardous Weather Outlook:\n ' + nodata)
    self.write_text(filepath=textfilepath, some_text=self.alerts['hwo']['hwo_today'])
   
    jsonfilepath = os.path.join(self.data['output_dir'], 'hwo.json')
    if self.alerts['hwo'] is None:
      self.alerts['hwo'] = dict(today=[nodata, nodata], spotter=[nodata,nodata],
                           daystwothroughseven=[nodata, nodata])
    self.write_json(filepath=jsonfilepath, some_dict=self.alerts['hwo'])

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
      self.write_json(os.path.join(self.data['output_dir'], 'alerts.json'), self.alert_dict)
      self.write_dict(filepath = alertpath, some_dict = self.alert_dict) 

    return True


  def write_text(self, filepath, some_text):
    """
    Write a text string out to a file.
    """
    with open(filepath, 'w') as text_file:
      text_file.write(some_text)
    text_file.close()
    return True


  def write_dict(self, filepath, some_dict):
    """
    Write out a dict to a text file.
    """
    with open(filepath, 'w') as current_alerts:
      for key, value in some_dict.iteritems():
        print('Key for this alert entry: {0}'.format(key))
        current_alerts.write('{0}\n'.format(value['warning_summary']))

    return True


  def write_json(self, filepath, some_dict):
    """
    Write out a JSON file of a given dict.
    """
    with open(filepath, 'w') as out_obj:
      try:
        out_obj.write(json.dumps(some_dict))
        return True
      except:
        return False


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


  def split_hwo(self):
    """
    Pull out today's hazardous weather outlook and spotter activation notice.
    Return a slightly more compact text block of the two paragraphs.

    """
    bodytext = self.hwo_text
    returntext = ''
    # print('Raw body text of HWO: \n{0}'.format(bodytext))

    dayone = re.search(r'(\.DAY ONE.*?)(\.DAYS TWO THROUGH SEVEN.*?)', bodytext, re.DOTALL)
    if dayone:
      hwotext = re.sub(r'\n\n$', '', dayone.group(1))
      hwotext = re.sub(r'\.{1,}DAY ONE[\.]{1,}', '', hwotext)
      first_sentence = re.search(r'^(.*)\.', hwotext).group(1)
      # print('First sentence: {0}'.format(first_sentence))
      hwotext = re.sub('\n', ' ', hwotext)
      first_info = re.sub(first_sentence, '', hwotext)
      first_info = re.sub('^\s*\.*', '', first_info)
      self.alerts['hwo']['today'] = [first_sentence.strip(), first_info.strip()]
      

    daytwo = re.search('DAYS TWO THROUGH SEVEN(.*)SPOTTER', bodytext, re.DOTALL).group(1)
    if daytwo:
      print('DayTwo: {0}'.format(daytwo))
      daytwo = re.sub(r'\n{1,}', ' ', daytwo)
      daytwo = re.sub(r'\.{3,}\s*', ' ', daytwo)
      first_sentence = re.search(r'^(.*?)\.', daytwo).group(1)
      # print('First sentence: {0}'.format(first_sentence))
      second_info = re.sub(first_sentence, '', daytwo)
      second_info = re.sub('^\s*\.*', '', second_info)
      self.alerts['hwo']['daystwothroughseven'] = [first_sentence.strip(),
                                                   second_info.strip()]

    spotter = re.search(r'(\.SPOTTER INFORMATION STATEMENT.*?)(\s*\$\$)',
                        bodytext, re.DOTALL)
    if spotter:
      spottext = re.sub(r'\n\n$', '', spotter.group(1))
      spottext = re.sub(r'\.{1,}SPOTTER INFORMATION STATEMENT[\.]{1,}',
                         '', spottext)
      spottext = re.sub('\n', ' ', spottext)
      self.alerts['hwo']['spotter'] = ['Spotter Information Statement',
                                       spottext.strip()]

    if hwotext:
      returntext = '{0}{1}\n\n'.format(returntext, hwotext)
    if spottext:
      returntext = '{0}{1}\n\n'.format(returntext, spottext)

    returntext = re.sub(r'\n\n$', '', returntext)
    return returntext, self.alerts['hwo']


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


  def classify_alerts(self):
    """
    Some warnings are more urgent than others. This method classifies the
    warnings according to immediate threat to life and property, but I am
    not a lawyer and this is really just the way I perceive the usefulness
    of seeing alerts on a dashboard.
    """
    oh_shit = ['Blizzard Warning', 'Ice Storm Warning', 'High Wind Warning',
               'Severe Thunderstorm Warning', 'Tornado Warning',
               'Extreme Wind Warning', 'Gale Warning', 'Hurricane Force Wind Warning',
               'Flash Flood Warning', 'Flood Warning', 'River Flood Warning',
               'Tropical Storm Warning', 'Hurricane Warning', 'Coastal Flood Warning']
    be_aware = ['Winter Storm Watch', 'Winter Weather Advisory', 'Freeze Watch',
                'Freeze Warning', 'Frost Advisory', 'Wind Chill Advisory',
                'Wind Chill Warning', 'Red Flag Warning', 'Dense Fog Advisory',
                'High Wind Watch', 'Wind Advisory', 'Severe Thunderstorm Watch',
                'Tornado Watch', 'Small Craft Advisory', 'Storm Warning',
                'Special Marine Warning', 'Coastal Flood Watch', 'Flash Flood Watch',
                'Flood Watch', 'River Flood Watch', 'Excessive Heat Watch',
                'Excessive Heat Warning', 'Heat Advisory', 'Tropical Storm Watch',
                'Hurricane Watch']

    for alert in self.alert_dict:
      if alert['event_type'] in oh_shit:
        self.alerts['warn'].append(alert)
      elif alert['event_type'] in be_aware:
        self.alerts['watch'].append(alert)
      else:
        print('Unable to classify {0}'.format(alert['event_type']))
        self.alerts['alerts'].append(alert)
        continue

    return self.alerts


