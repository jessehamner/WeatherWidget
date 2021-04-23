"""
hwo.py: download and sort the NOAA / All Hazards hazardous weather outlook.
Return a nice dictionary.
"""

import os
import re
import logging
import requests
from bs4 import BeautifulSoup


class HWO(object):
  """
  Hazardous weather outlook (HWO) object class.
  """

  def __init__(self, data, outputfile='hwo.txt'):
    """
    Create an object and empty dictionary.
    """
    self.data = data
    self.outputfile = outputfile
    self.hwo_text = ''
    self.hwodict = dict(spotter=[],
                        dayone=[],
                        daystwothroughseven=[],
                        today_text='',
                        has_spotter=False
                       )


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

    response = requests.get(self.data['defaults']['hwo_url'],
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
    logging.debug('Raw body text of HWO: \n%s', bodytext)

    dayone = re.search(r'(\.DAY ONE.*?)(\.DAYS TWO THROUGH SEVEN.*?)', bodytext, re.DOTALL)
    if dayone:
      hwotext = re.sub(r'\n\n$', '', dayone.group(1))
      hwotext = re.sub(r'\.{1,}DAY ONE[\.]{1,}', '', hwotext)
      first_sentence = re.search(r'^(.*)\.', hwotext).group(1)
      logging.debug('First sentence: %s', first_sentence)
      hwotext = re.sub('\n', ' ', hwotext)
      hwotext = nice_plumbing(hwotext)

      first_info = re.sub(first_sentence, '', hwotext)
      first_info = re.sub(r'^\s*\.*', '', first_info)
      self.hwodict['dayone'] = [first_sentence.strip(), first_info.strip()]

    daytwo = re.search('DAYS TWO THROUGH SEVEN(.*)SPOTTER', bodytext, re.DOTALL)
    if daytwo:
      daytwo = daytwo.group(1)
    if daytwo:
      logging.debug('DayTwo: %s', daytwo)
      daytwo = re.sub(r'\n{1,}', ' ', daytwo)
      daytwo = re.sub(r'\.{3,}\s*', ' ', daytwo)
      first_sentence = re.search(r'^(.*?)\.', daytwo).group(1)
      logging.debug('First sentence: %s', first_sentence)
      second_info = re.sub(first_sentence, '', daytwo)
      second_info = nice_plumbing(second_info)
      self.hwodict['daystwothroughseven'] = [first_sentence.strip(),
                                             second_info.strip()]

    spotter = re.search(r'(\.*SPOTTER INFORMATION STATEMENT.*?)(\s*\$\$)',
                        bodytext, re.DOTALL)
    if spotter:
      spottext = nice_plumbing(spotter.group(1))
      spottext = re.sub(r'SPOTTER INFORMATION STATEMENT[\.]{1,}',
                        '', spottext)
      spottext = re.sub('\n', ' ', spottext)
      self.hwodict['spotter'] = ['Spotter Information Statement',
                                 spottext.strip()]

    if spottext:
      self.hwodict['today_text'] = '{0}{1}\n\n'.format(self.hwodict['dayone'][1],
                                                       spottext)
      if re.search('Spotter activation is not expected at this time', spottext):
        return True
      self.hwodict['has_spotter'] = True
    return True


def nice_plumbing(text):
  """
  Try and regex/tidy some of the text.
  """

  return_text = re.sub(r'^\s*\.*', '', text)
  return_text = re.sub(r'\.\s+\.$', '.', return_text)
  return_text = re.sub(r'\n+$', '', return_text)
  return return_text
