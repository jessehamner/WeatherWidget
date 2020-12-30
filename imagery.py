"""
imagery.py: a Class for obtaining weather satellite imagery from NOAA.
"""

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
    self.res = data['goes_res']
    self.url = data['defaults']['goes_url'].format(sat=data['goes_sat'],
                                                   sector=data['goes_sector'],
                                                   band=self.band)
    self.fileslist = []
    self.today_v = self.data['today_vars']
    self.goes_current = {'visible': '',
                         'preferred_band': '',
                         'image_html': '',
                         'id': 'sat_image_thumb'
                        }

  def get_all(self):
    """
    Convenience function to retrieve several images.
    """
    self.get_current_image()
    self.get_forecast_map()
    self.get_national_temp_map()
    return True


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
    image_html = '<img src="{img}" alt="Current GOES image">'
    try:
      self.fileslist = self.get_goes_list()
      timestamps = self.get_goes_timestamps()
    except Exception as exc:
      logging.error('Exception when determining current timestamps: %s', exc)
      return False

    try:
      current_timestamp = timestamps[-1]
      logging.info('Current timestamp: %s', current_timestamp)
    except Exception as exc:
      logging.error('Exception when evaluating current timestamps, %s: %s', timestamps, exc)
      return False

    try:
      current_image = self.get_goes_image(timehhmm=current_timestamp)
      img_path = os.path.join(self.data['image_dir'], current_image)
      logging.info('retrieved %s', current_image)
      self.goes_current['preferred_band'] = current_image
      self.goes_current['image_html'] = image_html.format(img=img_path)
      wf.write_json(self.goes_current,
                    outputdir=self.data['output_dir'],
                    filename='goes.json')
      return True
    except Exception as exc:
      logging.error('Exception: %s', exc)
      return False


  def get_daily_list(self, localyear, localdoy, links):
    """
    Get the image list for a given day of the year.

    """
    filelist = []
    todaystring = '{0}{1}'.format(localyear, localdoy)
    logging.debug('Today-string for GOES imagery: %s', todaystring)
    myimage = re.compile('ABI-{0}-{1}-{2}'.format(self.data['goes_sector'], self.band, self.res))
    for link in links:
      if link.has_attr("href"):
        filename = link['href']
        if re.search(self.res, filename) and re.search(todaystring, filename):
          logging.debug('File from today: "%s"', filename)
      try:
        if myimage.search(filename):
          if re.search(self.res, filename) and re.search(todaystring, filename):
            filelist.append(filename)
      except KeyError as exc:
        logging.error('KeyError: %s', exc)
      except AttributeError as exc:
        logging.error('AttributeError: %s', exc)

    logging.debug('Returning file list.')
    return filelist


  def get_goes_list(self):
    """
    GOES images post every 5 minutes, but there is no guarantee that you will
    know the minute of the image when concatenating the filename.
    Therefore, this function pulls a list from the specified directory and
    returns the list of files from today with the specified resolution for use.
    At midnight UTC, it becomes necessary to consider the previous (UTC!) day's
    images, at least for a few minutes. And, on New Year's Eve, it will be
    necessary to consider the previous *year* for a few minutes: so, corner
    cases require less elegant programming, ha ha.
    """
    logging.debug('Checking url: %s', self.url)
    filelist = BeautifulSoup(requests.get(self.url).text, 'html.parser')
    links = filelist.find_all("a", attrs={"href": True})
    files = []

    localdoy = int(self.today_v['utcdoy'])
    localyear = int(self.today_v['utcyear'])
    logging.info('UTC year: %s; UTC day-of-the-year: %s', localyear, localdoy)
    files.extend(self.get_daily_list(localyear, localdoy, links))
    if localdoy == 1:
      logging.debug('Today is the first of the year. Yesterday is previous year.')
      localdoy = 365  # TODO check for leap year with timedelta instead
      localyear = localyear - 1
    else:
      localdoy = localdoy - 1

    additional_files = self.get_daily_list(localyear, localdoy, links)
    if additional_files:
      logging.debug('Files from previous day, UTC: %s', str(additional_files))
      files.extend(additional_files)

    return files


  def get_goes_timestamps(self):
    """
    Extract image timestamps from the date portion of GOES image list.
    Return a list of those (UTC) timestamps.
    """
    band_timestamps = []
    yeardoy = '{0}{1}'.format(self.today_v['year'], self.today_v['utcdoy'])
    logging.debug('year-doy combination tag: %s', yeardoy)
    for filename in self.fileslist:
      try:
        protostamp = re.search(yeardoy + r'(\d{4})', filename)
        if protostamp:
          band_timestamps.append(protostamp.groups(1)[0])
      except Exception as exc:
        logging.error('Exception: %s', exc)
        continue

    return band_timestamps


  def get_goes_image(self, timehhmm):
    """
    Retrieve current GOES weather imagery.
    """
    image = self.data['defaults']['goes_img'].format(year=self.today_v['year'],
                                                     doy=self.today_v['doy'],
                                                     timeHHMM=timehhmm,
                                                     sat=self.data['goes_sat'],
                                                     sector=self.data['goes_sector'],
                                                     band=self.band,
                                                     resolution=self.res
                                                    )
    # image = '20200651806_GOES16-ABI-sp-NightMicrophysics-2400x2400.jpg'
    returned_val = requests.get(os.path.join(self.url, image), verify=False)
    with open(os.path.join(self.data['output_dir'], image), 'wb') as satout:
      satout.write(bytearray(returned_val.content))
      logging.debug('Writing image %s to path %s', image, self.data['output_dir'])

    with open(os.path.join(self.data['output_dir'], 'goes_current.jpg'), 'wb') as satout:
      satout.write(bytearray(returned_val.content))
      logging.debug('Writing "goes_current.jpg" to path %s', self.data['output_dir'])

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
    thefiles = [a for a in os.listdir(self.data['output_dir']) if re.search('GOES', a)]
    today_int = int(self.today_v['doy'])
    cur_year_int = int(self.today_v['year'])
    keepme = []

    for i in range(0, 3):
      # determine appropriate year and day, if needed.
      leadtag = str('{0}{1}'.format(cur_year_int, (today_int - i)))
      keepme.extend([a for a in thefiles if re.search(leadtag, a)])

    removeme = [a for a in thefiles if a not in keepme]
    try:
      [os.remove(b) for b in [os.path.join(self.data['output_dir'], a) for a in removeme]]
      logging.debug('Removing outdated GOES imagery.')
    except Exception as exc:
      logging.error('Exception! %s', exc)
      return False

    return True


  def get_file(self, url, mapname, file_to_retrieve, verify=False):
    """
    Generic helper function to retrieve a file from a given url and write it
    to the defined output directory.
    """
    target_url = os.path.join(url, file_to_retrieve)
    logging.info('Retrieving %s and saving to %s', target_url, mapname)
    response = requests.get(url=target_url, verify=verify)
    if response.status_code != 200:
      logging.warn('Response code: %s. Returning False.', response.status_code)
      return False
    with open(os.path.join(self.data['output_dir'], mapname), 'wb') as outputfile:
      outputfile.write(response.content)
      outputfile.close()
    return True


  def get_forecast_map(self, mapname='national_forecast_map.png'):
    """
    Retrieve the national forecast map.

    """
    return_value = self.get_file(url=self.data['defaults']['forecast_map_url'],
                                 file_to_retrieve=self.data['defaults']['forecast_map_file'],
                                 mapname=mapname,
                                 verify=False)
    return return_value


  def get_national_temp_map(self, mapname='national_high_temp_map.png'):
    """
    Pull the national high temperature map from
    https://graphical.weather.gov/images/conus/MaxT1_conus.png
    """
    logging.debug('Retrieving national high temperatures map from %s',
                  self.data['defaults']['temp_map_url'])
    return_value = self.get_file(url=self.data['defaults']['temp_map_url'],
                                 mapname=mapname,
                                 file_to_retrieve=self.data['defaults']['temp_map_file'],
                                 verify=True)
    return return_value
