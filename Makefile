.PHONY: save load

TMPATH=$(GOPATH)/src/github.com/tendermint/tendermint
AMOPATH=$(GOPATH)/src/github.com/amolabs/amoabci

all: amo-node

tendermint:
	-git clone https://github.com/tendermint/tendermint $(TMPATH)
	cd $(TMPATH); git checkout v0.29.2
	make -C $(TMPATH) get_tools
	make -C $(TMPATH) get_vendor_deps
	make -C $(TMPATH) build-linux
	cp $(TMPATH)/build/tendermint ./

amod:
	-git clone https://github.com/amolabs/amoabci $(AMOPATH)
	cd $(AMOPATH); git checkout v1.0-alpha1
	make -C $(AMOPATH) get_tools
	make -C $(AMOPATH) get_vendor_deps
	make -C $(AMOPATH) TARGET=linux build
	cp $(AMOPATH)/amod ./

amo-node: tendermint amod
	cp -f tendermint amod DOCKER_amod/
	docker build -t amolabs/amod DOCKER_amod

save: amo-node
	docker image save amolabs/amod | gzip > amod.tgz

load: amod.tgz
	zcat amod.tgz | docker image load
