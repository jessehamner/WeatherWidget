
# Weather Widget

A small set of python and bash utilities to retrieve radar images and the 
text of the Hazardous Weather Outlook for a given region from the 
US National Weather Service. On Mac OS X, these scripts integrate nicely with
[GeekTool](https://www.tynsoe.org/v2/geektool/) 
desktop widgets.

<p align="center">
<img src="https://github.com/jessehamner/WeatherWidget/blob/master/images/desktop.png" width="300" alt-text="GeekTool desktop widgets showing radar image and hazardous weather outlook information">
</p>


## Prerequisites

[Python](https://www.python.org/), and either [bash](https://www.gnu.org/software/bash/) or [zsh](http://zsh.sourceforge.net/). I have no idea if this works on the Windows 10 bash interpreter.
[ImageMagick](https://imagemagick.org/) is also required. This codebase is generally intended for Mac OS X and Linux,
but obviously there are Windows versions of all of this software, but I don't
regularly use Windows.

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

The script is a simple library of functions, held together with some glue in 
main(). For locations other than Fort Worth / DFW, the end-user will need to
change three abbreviations in the code: one for the 
[weather forecast office](https://en.wikipedia.org/wiki/List_of_National_Weather_Service_Weather_Forecast_Office), 
one for the 
[radar station](https://radar.weather.gov/)
, and one for the
[local conditions station abbreviation](https://w1.weather.gov/xml/current_obs/).


```python
RADAR_STATION = 'FWS'
NWS_ABBR = 'FWD'
STATION = 'KDTO'
```

### Basic program flow:

#### Python
- Check for some required background images and gets them if needed.
- Retrieve current conditions
- Get the radar image
- Get the warnings image ("boxes" for overlaying)
- Get the Hazardous Weather Outlook and parse it
- Write out files to `/tmp/`

#### bash
- Run the python script
- Check for an overlay graphic (used in compositing the radar image)
- Clean up the last observations
- Use ImageMagick to composite the current radar image and backgrounds

## Limitations

The [National Weather Service API](https://www.weather.gov/documentation/services-web-api)
currently lists only one endpoint as valid, the `https://api.weather.gov/alerts` endpoint. 
As of this writing, the "current observations" also works, though I do not know if the coverage is universal.

At present, getting *forecast* information would have to come from 
[Dark Sky's API](https://darksky.net/dev/docs/faq) 
or some similar service.

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



### That other Geeklet

In case you're curious (one person was) about the "Time Zones" geeklet seen in the desktop screencap, the bash command is this:

```bash
echo "Mtn View:   $(env TZ=America/Los_Angeles date +'%l:%M %p %A')";echo "Dallas:     $(env TZ=America/Chicago date +'%l:%M %p %A')";echo "Boston:     $(env TZ=America/New_York date +'%l:%M %p %A')";echo "London:     $(env TZ=Europe/London date +'%l:%M %p %A')";echo "Amsterdam:  $(env TZ=Europe/Amsterdam date +'%l:%M %p %A')";echo "Banglalore: $(env TZ=Asia/Kolkata date +'%l:%M %p %A')"
```
