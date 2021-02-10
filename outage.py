"""
outage.py: check for issues and outages with web resources used by this
library.
"""

from __future__ import print_function

import re
import logging
import datetime
import requests
from bs4 import BeautifulSoup

class Outage(object):
  """
  Fan out and check for outages, then store the info and pass it back up.
  """

  def __init__(self, data=''):
    """
    Instantiate the Outage object and set up common variables.
    """
    self.data = data
    self.defaults = data['defaults']
    self.ftm_params = {'site': 'NWS',
                       'issuedby': data['radar_station'],
                       'product': 'FTM',
                       'format': 'CI',
                       'version': 1,
                       'glossary': 0
                      }
    self.ftm_text = ''
    self.return_text = ''


  def check_outage(self):
    """
    Check a webpage for information about any outages at the radar site.
    The product is called a 'Free Text Message' (FTM).
    'https://forecast.weather.gov/product.php?site=NWS
    &issuedby=FWS&product=FTM&format=CI&version=1&glossary=0'
    The information is identical to the HWO call.
    """

    print('ftm parameter dict: {0}'.format(self.ftm_params))

    try:
      response = requests.get(self.defaults['hwo_url'],
                              params=self.ftm_params,
                              verify=True, timeout=10)
    except requests.exceptions.ConnectionError as exc:
      print('ConnectionError: {0}'.format(exc))
      return None

    html = response.text
    soup = BeautifulSoup(html, 'html.parser')

    if not soup:
      print('WARNING: no returned data from html request for outages.')
      return None

    try:
      pres = soup.body.find_all('pre')
    except TypeError:
      return None
    except AttributeError:
      return None

    for pretag in pres:
      self.ftm_text = pretag.get_text()
      # print('ftm_text: {0}'.format(ftm_text))
      if len(self.ftm_text) > 100:
        self.ftm_text = self.ftm_text.split('\n')
        return True
    return False


  def parse_outage(self):
    """
    Read the outage text, if any, and determine:
    - should it be displayed (i.e. is it timely and current?)
    - what text is relevant (but default to "all of the text")
    """
    if not self.ftm_text:
      print('No outage text seen. Returning -None-')
      return None
    message_date = ''
    for line in self.ftm_text:
      line.strip()
      if re.search(r'^\s*$', line):
        continue
      if re.search(r'^\s*FTM|^000\s*$|^NOUS', line):
        continue
      if re.search('MESSAGE DATE:', line, flags=re.I):
        message_date = re.sub(r'MESSAGE DATE:\s+', '', line, flags=re.I)
        print('Date of issue: {0}'.format(message_date))
        dateobj = datetime.datetime.strptime(message_date, '%b %d %Y %H:%M:%S')
        today = datetime.datetime.now()
        if (today - dateobj) > datetime.timedelta(days=1):
          print('Outage info is older than one day -- ignoring.')
          return None
        else:
          self.return_text = str('{0}\nNWS FTM NOTICE:'.format(self.return_text))

      else:
        self.return_text = str('{0} {1}'.format(self.return_text, line))

    if message_date:
      self.return_text = re.sub('  ', ' ', self.return_text)
      return self.return_text.strip()
    return None
