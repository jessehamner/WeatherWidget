"""
radar.py: download and perform image tasks on radar imagery.
"""

from __future__ import print_function

import os
import logging
import requests
from PIL import Image


class Radar(object):
  """
  download and merge radar imagery and layers.
  radar station abbr: data['radar_station']
  radar url: data['radar_url']
  names of all the files needed to overlay: data['graphics_list']


  """

  def __init__(self,
               data=''):
    self.data = data
    self.defaults = data['defaults']
    self.radar_url = data['defaults']['radar_url']
    self.station = data['radar_station']
    self.assets_url = data['defaults']['weather_url_root']
    self.warnings_url = data['defaults']['warnings_url']
    self.problem = False

  def get_radar(self):
    """
    Using the NWS radar station abbreviation, retrieve the current radar image
    and world file from the NWS.
    """

    response1 = requests.get(self.radar_url.format(station=self.station,
                                                   image='N0R_0.gfw'),
                             verify=False, timeout=10)
    if response1.status_code != 200:
      print('Response from server was not OK: {0}'.format(response1.status_code))
      self.problem = True
      return False
    cur1 = open(os.path.join(self.data['output_dir'], 'current_image.gfw'), 'w')
    cur1.write(response1.text)
    cur1.close()

    response2 = requests.get(self.radar_url.format(station=self.station,
                                                   image='N0R_0.gif'),
                             verify=False, timeout=10)
    if response2.status_code != 200:
      print('Response from server was not OK: {0}'.format(response2.status_code))
      self.problem = True
      return False

    cur2 = open(os.path.join(self.data['output_dir'], 'current_image.gif'), 'wb')
    cur2.write(response2.content)
    cur2.close()

    return True


  def get_warnings_box(self):
    """
    Retrieve the severe weather graphics boxes (suitable for overlaying)
    from the NWS for the specified locale.
    """
    warnings = 'Warnings'
    response = requests.get(self.warnings_url.format(station=self.station,
                                                     warnings=warnings
                                                    ),
                            verify=False, timeout=10)
    try:
      cur = open(os.path.join(self.data['output_dir'], 'current_warnings.gif'), 'wb')
      cur.write(response.content)
      cur.close()
      return True
    except Exception as exc:
      print('Exception: {0}'.format(exc))
      self.problem = True
      return False


  def check_assets(self):
    """
    Confirm that layer images from NWS already exist where they should be.
    """
    for asset in self.data['radar_layers']:
      file_url_dir = '{0}'.format(asset.format(r_abbr=self.station))
      filename = file_url_dir.split('/')[-1]
      print('Local file path: {0}'.format(os.path.join(self.data['output_dir'], filename)))
      if not self._check_asset(self.data['output_dir'],
                               filename=filename,
                               url_dir=file_url_dir,
                               url=self.assets_url):
        self.problem = True


    file_url_dir = '{0}'.format(self.defaults['legend_file'].format(radar=self.station))
    filename = file_url_dir.split('/')[-1]
    print('Local legend file path: {0}'.format(os.path.join(self.data['output_dir'], filename)))
    if not self._check_asset(self.data['output_dir'],
                             filename=filename,
                             url_dir=file_url_dir,
                             url=self.defaults['legend_url_root']):
      self.problem = True
      return False

    return True


  def _check_asset(self, outputdir, filename, url_dir, url):
    """

    """
    localpath = os.path.join(outputdir, filename)
    if os.path.isfile(localpath) is False:
      print('Need to retrieve {0} from {1}'.format(localpath, os.path.join(url, url_dir)))
      if self._retrieve_asset(file_url_dir=url_dir, url=url, filename=filename):
        print('Got it.')
      else:
        print('Unable to get the file. Returning False.')
        self.problem = True
        return False

    else:
      print('{0} is where it should be (in {1})'.format(filename, outputdir))
      return True



  def _retrieve_asset(self, file_url_dir, url, filename):
    """

    """

    graphic = requests.get(os.path.join(url, file_url_dir),
                           verify=False, timeout=10)
    with open(os.path.join(self.data['output_dir'], filename), 'wb') as output:
      output.write(graphic.content)
      output.close()
    return True


  def _overlay_composite(self, resultfile='bkg2.gif'):
    """
    Take list of images in output_dir and overlay them as needed to make
    the proper radar overlay image.
    """
    blist = ['highways', 'ring', 'lrg_cities', 'counties']

    im1 = self._open_transparent('highways')
    for layer in blist[1:]:
      temp = self._open_transparent(layer)
      if temp:
        im1.paste(temp, (0, 0), temp)

    im1.save(os.path.join(self.data['output_dir'], resultfile),
             transparency=0)

    return im1


  def _open_transparent(self, layer):
    """
    Open the image and enable transparent layers.
    """
    rad_l = self.data['radar_layers']
    try:
      imagename = rad_l[layer].format(r_abbr=rad_l['r_abbr']).split('/')[-1]
      imagepath = os.path.join(self.data['output_dir'], imagename)
      if not os.path.exists(imagepath):
        return None
    except Exception as exc:
      print('Exception: {0}'.format(exc))
      return None

    try:
      return Image.open(imagepath).convert('RGBA')
    except Exception as exc:
      print('Exception: {0}'.format(exc))
      return None
