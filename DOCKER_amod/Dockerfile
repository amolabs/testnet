# vim: set expandtab:
FROM alpine:3.7

ENV AMOHOME /amo
ENV TMHOME /tendermint
ENV MONIKER amo

#RUN addgroup amo && adduser -S -G amo amo -h "$AMOHOME"
#USER amo

VOLUME [ $AMOHOME ]
VOLUME [ $TMHOME ]

COPY tendermint amod /usr/bin/
COPY run_node.sh ./

WORKDIR $AMOHOME

EXPOSE 26656 26657

CMD ["/bin/sh", "/run_node.sh"]

