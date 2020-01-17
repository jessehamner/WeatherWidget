#!/bin/bash
$(/usr/bin/which python) ${HOME}/Dropbox/weatherwidget/current_conditions.py
convert_binary=`source ${HOME}/.bash_profile; /usr/bin/which convert`
dir="/tmp"
echo""
echo "$(date)"
# echo "-convert- binary: ${convert_binary}"
if [ "${convert_binary}" == "convert not found" ]; then
  echo "Error! -convert- command not found."
  exit
fi

if [ "${convert_binary}" == "" ]; then
  echo "Error! -convert- command not found -- missing binary?"
  exit
fi

for file in bkg2
do
  if [[ -f "${dir}/${file}.gif" ]]; then
    sleep 1
  else
    echo "${file}.gif is not present in ${dir}. Copying it in."
    cp ${HOME}/Dropbox/weatherwidget/images/${file}.gif ${dir}/
  fi
done

for file in weather 
do
  if [[ -f "${dir}/${file}.gif" ]]; then
    # echo "Removing ${dir}/${file}.gif"
    rm ${dir}/${file}.gif
  fi
done

# Get the MD5 hash of the backup image (no time stamp):
sha0=$(shasum /tmp/wow_00.gif | awk {'print $1'} | tr '\n' ' ' | sed 's/ $//g')
${convert_binary} -composite ${dir}/current_image.gif   ${dir}/current_warnings.gif  ${dir}/weather.gif
${convert_binary} -composite ${dir}/weather.gif   ${dir}/bkg2.gif  ${dir}/wow.gif

# Copy the potentially new image (no time stamp) to a backup image:
cp ${dir}/wow.gif ${dir}/wow_00.gif

# Make an MD5 hash of the potentially new image:
sha1=$(shasum /tmp/wow.gif | awk {'print $1'} | tr '\n' ' ' | sed 's/ $//g')

# Check the two hashes against each other (backup to possibly-new):
if [[ "${sha0}" == "${sha1}" ]]; then
  echo "Radar image has not changed."
  exit
fi

# Keep a clean copy for comparison next time
# cp ${dir}/wow.gif ${dir}/wow_00.gif

# Timestamp the image with the system time:
${convert_binary} -font Courier -pointsize 18 -strokewidth 0.5 -stroke white \
  -draw "fill white text 530,50 '$(date +%H:%M)'" ${dir}/wow.gif ${dir}/wow.gif

# Copy the new time-stamped image to frame 0:
cp ${dir}/wow.gif ${dir}/wow_0.gif

# Make an animated GIF from the timestamped images.
imagecount=20
animate=" -delay 100 -dispose Background "
for i in $(seq ${imagecount} -1 0)
  do
    sum=`expr ${i} - 1`
    if [[ -f "${dir}/wow_${sum}.gif" ]]; then
      echo "Converting image from ${sum} to ${i}"
      mv ${dir}/wow_${sum}.gif ${dir}/wow_${i}.gif
      animate="${animate} ${dir}/wow_${i}.gif"
    fi
  done
animate="${animate} -loop 0 ${dir}/animation.gif"

# echo "animate command: ${convert_binary} ${animate}"
${convert_binary} ${animate}

