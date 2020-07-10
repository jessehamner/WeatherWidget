"""
weathersvg.py: a series of utilities to produce small SVG outputs
of useful weather data.
"""

from __future__ import print_function

import os
import re
import svgwrite


def fix_missing(value):
  """
  If there's a missing value for a number, return two dashes. Otherwise,
  return the number.
  """

  try:
    if value == '' or value is None:
      return '--'
    return value
  except Exception as exc:
    print('Returning a missing value string: {0}'.format(exc))
    return '--'
  

def precip_chance_svg(morning, evening, filename, outputdir='/tmp/'):
  """
  Take the day's precip chances and produce a color-coded svg of percentages.
  """
  svg_info = {'high_coords': (8, 16),
              'low_coords': (2, 38),
              'dimensions': (55, 40),
              'colors': ['#baa87d', '#7ae6c0', '#2bb5aa', '#023dbd', '#035740'],
              'fontcolor': 'white'
             }

  bgc = svg_info['colors'][int(max(morning, evening)/100.0 * (len(svg_info['colors']) - 1))]

  if not re.search(r'%$', str(evening)):
    evening = '{0}%'.format(evening)
  if not re.search(r'%$', str(morning)):
    morning = '{0}%'.format(morning)

  style1 = '''.{stylename} {openbrace} font: bold {fontsize}px sans-serif;
  fill:{fontcolor}; stroke:#000000; stroke-width:1px; stroke-linecap:butt;
  stroke-linejoin:miter; stroke-opacity:0.5; {closebrace}'''

  dwg = svgwrite.Drawing(os.path.join(outputdir, filename),
                         size=svg_info['dimensions'])

  dwg_styles = svgwrite.container.Style(content='.background {fill: ' + bgc +
                                        '; stroke: #f0f0f0f0;}')
  dwg_styles.append(content=style1.format(stylename='morning', openbrace='{',
                                          fontsize='18', fontcolor='#f2df94',
                                          closebrace='}'))
  dwg_styles.append(content=style1.format(stylename='evening', openbrace='{',
                                          fontsize='18', fontcolor='#ffd4fb',
                                          closebrace='}'))
  dwg.defs.add(dwg_styles)
  evening = fix_missing(evening) 
  morning = fix_missing(morning) 
  evening_text = svgwrite.text.TSpan(text=evening,
                                     insert=svg_info['high_coords'],
                                     class_='evening')
  morning_text = svgwrite.text.TSpan(text=morning,
                                     insert=svg_info['low_coords'],
                                     class_='morning')
  frame = svgwrite.shapes.Rect(insert=(0, 0),
                               size=svg_info['dimensions'],
                               class_='background')
  text_block = svgwrite.text.Text('', x='0', y='0')
  text_block.add(evening_text)
  text_block.add(morning_text)
  dwg.add(frame)
  dwg.add(text_block)
  dwg.save(pretty=True)

  return 0


def high_low_svg(high, low, filename, outputdir='/tmp/'):
  """
  Use svgwrite to make a simple graphic with high/low temps for the day's
  forecast.
  Unicode deg-Celsius is U+2103 (only for UTF-16)
  Unicode deg-Fahrenheit is U+2109 (only for UTF-16)
  Unicode degree symbol is U+00B0 ('\xb0') -- same as Latin-1 encoding, but is
  not available in 1963-standard 7-bit ASCII
  """

  high_coords = (2, 15)
  low_coords = (2, 36)
  dimensions = (40, 40)
  style1 = '.{stylename} {openbrace} font: bold {fontsize}px sans-serif;\
  fill:{fontcolor}; stroke:#000000; stroke-width:1px; stroke-linecap:butt;\
  stroke-linejoin:miter; stroke-opacity:0.7; {closebrace}'

  dwg = svgwrite.Drawing(os.path.join(outputdir, filename), size=dimensions)
  dwg_styles = svgwrite.container.Style(content='.background {fill: #f0f0f0f0; stroke: #f0f0f0f0;}')
  dwg_styles.append(content=style1.format(stylename='low', openbrace='{',
                                          fontsize='16', fontcolor='blue',
                                          closebrace='}'))
  dwg_styles.append(content=style1.format(stylename='high', openbrace='{',
                                          fontsize='18', fontcolor='red',
                                          closebrace='}'))
  dwg.defs.add(dwg_styles)
  high = fix_missing(high) 
  low = fix_missing(low) 
  high_symbol = (unicode(high) + u'\xb0')
  low_symbol = (unicode(low) + u'\xb0')
  high_text = svgwrite.text.TSpan(text=high_symbol,
                                  insert=high_coords, class_='high')
  low_text = svgwrite.text.TSpan(text=low_symbol,
                                 insert=low_coords, class_='low')
  text_block = svgwrite.text.Text('', x='0', y='0')
  text_block.add(high_text)
  text_block.add(low_text)
  dwg.add(text_block)
  dwg.save(pretty=True)

  return 0


def make_forecast_icons(fc_dict, outputdir='/tmp/'):
  """
  Write out SVG icons of the next three days of temps and precip chances.
  """
  filelabel = 'today_{fctype}_plus_{day}.svg'
  for i in range(0, 3):
    high_low_svg(fc_dict[i]['high'], fc_dict[i]['low'],
                 filelabel.format(fctype='temp', day=i),
                 outputdir=outputdir
                )
    precip_chance_svg(int(fc_dict[i]['precip_morning']),
                      int(fc_dict[i]['precip_evening']),
                      filename=filelabel.format(fctype='precip', day=i),
                      outputdir=outputdir
                     )

  return True


def assign_icon(description, icon_match):
  """
  Try to parse the language in forecasts for each to and match to an
  appropriate weather SVG icon.
  """

  returnvalue = ''
  description = description.strip()
  description = description.lower()
  description = re.sub(r'\s+', ' ', description)
  print('Finding icon for "{0}"'.format(description))
  for key, value in icon_match.iteritems():
    for val in value:
      if description == val.lower().strip():
        returnvalue = key
        print('Matched "{0}"'.format(val.lower()))
        return returnvalue

  print('Unable to match "{0}"'.format(description))
  return 'wi-na.svg'


def css_string(css_dict):
  """
  Convenience function to format a dict into a css_friendly string.
  """
  stylestring = '{'
  for key, value in css_dict.iteritems():
    stylestring = '{0}{1}:{2}; '.format(stylestring, key, value)
  stylestring = stylestring + '}'
  return stylestring


def draw_compass_svg(degrees, data):
  """
  Drawing raw SVG via text and python.
  """
  wcd = data['defaults']['wind_compass']
  # raw_svg_header = '<?xml version="1.0" encoding="utf-8"?>'

  svg_invocation = '''<svg height="{height}" width="{width}" version="1.1" id="{id_label}"
  xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
  x="0px" y="0px" viewBox="{viewbox}"
  style="enable-background:new {viewbox};" xml:ispace="preserve">'''

  circle_css = data['defaults']['circle_css']
  rot1_css = data['defaults']['rot1_css']
  rot1_css['transform'] = 'rotate({0}deg)'.format(degrees)

  svg_css = '<style>circle {0} .rot1 {1}</style>'.format(css_string(circle_css),
                                                         css_string(rot1_css))

  # symbol = '<symbol id="whole-icon"> <g class="rot1">
  # <circle cx="20" cy="20" r="17" id="ring"/>
  # <path d="M20 7 L 27 30 L 20 26 L 13 30 L 20 7 z" id="arrow" /></g> </symbol>'
  # raw_svg_footer = '<use xlink:href="#whole-icon"/></svg>'

  svg_string = '{0}{1}{2}{3}'.format(svg_invocation.format(height=wcd['height'],
                                                           width=wcd['width'],
                                                           id_label=wcd['id_label'],
                                                           viewbox=wcd['viewbox']),
                                     svg_css, wcd['symbol'], wcd['raw_svg_footer'])
    # print(svg_string)
  return svg_string


def wind_direction_icon(heading, sourcepath='static/icons/weather-icons-master/svg'):
  """
  Generate the html for the appropriately rotated SVG file for
  the wind direction.
  """

  filename = 'wi-wind-deg.svg'
  filepath = os.path.join(sourcepath, filename)


  img_html = '''<img src="{0}" width="40" height="40" fill="white"
      transform="rotate({1},20,20)" />'''.format(filepath, int(heading))
  print(img_html)

  return img_html
