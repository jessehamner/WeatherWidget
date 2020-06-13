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
                      'warning_summary': ''
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
      print('Event_type info: {0}'.format(event_type.text))
      event_type = event_type.text
    else:
      print('No cap:event tags in entry?')

    startdate = self.entry.find('effective', text=True)
    if startdate:
      # print('Startdate: {0}'.format(startdate.text))
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

    print('Unable to classify {0}'.format(event_type))
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
      self.alerts['hwo']['today_text'] = ('Hazardous Weather Outlook:\n ' + nodata)
    wf.write_text(filepath=textfilepath, some_text=self.alerts['hwo']['today_text'])

    if self.alerts['hwo'] is None:
      self.alerts['hwo'] = dict(today=[nodata, nodata], spotter=[nodata, nodata],
                                daystwothroughseven=[nodata, nodata])
    wf.write_json(outputdir=self.data['output_dir'],
                  filename='hwo.json',
                  some_dict=self.alerts['hwo'])

    print('Getting alerts for the following counties: {0}.'.format(self.data['alert_counties']))
    self.get_current_alerts()

    self.set_flags()


    alertpath = os.path.join(self.data['output_dir'], self.outputalertsfile)
    if not self.alerts:
      try:
        if os.path.exists(alertpath):
          os.remove(alertpath)
      except OSError as exc:
        print('OS Error: {0}'.format(exc))

    wf.write_json(some_dict=self.alerts,
                  filename='alerts.json',
                  outputdir=self.data['output_dir'])
    wf.write_dict(filepath=alertpath, some_dict=self.alerts)

    return True


  def set_flags(self):
    """
    Go through the alerts and HWO and see what booleans should be set.
    """
    if self.alerts['warn']:
      self.alerts['flags']['has_warnings'] = True
    if self.alerts['watch']:
      self.alerts['flags']['has_watches'] = True
    if self.alerts['warn']:
      self.alerts['flags']['has_warnings'] = True
    if self.alerts['warn']:
      self.alerts['flags']['has_warnings'] = True
    return True


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
    except Exception as exc:
      print('Exception when requesting current alerts: {0}'.format(exc))
      return None

    if response.status_code == 200 and response.headers['Content-Type'] == 'text/xml':
      # Parse the feed for relevant content:
      entries = BeautifulSoup(response.text, 'xml').find('feed').find_all('entry')
    else:
      print('ERROR: Response from NWS alerts server is: {0}'.format(response.status_code))
      return None

    for entry in entries:
      print('Now checking alerts xml.')
      warning_county = self.is_county_relevant(entry,
                                               tagname='areaDesc')
      if warning_county:
        print('Found warning for {0} county.'.format(warning_county))
        print('Text of this warning entry is: {0}'.format(entry.prettify()))
        event_id = entry.find('id').text
        print('event id appears to be: {0}'.format(event_id))

        edt = EventDict(entry, self.data)
        edt.populate()
        self.alerts[edt.eventdict['alert_type']] = edt.eventdict

    return self.alerts


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
    except AttributeError as exc:
      print('Attribute Error: {0}. Returning None.'.format(exc))
      return None

    for county in clist:
      print('Checking county {0}'.format(county))
      if county.strip() in self.data['alert_counties']:
        return county.strip()

    return None
