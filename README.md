
# Weather Widget

A small set of python and bash utilities to retrieve radar images and the 
text of the Hazardous Weather Outlook for a given region from the 
US National Weather Service. On Mac OS X, these scripts integrate nicely with
[GeekTool](https://www.tynsoe.org/v2/geektool/) 
desktop widgets.

![alt text](https://github.com/jessehamner/weatherwidget/raw/master/src/common/images/desktop.png "GeekTool desktop widgets showing radar image and hazardous weather outlook information")

## Prerequisites

Python, bash (no idea if this works on the Windows 10 bash interpreter),
and ImageMagick. This codebase is generally intended for Mac OS X and Linux,
but obviously there are Windows versions of all of this software, but I don't
regularly use Windows.

## Quick Start

- Change three variables in the Python script
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
