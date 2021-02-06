
# Weather Widget

A small set of python and bash utilities to retrieve radar images and the 
text of the Hazardous Weather Outlook for a given region from the 
US National Weather Service. On Mac OS X, these scripts integrate nicely with
[GeekTool](https://www.tynsoe.org/v2/geektool/) 
desktop widgets. On linux, these resources can be nicely incorporated to a <a href="https://github.com/tabler/tabler">tabler</a> (based on Angular.js) dashboard/webpage.

<p align="center">
<img src="https://github.com/jessehamner/WeatherWidget/blob/master/images/desktop.png" width="300" alt-text="GeekTool desktop widgets showing radar image and hazardous weather outlook information along with forecast and hydrograph.">
</p>


## Prerequisites

[Python](https://www.python.org/), and either [bash](https://www.gnu.org/software/bash/) or [zsh](http://zsh.sourceforge.net/). I have no idea if this works on the Windows 10 bash interpreter.
[ImageMagick](https://imagemagick.org/) is also required. This codebase is generally intended for Mac OS X and Linux,
but obviously there are Windows versions of all of this software, but I don't
regularly use Windows.
[Erik Flowers's weather icons](https://erikflowers.github.io/weather-icons/)


## Quick Start

- Install prerequisites, if needed (`requests` and `bs4` for python; ImageMagick libraries)
- Change three variables in the Python script
- Make sure the hard-coded paths to the `convert` binary are correct (might be `/usr/bin/convert`, might be `/opt/local/bin/convert`, might be something else)
- If you don't have any cities larger than 1M people nearby, change the name of the weather station `City_xxxx_Short.gif` file in `merge_backgrounds.sh`
- Put the bash and python scripts into a directory on your PATH
- Run the python script once, manually, to ensure that everything works and to get the background images you need to have
- Run `merge_backgrounds.sh` to make composited background images for the radar images
- Set up the GeekTool widgets, if desired
- Set up the periodic execution of the scripts with `cron` or `launchd`


## Python

The codebase has a library of functions, classes, and methods, held together with some glue in 
main(). For locations other than Fort Worth / DFW, the end-user will need to
change numerous abbreviations in the YaML settings file, including: one for the 
[weather forecast office](https://en.wikipedia.org/wiki/List_of_National_Weather_Service_Weather_Forecast_Office), 
one for the 
[radar station](https://radar.weather.gov/)
, and one for the
[local conditions station abbreviation](https://w1.weather.gov/xml/current_obs/).

More recently, functions have been added to gather forecast information from
[the NWS web API](https://graphical.weather.gov/xml/rest.php)

and hydrologic information from 
[the NWS Advanced Hydrologic Prediction Service](https://water.weather.gov/ahps2/hydrograph.php).

The YAML settings file does require a lot of abbreviations and such, but it's
all pretty well contained in that one file. (Exception: merge_backgrounds.sh still hasn't been adapted for the settings file)


### Basic program flow:

#### Python
- Check for some required background images and gets them if needed.
- Retrieve current conditions
- Get the radar image (currently b0rked, because the NWS changed how they distribute weather radar data in December 2020)
- Get the warnings image ("boxes" for overlaying)
- Get the Hazardous Weather Outlook and parse it
- Check for weather alerts
- Get the weather forecasts and parse them
- Get the hydrologic graph for the local river gauge, if any
- Write out files to `/tmp/` (or where specified in the settings file)

#### bash
- Run the python script
- Check for an overlay graphic (used in compositing the radar image)
- Clean up the last observations
- Use ImageMagick to composite the current radar image and backgrounds
- Make a radar animation of up to the last 20 radar images

## Limitations

The [National Weather Service API](https://www.weather.gov/documentation/services-web-api)
currently lists only one endpoint as valid, the `https://api.weather.gov/alerts` endpoint. 
As of this writing, the "current observations" also works, though I do not know if the coverage is universal.

## Setting Up Scheduled Jobs

### Mac OS X 

Before the first run, the end-user must modify the `plist`. There are sensible defaults but
the path to the scripts _must_ be set before it can run successfully.

Troubleshooting note: I found that the 
[scripts don't necessarily have access to
a PATH variable](https://superuser.com/questions/1093832/cant-get-launchd-plist-run-successfully-in-mac-os-x) 
-- meaning the absolute paths must be specified for everything.

Put the `getweather.plist` file into `~/Library/LaunchAgents/`

If you have already done this once, you may need to `unload` the plist first.

`launchctl unload ~/Library/LaunchAgents/getweather.plist`

`launchctl load ~/Library/LaunchAgents/getweather.plist`

To use GeekTool, one must also set up a widget ("geeklet").

### Linux

Add a line to `/etc/crontab` and be sure that the end of the file contains a 
blank line, or else the last line of the file won't be parsed.
The line might look like this (though using root is a terrible idea and that's
an issue I will fix):

```
# Get weather radar a minute after the image is scheduled to appear:
3,6,10,15,19,23,27,35,38,43,47,51,55,59 * * * * root  /opt/weatherwidget/getweather.sh
```


### That other Geeklet

In case you're curious (one person was) about the "Time Zones" geeklet seen in the desktop screencap, the bash command is this:

```bash
echo "Mtn View:   $(env TZ=America/Los_Angeles date +'%l:%M %p %A')";echo "Dallas:     $(env TZ=America/Chicago date +'%l:%M %p %A')";echo "Boston:     $(env TZ=America/New_York date +'%l:%M %p %A')";echo "London:     $(env TZ=Europe/London date +'%l:%M %p %A')";echo "Amsterdam:  $(env TZ=Europe/Amsterdam date +'%l:%M %p %A')";echo "Banglalore: $(env TZ=Asia/Kolkata date +'%l:%M %p %A')"
```
