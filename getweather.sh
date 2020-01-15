#!/bin/bash
$(/usr/bin/which python) ${HOME}/Dropbox/weatherwidget/current_conditions.py
convert_binary=`source ${HOME}/.bash_profile; /usr/bin/which convert`
dir="/tmp"
echo""
echo "$(date)"
echo "-convert- binary: ${convert_binary}"
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
    echo "${file}.gif is already present in ${dir}."
    sleep 1
  else
    cp ${HOME}/Dropbox/weatherwidget/images/${file}.gif ${dir}/
  fi
done

for file in wow weather 
do
  if [[ -f "${dir}/${file}.gif" ]]; then
    echo "Removing ${dir}/${file}.gif"
    rm ${dir}/${file}.gif
  fi
done

${convert_binary} -composite ${dir}/current_image.gif   ${dir}/current_warnings.gif  ${dir}/weather.gif
${convert_binary} -composite ${dir}/weather.gif   ${dir}/bkg2.gif  ${dir}/wow.gif
