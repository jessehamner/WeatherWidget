#!/bin/bash

dir="/tmp"
radar="FWS"

/usr/bin/which convert | grep "convert not found" && exit 1
echo "Found Imagemagick binary. Moving forward."
convert_binary=$(/usr/bin/which convert)

highways="${dir}/${radar}_Highways_Short.gif"
rangering="${dir}/${radar}_RangeRing_Short.gif"
cities="${dir}/${radar}_City_1M_Short.gif"
smallcities="${dir}/${radar}_City_250K_Short.gif"
counties="${dir}/${radar}_County_Short.gif"

echo "Checking for files in ${dir} directory..."
for file in ${highways} ${rangering} ${cities} ${smallcities} ${counties}
do
  [ -s "${file}" ] || echo "Unable to find ${file}! Exiting early." && exit 1
done

${convert_binary} -composite "${highways}" "${rangering}" "${dir}/result1.gif"
${convert_binary} -composite  "${dir}/result1.gif" "${cities}" "${dir}/bkg1.gif"
${convert_binary} -composite  "${dir}/bkg1.gif" "${counties}" "${dir}/bkg2.gif"

echo "Done!"
# <EOF>
