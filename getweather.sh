#!/bin/bash
python_binary="$(/usr/bin/which python | tr '\n' ' ' | sed 's/ //g')"
# echo "python: ${python_binary}"
# python_version="$(${python_binary} --version)"
sourcelib="${HOME}/Dropbox/weatherwidget"
${python_binary} ${sourcelib}/current_conditions.py
convert_binary=`source ${HOME}/.bash_profile; /usr/bin/which convert`
# echo "-convert- binary: ${convert_binary}"
legendfile=""
dir="/tmp"
date_binary=$(/usr/bin/which date)
# echo "Date binary: ${date_binary}"
# echo "Path: ${_}"


function parse_return {
  rrr=$(echo $1 | tr '\n' ' ' | sed 's/ $//g')
  r2=$(echo ${rrr} | grep -e "corrupt image" -e "improper image header" -e "no images defined" -e "unable to open image")
  [ "${r2}" != "" ] && echo "Error! image is corrupted?" && exit 1
  return 0
}

/usr/bin/which convert | grep "convert not found" && exit
# echo "Found Imagemagick binary. Moving forward."
convert_binary=`source ${HOME}/.bash_profile; /usr/bin/which convert`

for file in bkg2
do
  [ -s "${dir}/${file}.gif" ] || echo "${file}.gif is not present in ${dir}. Copying it in." && \
    cp ${sourcelib}/images/${file}.gif ${dir}/
done

if [[ -s "${dir}/trim_legend.gif" ]]; then
  # echo "Found trim_legend.gif file -- looks good."
  sleep 0.1
  else
    legendfile=$(ls -1 ${dir}/ | grep -e "N0R_Legend" -i | tr '\n' ' ' | sed  's/ //g')

    if [[ -s "${dir}/${legendfile}" ]]; then
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
  [ -s "${dir}/${file}.gif" ] && rm ${dir}/${file}.gif
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
[ "${sha0}" == "${sha1}" ] && echo "Radar image has not changed." && exit

# Copy the new time-stamped image to frame 0:
cp ${dir}/wow.gif ${dir}/wow_0.gif

# Make an animated GIF from the timestamped images.
imagecount=20
animate=" -delay 100 -dispose Background "
for i in $(seq ${imagecount} -1 0)
  do
    sum=`expr ${i} - 1`
    if [[ -s "${dir}/wow_${sum}.gif" ]]; then
      # echo "Converting image from ${sum} to ${i}"
      mv ${dir}/wow_${sum}.gif ${dir}/wow_${i}.gif
      animate="${animate} ${dir}/wow_${i}.gif"
    fi
  done
animate="${animate} -loop 0 ${dir}/animation.gif"

# echo "animate command: ${convert_binary} ${animate}"
${convert_binary} ${animate}

