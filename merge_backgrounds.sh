#!/bin/sh

dir="/tmp"
radar="FWS"

highways="${dir}/${radar}_Highways_Short.gif"
rangering="${dir}/${radar}_RangeRing_Short.gif"
cities="${dir}/${radar}_City_1M_Short.gif"
smallcities="${dir}/${radar}_City_250K_Short.gif"
counties="${dir}/${radar}_County_Short.gif"

echo "Checking for files in ${dir} directory..."
for file in ${highways} ${rangering} ${cities} ${smallcities} ${counties}
do
  if [[ -f "${file}" ]]; then
    sleep 0.5
  else
    echo "Unable to find ${file}! Exiting early."
    exit
  fi
done

convert -composite "${highways}" "${rangering}" "${dir}/result1.gif"
convert -composite  "${dir}/result1.gif" "${cities}" "${dir}/bkg1.gif"
convert -composite  "${dir}/bkg1.gif" "${counties}" "${dir}/bkg2.gif"

echo "Done!"
# <EOF>
