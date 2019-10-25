#!/bin/bash
$(which python) ${HOME}/Dropbox/bin/current_conditions.py

for file in bkg2
do
  if [[ -f "/tmp/${file}.gif" ]]; then
    # echo "${file}.gif is already there."
    sleep 1
  else
    cp ${HOME}/Dropbox/${file}.gif /tmp/
  fi
done

for file in wow weather 
do
  if [[ -f "/tmp/${file}.gif" ]]; then
    # echo "Removing /tmp/${file}.gif"
    rm /tmp/${file}.gif
  fi
done

convert -composite /tmp/current_image.gif   /tmp/current_warnings.gif  /tmp/weather.gif
convert -composite /tmp/weather.gif   /tmp/bkg2.gif  /tmp/wow.gif
