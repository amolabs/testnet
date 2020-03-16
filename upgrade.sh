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
# - cp -f amod /usr/bin/amod

# default
NAME='AMO helper'
PY='python3'
INTERVAL=1 # sleep interval
PROCESS_BAR_SIZE=60

usage() {
    echo "syntax: $0 <data_root>"
}

print_h() {
    echo "[$NAME] $1"
}

fail() {
    print_h "upgrade failed: $1"
	exit -1
}

read_json() {
    data=$1
    target=$2
    result=$(echo $data | $PY -c "import sys, json; print(json.load(sys.stdin)$target)")
    if [ $? -ne 0 ]; then fail; fi
    echo $result
}

check_upgrade_protocol() {
    # load upgrade_protocol_height from node config
    query='{"jsonrpc": "2.0", "id": 0, "method": "abci_query", "params": {"path": "/config", "data": "6e756c6c"}}'
    config=$(curl -s -H "Content-Type: application/json" -X POST -d "$query" localhost:26657)
    if [ $? -ne 0 ]; then fail; fi
    config=$(read_json "$config" "['result']['response']['value']" | base64 -D)
    upgrade_protocol_height=$(read_json "$config" "['upgrade_protocol_height']")
    
    # load height and last_height from $DATAROOT/amo/data/state.json
    state=$(cat $DATAROOT/amo/data/state.json)
    height=$(read_json "$state" "['height']")
    last_height=$(read_json "$state" "['last_height']")

    # pre-condition
    if [[ $height -gt $upgrade_protocol_height ]]; then
        print_h "no need to upgrade protocol"
        exit 0
    fi

    # wait until upgrade protocol condition matches
    while [[ $height -eq $last_height || $height -ne $upgrade_protocol_height ]]; do
        print_h "height=$height, last_height=$last_height, upgrade_protocol_height=$upgrade_protocol_height"
        
        state=$(cat $DATAROOT/amo/data/state.json)
        height=$(read_json "$state" "['height']")
        last_height=$(read_json "$state" "['last_height']")

        sleep $INTERVAL
    done
}

DATAROOT=$1
if [ -z "$DATAROOT"  ]; then
    usage
    exit
fi

print_h "dataroot=$DATAROOT"

print_h "get latest release info"
release=$(curl -s https://api.github.com/repos/amolabs/amoabci/releases/latest | sed 's/\\r\\n//')
if [ $? -ne 0 ]; then fail; fi
asset_url=$(read_json "$release" "['assets'][0]['browser_download_url']")
asset_name=$(read_json "$release" "['assets'][0]['name']")

print_h "download latest release: $asset_name"
out=$(wget -q $asset_url -O $asset_name)
if [ $? -ne 0 ]; then fail; fi

print_h "untar latest release: $asset_name"
out=$(tar -xzf $asset_name)
if [ $? -ne 0 ]; then fail; fi

print_h "check if protocol needs to get upgraded"
check_upgrade_protocol

print_h "copy latest amod"
out=$(sudo cp -f amod /usr/bin/amod)
if [ $? -ne 0 ]; then fail; fi