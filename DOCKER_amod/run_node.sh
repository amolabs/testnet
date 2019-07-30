if [ -z "$AMOHOME" ]; then
	AMOHOME=/amo
fi
if [ -z "$TMHOME" ]; then
	TMHOME=/tendermint
fi

/usr/bin/tendermint --home $TMHOME init

/usr/bin/amod run &
/usr/bin/tendermint --home $TMHOME node

