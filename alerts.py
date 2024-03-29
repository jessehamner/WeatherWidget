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
import hwo
import weathersvg as wsvg


class EventDict(object):
  """
  Store one event in a common format.
  """

  def __init__(self, entry, data):
    """
    Instantiate the event object and create an empty dictionary.
    """
    self.entry = entry
    self.sum_str = '{sev} {event_type}, {st_date} - {en_date}\nSummary: {summary}\n\n'
    self.eventdict = {'event_type': '',
                      'startdate': '',
                      'enddate': '',
                      'severity': '',
                      'certainty': '',
                      'summary': '',
                      'event_id': '',
                      'warning_summary': '',
                      'alert_type': '',
                      'alert_icon': 'wi-na.svg',
                     }
    self.data = data

  def populate(self):
    """
    Filter and fill up the eventdict instance.
    """
    summary = self.entry.find('summary').text
    summary = re.sub(r'\*', '\n', summary)

    event_type = self.entry.find('event', text=True)
    if event_type:
      event_type = event_type.text
      logging.info('Event_type info: %s', event_type)
    else:
      logging.info('No cap:event tags in entry?')

    startdate = self.entry.find('effective', text=True)
    if startdate:
      logging.info('Startdate: %s', startdate.text)
      startdate = startdate.text

    # category = entry.find('category').string
    self.eventdict = {'event_type': event_type,
                      'startdate': startdate,
                      'enddate': self.entry.find('expires').string,
                      'severity': self.entry.find('severity').text,
                      'certainty': self.entry.find('certainty').text,
                      'summary': summary,
                      'event_id': self.entry.find('id').text,
                      'alert_type': self.classify_alert(event_type)
                     }
    self.eventdict['warning_summary'] = self.sum_str.format(event_type=event_type,
                                                            st_date=startdate,
                                                            en_date=self.eventdict['enddate'],
                                                            sev=self.eventdict['severity'],
                                                            summary=summary)
    self.eventdict['alert_icon'] = wsvg.assign_icon(self.eventdict['event_type'],
                                                    self.data['defaults']['icon_match'])

    if self.eventdict['alert_type']:
      if self.eventdict['alert_type'] == 'warn':
        logging.info('event_type matched "warnings" list. Assigning "warning.svg"')
        self.eventdict['alert_icon'] = 'warning.svg'
      elif self.eventdict['alert_type'] == 'watch':
        logging.info('event_type matched "watches" list. Assigning "watch.svg"')
        self.eventdict['alert_icon'] = 'watch.svg'
      elif self.eventdict['alert_type'] == 'alert':
        logging.info('event_type matched "alerts" list. Assigning "watch.svg"')
        self.eventdict['alert_icon'] = 'watch.svg'
      else:
        logging.warn('Unable to match alert type to event_type. Using default.')
    else: 
      self.eventdict['alert_icon'] = 'wi-na.svg'

    logging.debug('Warning summary: %s', self.eventdict['warning_summary'])
    return self.eventdict


  def classify_alert(self, event_type):
    """
    Some warnings are more urgent than others. This method classifies the
    warnings according to immediate threat to life and property, but I am
    not a lawyer and this is really just the way I perceive the usefulness
    of seeing alerts on a dashboard.
    """
    if event_type.lower() in self.data['defaults']['watches']:
      return 'watch'
    elif event_type.lower() in self.data['defaults']['warnings']:
      return 'warn'
    elif event_type.lower() in self.data['defaults']['alerts']:
      return 'alert'

    logging.warn('Unable to classify %s', event_type)
    return 'alert'


class Alerts(object):
  """
  download and parse alerts, hazards, and spotter activation info.
  """

  def __init__(self,
               data='',
               outputfile='current_hwo.txt',
               outputalertsfile='alerts_text.txt'):
    """
    Instantiate the Alerts object and set up common variables.
    """
    self.data = data
    self.defaults = self.data['defaults']
    self.hwo_text = ''
    self.outputfile = outputfile
    self.outputalertsfile = outputalertsfile
    self.alerts = dict(hwo=dict(),
                       flags=dict(has_watches=False,
                                  has_warnings=False,
                                  has_alerts=False,
                                  has_spotter=False),
                       alert=[],
                       watch=[],
                       warn=[]
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
    hwo_dict = hwo.HWO(self.data)
    hwo_dict.get_hwo()
    hwo_dict.split_hwo()
    self.alerts['hwo'] = hwo_dict.hwodict

    textfilepath = os.path.join(self.data['output_dir'], 'today_hwo.txt')
    if not self.alerts['hwo']['today_text']:
      self.alerts['hwo']['today_text'] = nodata
    wf.write_text(filepath=textfilepath, some_text=self.alerts['hwo']['today_text'])

    if self.alerts['hwo'] is None:
      self.alerts['hwo'] = dict(today=[nodata, nodata], spotter=[nodata, nodata],
                                daystwothroughseven=[nodata, nodata])

    logging.info('Getting alerts for these counties: %s', self.data['alert_counties'].keys())
    self.get_current_alerts()
    self.set_flags()

    alertpath = os.path.join(self.data['output_dir'], self.outputalertsfile)
    if not self.alerts:
      try:
        if os.path.exists(alertpath):
          os.remove(alertpath)
      except OSError as exc:
        logging.error('OS Error: %s}', exc)

    wf.write_json(some_dict=self.alerts,
                  filename='alerts.json',
                  outputdir=self.data['output_dir'])
    wf.write_dict(filepath=alertpath, some_dict=self.alerts)

    return True


  def set_flags(self):
    """
    Go through the alerts and HWO and see what booleans should be set.
    """
    nospotter = 'Spotter activation is not expected at this time'
    if self.alerts['warn']:
      self.alerts['flags']['has_warnings'] = True
    if self.alerts['watch']:
      self.alerts['flags']['has_watches'] = True
    if self.alerts['alert']:
      self.alerts['flags']['has_alerts'] = True
    if re.search(nospotter, self.alerts['hwo']['spotter'][1]):
      self.alerts['flags']['has_spotter'] = False
    else:
      self.alerts['flags']['has_spotter'] = True

    return True


  def get_county_alerts(self, key):
    """
    Retrieve any alerts for a given county.
    """
    county_alerts = []
    county_params_dict = {'x': self.data['alert_counties'][key][1],
                          'y': int(self.data['alert_counties'][key][0])
                         }
    logging.debug('County params dict for HTTPS request: %s', str(county_params_dict))
    try:
      response = requests.get(self.data['defaults']['alerts_url'],
                              params=county_params_dict,
                              verify=True, timeout=10)
    except Exception as exc:
      logging.error('Exception when requesting current alerts: %s', exc)
      return None

    if response.status_code == 200:
      logging.debug('Response from NWS alerts server was 200. Continuing.')
      if response.headers['Content-Type'] == 'text/xml':
      # Parse the feed for relevant content:
        entries = BeautifulSoup(response.text, 'xml').find('feed').find_all('entry')
      else:
        logging.error('Response content is: %s', response.headers['Content-Type'])
        logging.debug('Response text from NWS server: %s', response.text)
        return None
    else:
      logging.error('Response from NWS alerts server is: %s', response.status_code)
      return None

    logging.info('Now checking alerts xml for county: %s.', key)
    for entry in entries:
      title = entry.find('title').text
      logging.debug('title: %s', title)
      if re.search(r'^There are no active watches', title):
        logging.info('No active watches for this area.')
        return False

      logging.debug('Entry: %s', entry)
      warning_county = self.is_county_relevant(key,
                                               entry,
                                               tagname='areaDesc')
      if warning_county:
        logging.info('Found warning for %s county', warning_county)
        logging.debug('Text of warning entry: %s', entry.prettify())
        event_id = entry.find('id').text
        logging.debug('event id appears to be: %s', event_id)

        edt = EventDict(entry, self.data)
        edt.populate()
        logging.info('This event belongs in list: %s', edt.eventdict['alert_type'])
        county_alerts.append(edt.eventdict)

    return county_alerts


  def check_duplicate(self, current_dict):
    """
    Run through each event ID already in the self.alerts[] dict. Return True
    if the ID is there.
    """
    current_id = current_dict['event_id']
    logging.info('checking event_id "%s" for redundancy.', current_id)
    warns = ['alert', 'watch', 'warn']
    for warntype in warns:
      logging.debug('Existing entries: %s', str(self.alerts[warntype]))
      for existing in self.alerts[warntype]:
        logging.debug('Checking %s vs %s', existing['event_id'], current_id)
        if existing['event_id'] == current_id:
          logging.info('Matched %s to %s -- returning True', existing['event_id'], current_id)
          return True
        if existing['summary'] == current_dict['summary']:
          logging.info('Identical summary text. -- returning True')
          return True
    logging.info('Cycled through every entry in self.alerts. Returning False.')
    return False


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
    if self.data['alert_counties'].keys() is None:
      logging.info('No counties in submitted parameters. Returning -None-')
      return None

    for county in self.data['alert_counties'].keys():
      county_alerts = self.get_county_alerts(county)
      if not county_alerts:
        continue

      for already in county_alerts:
        logging.info('checking event_id "%s" for redundancy.', already['event_id'])
        if self.check_duplicate(already):
          continue
        logging.debug('event dictionary: %s', str(already))
        self.alerts[already['alert_type']].append(already)

    return self.alerts


  def is_county_relevant(self, key, xml_entry, tagname='areaDesc'):
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
    except AttributeError as exc:
      logging.error('Attribute Error: %s. Returning None.', exc)
      return None

    for county in clist:
      logging.info('Checking county %s', county)
      if county.strip() == key:
        return county.strip()

    return None
