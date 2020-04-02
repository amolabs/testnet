#!/bin/bash

# AMO helper (for protocol upgrade)
# roles:
#   - watch node's heartbeat
#   - if node is dead, revive it (systemctl job)
#   - if protocol gets upgraded, change binary and revive it
#
# protocol upgrade detection:
# - state <- load $DATAROOT/amo/data/state.json
# - config <- query config from node
# - replace binary, if state.Height != state.LastHeight && config.UpgradeProtocolHeight == state.Height
#
# binary replacement:
# - release <- curl https://api.github.com/repos/amolabs/amoabci/releases/latest
# - wget relase.download_url -O release.name
# - tar -xzf latest.assets[0].name
# - cp -f amod $(which amod)
#
# overall flow:
# - check
# - prepare
# - standby
# - upgrade

# default
NAME='AMO helper'
PY='python3'
MODE='normal'
INTERVAL=1 # sleep interval
PROGRESS_BAR_SIZE=60

usage() {
    echo "syntax: $0 [options] <data_root>"
    echo "options:"
    echo "  -f  force upgrade"
    echo "  -h  print usage"
}

while getopts "fh" arg; do
    case $arg in
        f)
        	MODE='force'
        	;;
        h | *)
        	usage
        	exit
        	;;
    esac
done

shift $(( OPTIND - 1))

print_h() {
    echo "[$NAME] $1"
}

fail() {
    print_h "upgrade failed"
    exit -1
}

read_json() {
    data=$1
    target=$2
    result=$(echo $data | $PY -c "import sys, json; print(json.load(sys.stdin)$target)")
    if [ $? -ne 0 ]; then fail; fi
    echo $result
}

hide_cursor() {
    echo -n `tput civis`
}
 
show_cursor() {
    echo -n `tput cvvis`
}

progress_bar() {
    begin=$1
    end=$2
    current=$3
    current_pos=$(((current-begin)*PROGRESS_BAR_SIZE/(end-begin)))

    echo -en "\r[$NAME] ["
    for (( i = 0; i < PROGRESS_BAR_SIZE; i++ )); do
        if [[ i -le current_pos ]]; then
            echo -n "#"
            continue
        fi
        printf "."
    done 
    echo -n "] $begin >> $current >> $end"
}

check() {
    print_h "check if protocol needs to get upgraded"

    height=$1
    upgrade_protocol_height=$2

    # pre-condition
    if [[ $height -gt $upgrade_protocol_height ]]; then
        print_h "no need to upgrade protocol"
        exit 0
    fi
}

prepare() {
    print_h "prepare necessary things to upgrade protocol"

    print_h "  get latest release info"
    release=$(curl -s https://api.github.com/repos/amolabs/amoabci/releases/latest | sed 's/\\r\\n//')
    if [ $? -ne 0 ]; then fail; fi
    asset_url=$(read_json "$release" "['assets'][0]['browser_download_url']")
    asset_name=$(read_json "$release" "['assets'][0]['name']")
    
    print_h "  download latest release: $asset_name"
    out=$(wget -q $asset_url -O $asset_name)
    if [ $? -ne 0 ]; then fail; fi
    
    print_h "  untar latest release: $asset_name"
    out=$(tar -xzf $asset_name)
    if [ $? -ne 0 ]; then fail; fi
}

standby() {
    print_h "wait for height to reach upgrade protocol height"

    height=$1
    last_height=$2
    upgrade_protocol_height=$3

    hide_cursor
    begin=$height
    end=$upgrade_protocol_height
    # wait until upgrade protocol condition matches
    while [[ $height -eq $last_height || $height -ne $upgrade_protocol_height ]]; do
        progress_bar "$begin" "$end" "$height"
        
        state=$(cat $DATAROOT/amo/data/state.json)
        height=$(read_json "$state" "['height']")
        last_height=$(read_json "$state" "['last_height']")

        sleep $INTERVAL
    done
    show_cursor
    echo
}

upgrade() {
    print_h "execute protocol upgrade"

    print_h "  copy latest amod"
    out=$(sudo cp -f amod $(which amod))
    if [ $? -ne 0 ]; then fail; fi

    print_h "  restart amod service"
    out=$(sudo systemctl restart amod)
    if [ $? -ne 0 ]; then fail; fi

    print_h "successfully upgraded protocol"
}

DATAROOT=$1
if [ -z "$DATAROOT"  ]; then
    usage
    exit
fi

print_h "dataroot=$DATAROOT"

case $MODE in
    'normal')
        # load upgrade_protocol_height from node config
        query='{"jsonrpc": "2.0", "id": 0, "method": "abci_query", "params": {"path": "/config", "data": "6e756c6c"}}'
        config=$(curl -s -H "Content-Type: application/json" -X POST -d "$query" localhost:26657)
        if [ $? -ne 0 ]; then fail; fi
        config=$(read_json "$config" "['result']['response']['value']" | base64 --decode)
        upgrade_protocol_height=$(read_json "$config" "['upgrade_protocol_height']")
         
        # load height and last_height from $DATAROOT/amo/data/state.json
        state=$(cat $DATAROOT/amo/data/state.json)
        height=$(read_json "$state" "['height']")
        last_height=$(read_json "$state" "['last_height']")

        check "$height" "$upgrade_protocol_height"
        prepare
        standby "$height" "$last_height" "$upgrade_protocol_height"
        upgrade
        ;;
    'force')
        prepare
        upgrade
        ;;
esac

