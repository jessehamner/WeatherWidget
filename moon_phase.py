"""
moon_phase.py: a class for determining the current phase of the moon,
and for assigning a weather icon for that phase.
"""

from __future__ import print_function

import os
import re
import logging
import requests
import datetime
from bs4 import BeautifulSoup


class Moon_phase(object):
  """
  While the length of an average lunar cycle is 29.53 days, to avoid 
  propagation errors, this class retrieves a table from NOAA that shows the 
  new moon days and times for the year, and thus the code resets to a known
  precise zero each month.
  """

  def __init__(self, data=''):
    """
    Pull in the date data, mostly.
    """
    self.data = data
    self.today_v = data['today_vars']
    self.baseurl = 'https://tidesandcurrents.noaa.gov/moon_phases.shtml'
    self.phases = {
        '0': 'wi-moon-alt-new.svg',
        '1': 'wi-moon-alt-new.svg',
        '2': 'wi-moon-alt-waxing-crescent-1.svg',
        '3': 'wi-moon-alt-waxing-crescent-2.svg',
        '4': 'wi-moon-alt-waxing-crescent-3.svg',
        '5': 'wi-moon-alt-waxing-crescent-4.svg',
        '6': 'wi-moon-alt-waxing-crescent-5.svg',
        '7': 'wi-moon-alt-waxing-crescent-6.svg',
        '8': 'wi-moon-alt-first-quarter.svg',
        '9': 'wi-moon-alt-waxing-gibbous-1.svg',
        '10': 'wi-moon-alt-waxing-gibbous-2.svg',
        '11': 'wi-moon-alt-waxing-gibbous-3.svg',
        '12': 'wi-moon-alt-waxing-gibbous-4.svg',
        '13': 'wi-moon-alt-waxing-gibbous-5.svg',
        '14': 'wi-moon-alt-waxing-gibbous-6.svg',
        '15': 'wi-moon-alt-full.svg',
        '16': 'wi-moon-alt-waning-gibbous-1.svg',
        '17': 'wi-moon-alt-waning-gibbous-2.svg',
        '18': 'wi-moon-alt-waning-gibbous-3.svg',
        '19': 'wi-moon-alt-waning-gibbous-4.svg',
        '20': 'wi-moon-alt-waning-gibbous-5.svg',
        '21': 'wi-moon-alt-waning-gibbous-6.svg',
        '22': 'wi-moon-alt-third-quarter.svg',
        '23': 'wi-moon-alt-waning-crescent-1.svg',
        '24': 'wi-moon-alt-waning-crescent-2.svg',
        '25': 'wi-moon-alt-waning-crescent-3.svg',
        '26': 'wi-moon-alt-waning-crescent-4.svg',
        '27': 'wi-moon-alt-waning-crescent-5.svg',
        '28': 'wi-moon-alt-waning-crescent-6.svg',
        '29': 'wi-moon-alt-new.svg'
        }

    self.new_moon_dict = dict(year={})

  
  def get_moon_phase(self):
    """
    run methods in the correct order.
    """
    self.retrieve_new_moon_dict()
    svg_name = self.moon_phase_today()
    return svg_name


  def bs_pull_table_cell(self, row, index):
    """
    Helper function to sanitize and pull a specific cell from a specific table
    row.
    """
    try:
      return re.sub('\xa0', '', row.find_all('td')[index].text)
    except IndexError as e:
      print('IndexError trying to retrieve table cell {0}: {1}'.format(index, e))
      print('Row:\n{0}'.format(row))
      return 'NA'


  def retrieve_new_moon_dict(self):
    """
    Using some simple math, compute the moon phase for today, using
    NOAA's data for new moons in the current year.
    """
    thisyear = self.today_v['year']
    self.new_moon_dict['year'][thisyear] = {}
    url_args = {'year': thisyear, 'data_type': 'phaX1'}
    moon_table = requests.get(self.baseurl, params=url_args,
                              verify=False, timeout=10)

    if moon_table.status_code != 200:
      print('Unable to get a proper response from NOAA server. Returning False.')
      return False

    soup = BeautifulSoup(moon_table.text, 'html.parser')
    tables = soup.body.find_all('table')
    phase_table = tables[0]
    trows = phase_table.find_all('tr')
    for row in trows:
      if row.find_all('th'):
        continue
      rowmonth = self.bs_pull_table_cell(row, 1)
      rowday = self.bs_pull_table_cell(row, 2)
      rowtime = self.bs_pull_table_cell(row, 3)
      self.new_moon_dict['year'][thisyear][rowmonth] = [rowday, rowtime]

    return self.new_moon_dict


  def moon_phase_today(self):
    """
    Take in a date and determine the moon's phase on that day, using
    NOAA new moon dates and times as the time-base / sync.
    """
    today = self.today_v['utcnow']
    year = self.today_v['year']
    mon = self.today_v['mon']
    nextmoonstring = '{0}-{1}-{2} {3}'.format(year, mon,
                                              self.new_moon_dict['year'][year][mon][0],
                                              self.new_moon_dict['year'][year][mon][1])
    nextnewmoon = datetime.datetime.strptime(nextmoonstring, '%Y-%b-%d %H:%M')
    difference = nextnewmoon - today
    cycle = 29.53 # days in an average moon cycle

    place_in_cycle = (datetime.timedelta(29.53) - difference)
    days_into_cycle = ((place_in_cycle.days * 24) + (place_in_cycle.seconds/3600.0)) / 24
    while days_into_cycle > cycle:
      days_into_cycle = days_into_cycle - cycle

    print('Place in the cycle: {0}'.format(days_into_cycle))
    icon_index = int((days_into_cycle / cycle) * 29)

    print('Icon should be: {0}'.format(self.phases[str(icon_index)]))

    return self.phases[str(icon_index)]
