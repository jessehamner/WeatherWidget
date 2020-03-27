#!/bin/bash

# Quick and dirty script to animate downloaded jpgs into a nice animated m4v
# If you want to specify other than all GOES images following the default pattern,
# you can specify a pattern with $1 --
# ./animate_goes.sh "2020087*_GOES16-ABI-sp-GEOCOLOR-2400x2400.jpg"

glob=$1
[ "$glob" == "" ] && glob="2020*_GOES16-ABI-sp-GEOCOLOR-2400x2400.jpg" 
outputfile="out2.mp4"
pathdir="/tmp"

$(/usr/bin/which -s ffmpeg) || echo 'No ffmpeg found!'
$(/usr/bin/which -s ffmpeg) || exit
ffmpeg_executable="$(/usr/bin/which ffmpeg)"
# echo "ffmpeg executable: ${ffmpeg_executable}"
${ffmpeg_executable} -r 5 -pattern_type glob -i "${pathdir}/${glob}" -c:v libx264 "${pathdir}/${outputfile}"
echo "Done."
