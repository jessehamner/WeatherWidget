#!/bin/bash
python_binary="$(/usr/bin/which python | tr '\n' ' ' | sed 's/ //g')"
# echo "python: ${python_binary}"
# python_version="$(${python_binary} --version)"
${python_binary} ${HOME}/Dropbox/weatherwidget/current_conditions.py
convert_binary=`source ${HOME}/.bash_profile; /usr/bin/which convert`
# echo "-convert- binary: ${convert_binary}"
legendfile=""
dir="/tmp"
date_binary=$(/usr/bin/which date)
echo "Date binary: ${date_binary}"

function parse_return {
  rrr=$(echo $1 | tr '\n' ' ' | sed 's/ $//g')
  r2=$(echo ${rrr} | grep -e "corrupt image" -e "improper image header" -e "no images defined" -e "unable to open image")
  if [[ "${r2}" != "" ]]; then
    echo "Error! image is corrupted?"
    exit
  fi
  return 0
}

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

if [[ -f "${dir}/trim_legend.gif" ]]; then
  # echo "Found trim_legend.gif file -- looks good."
  sleep 0.1
  else
    legendfile=$(ls -1 ${dir}/ | grep -e "N0R_Legend" -i | tr '\n' ' ' | sed  's/ //g')

    if [[ -f "${dir}/${legendfile}" ]]; then
      echo "No trim_legend.gif file found, but can convert ${legendfile}..."
      echo "Converting legend to crop1.gif:"
      # echo "convert FWS_N0R_Legend_0.gif -crop 0x0+0+25 crop1.gif"
      ${convert_binary} "${dir}/${legendfile}" -crop 0x0+0+25 ${dir}/crop1.gif
      ${convert_binary} "${dir}/crop1.gif" -background none -splice 0x25  ${dir}/trim_legend.gif
  else 
    echo "Unable to process legend file. Skipping it."
  fi
fi

for file in weather wow-test
do
  if [[ -f "${dir}/${file}.gif" ]]; then
    # echo "Removing ${dir}/${file}.gif"
    rm ${dir}/${file}.gif
  fi
done

# Get the MD5 hash of the backup image (no time stamp):
sha0=$(shasum ${dir}/wow_00.gif | awk {'print $1'} | tr '\n' ' ' | sed 's/ $//g')

# Strip the transparency and add a black background to the radar image:
result=$(${convert_binary} ${dir}/current_image.gif -background black -alpha remove ${dir}/current_image.gif)
# echo "returned text from convert is: ${result}"
parse_return "${result}"
result=""

result=$(${convert_binary} -composite ${dir}/current_image.gif  ${dir}/current_warnings.gif ${dir}/weather.gif)
# echo "returned text from convert is: ${result}"
parse_return "${result}"
result=""

result=$(${convert_binary} -composite ${dir}/weather.gif ${dir}/bkg2.gif  ${dir}/wow-test.gif)
# echo "returned text from convert is: ${result}"
parse_return "${result}"
result=""

result=$(${convert_binary} -composite ${dir}/wow-test.gif ${dir}/trim_legend.gif ${dir}/wow.gif)
# echo "returned text from convert is: ${result}"
parse_return "${result}"

# Copy the potentially new image (no time stamp) to a backup image:
cp ${dir}/wow.gif ${dir}/wow_00.gif


# Make an MD5 hash of the potentially new image:
sha1=$(shasum ${dir}/wow.gif | awk {'print $1'} | tr '\n' ' ' | sed 's/ $//g')

# Timestamp the image with the system time:
${convert_binary} -font Courier -pointsize 18 -strokewidth 0.5 -stroke white \
  -draw "fill white text 530,50 '$(${date_binary} +%H:%M)'" ${dir}/wow.gif ${dir}/wow.gif

# Check the two hashes against each other (backup to possibly-new):
if [[ "${sha0}" == "${sha1}" ]]; then
  echo "Radar image has not changed."
  exit
fi

# Copy the new time-stamped image to frame 0:
cp ${dir}/wow.gif ${dir}/wow_0.gif

# Make an animated GIF from the timestamped images.
imagecount=20
animate=" -delay 100 -dispose Background "
for i in $(seq ${imagecount} -1 0)
  do
    sum=`expr ${i} - 1`
    if [[ -f "${dir}/wow_${sum}.gif" ]]; then
      # echo "Converting image from ${sum} to ${i}"
      mv ${dir}/wow_${sum}.gif ${dir}/wow_${i}.gif
      animate="${animate} ${dir}/wow_${i}.gif"
    fi
  done
animate="${animate} -loop 0 ${dir}/animation.gif"

# echo "animate command: ${convert_binary} ${animate}"
${convert_binary} ${animate}

