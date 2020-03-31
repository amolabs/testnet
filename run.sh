#!/bin/bash

usage() {
	echo "syntax: $0 [options] <data_root>"
	echo "options:"
	echo "  -h  print usage"
}

while getopts "h" arg; do
	case $arg in
		h | *)
			usage
			exit
			;;
	esac
done

DATAROOT=$1
if [ -z "$DATAROOT" ]; then
	usage
	exit
fi

echo "data root 	= $DATAROOT"

/usr/bin/amod run --home $DATAROOT 
