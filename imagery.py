"""
imagery.py: a Class for obtaining weather satellite imagery from NOAA.
"""

from __future__ import print_function

import os
import re
import logging
import requests
from bs4 import BeautifulSoup
import weather_functions as wf

class Imagery(object):
  """
  Enable clean retrieval of the most recent GOES image for a single band.

  """

  def __init__(self, band='', data=''):
    """
    Initial parameters are simple, but the data dictionary holds a few
    important variables.
    """
    self.band = band
    self.data = data
    self.defaults = data['defaults']
    self.sat = data['goes_sat']
    self.sector = data['goes_sector']
    self.res = data['goes_res']
    self.url = data['defaults']['goes_url'].format(sat=self.sat, sector=self.sector, band=self.band)
    self.fileslist = []
    self.today_v = self.data['today_vars']
    self.output_dir = self.data['output_dir']
    self.goes_current = {'visible': '',
                         'preferred_band': '',
                         'image_html': '',
                         'id': 'sat_image_thumb'
                        }


  def get_current_image(self):
    """

    Clean up first
    Get list of files
    Get timestamps
    Determine current timestamp
    Get current image
    Log
    Done
    """

    self.goes_cleanup()
    try:
      self.fileslist = self.get_goes_list()
      timestamps = self.get_goes_timestamps()
      current_timestamp = timestamps[-1]
      print('Current timestamp: {0}'.format(current_timestamp))
    except Exception as exc:
      print('Exception when evaluating current timestamps, {0}:\n{1}'.format(timestamps, exc))
      return False

    try:
      current_image = self.get_goes_image(timehhmm=current_timestamp)
      print('retrieved {0}'.format(current_image))
      self.goes_current['preferred_band'] = current_image
      self.goes_current['image_html'] = '<img src="{0}" alt="Current GOES image">'.format(os.path.join(self.data['image_dir'], current_image))
      wf.write_json(self.goes_current, outputdir=self.output_dir, filename='goes.json')
      return True
    except Exception as exc:
      print('Exception: {0}'.format(exc))
      return False


  def get_daily_list(self, doy, year, links):
    """
    Get the image list for a given day of the year.

    """
    filelist = []
    todaystring = '{0}{1}'.format(year, doy)
    myimage = re.compile('ABI-{0}-{1}-{2}'.format(self.sector, self.band, self.res))
    for i in links:
      if i.has_attr("href"):
        filename = i['href']
        # print('Checking file: "{0}"'.format(filename))
      try:
        if myimage.search(filename):
          if re.search(self.res, filename) and re.search(todaystring, filename):
            filelist.append(filename)
      except KeyError:
        pass
      except AttributeError:
        pass

    return filelist


  def get_goes_list(self):
    """
    GOES images post every 5 minutes, but there is no guarantee that you will
    know the minute of the image when concatenating the filename.
    Therefore, this function pulls a list from the specified directory and
    returns the list of files from today with the specified resolution for use.
    """
    # print('Checking url: {0}'.format(url))
    filelist = BeautifulSoup(requests.get(self.url).text, 'html.parser')
    links = filelist.find_all("a", attrs={"href": True})
    files = []

    localdoy = int(self.today_v['doy'])
    localyear = int(self.today_v['year'])
    files.extend(self.get_daily_list(localdoy, localyear, links))
    if localdoy > 364:
      localyear = localyear + 1
      localdoy = 1
    else:
      localdoy = localdoy + 1

    tomorrow_files = self.get_daily_list(localdoy, localyear, links)
    if tomorrow_files:
      # print('Files from tomorrow, UTC: {0}'.format(tomorrow_files))
      self.today_v['doy'] = localdoy
      self.today_v['year'] = localyear
      files.extend(tomorrow_files)
      # print('Files from today and tomorrow: {0}'.format(files))

    return files


  def get_goes_timestamps(self):
    """
    Extract image timestamps from the date portion of GOES image list.
    Return a list of those (UTC) timestamps.
    """
    band_timestamps = []
    yeardoy = '{0}{1}'.format(self.today_v['year'], self.today_v['doy'])
    # print('year-doy combination tag: {0}'.format(yeardoy))
    for filename in self.fileslist:
      try:
        protostamp = re.search(yeardoy + r'(\d{4})', filename).groups(1)[0]
        if protostamp:
          band_timestamps.append(protostamp)
      except Exception as exc:
        print('Exception: {0}'.format(exc))
        continue

    return band_timestamps


  def get_goes_image(self, timehhmm):
    """
    Retrieve current GOES weather imagery.
    """
    image = self.defaults['goes_img'].format(year=self.today_v['year'],
                                             doy=self.today_v['doy'],
                                             timeHHMM=timehhmm,
                                             sat=self.sat,
                                             sector=self.sector,
                                             band=self.band,
                                             resolution=self.res
                                            )
    # image = '20200651806_GOES16-ABI-sp-NightMicrophysics-2400x2400.jpg'
    returned_val = requests.get(os.path.join(self.url, image), verify=False)
    with open(os.path.join(self.output_dir, image), 'wb') as satout:
      satout.write(bytearray(returned_val.content))

    with open(os.path.join(self.output_dir, 'goes_current.jpg'), 'wb') as satout:
      satout.write(bytearray(returned_val.content))

    return image


  def goes_cleanup(self):
    """
    Remove GOES imagery older than two days.
    GOES image are stored in a format like:
    YYYYDDDHHMM_GOESNN-ABI-sp-BAND-PIXELSxPIXELS.jpg
    So at its simplest, take DDD, subtract three, and delete files that match
    that filename or earlier.
    Note that on January 1 and 2, the year will need to be changed as well.
    """
    thefiles = [a for a in os.listdir(self.output_dir) if re.search('GOES', a)]
    today_int = int(self.today_v['doy'])
    cur_year_int = int(self.today_v['year'])
    keepme = []

    for i in range(0, 3):
      # determine appropriate year and day, if needed.
      leadtag = str('{0}{1}'.format(cur_year_int, (today_int - i)))
      keepme.extend([a for a in thefiles if re.search(leadtag, a)])

    removeme = [a for a in thefiles if a not in keepme]
    try:
      [os.remove(b) for b in [os.path.join(self.output_dir, a) for a in removeme]]
    except Exception as exc:
      print('Exception! {0}'.format(exc))
      return False

    return True
