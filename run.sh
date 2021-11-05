#!/bin/bash

DOCKER=false
IMAGE_VERSION=latest
PUBLISH="-p 26657"
TTY="-it"
LOG=""

usage() {
	echo "syntax: $0 [options] <data_root>"
	echo "options:"
	echo "  -d  use docker with specified image version"
	echo "  -p  publish ports 26656,26657,26660"
	echo "  -s  keep silent, i.e. do not attach stdio"
	echo "  -h  print usage"
}

while getopts "d:psh" arg; do
	case $arg in
		d)
			DOCKER=true
			IMAGE_VERSION=$OPTARG
			;;
		p)
			PUBLISH="-p 26656:26656 -p 26657:26657 -p 26660:26660"
			;;
		s)
			TTY="-d"
			;;
		l)
			LOG="--log-driver=journald"
			;;
		h | *)
			usage
			exit
			;;
	esac
done

shift $(( OPTIND - 1 ))

DATAROOT=$1
if [ -z "$DATAROOT" ]; then
	usage
	exit
fi

echo "data root     = $DATAROOT"

if [ "$DOCKER" = true ]; then
	echo "docker image  = $IMAGE_VERSION"
	docker stop amod -t 5
	docker rm amod
	docker run $TTY $LOG --restart unless-stopped --name amod $PUBLISH -v $DATAROOT/amo:/amo amolabs/amod:$IMAGE_VERSION amod run --home /amo
else
	amod run --home $DATAROOT/amo
fi
