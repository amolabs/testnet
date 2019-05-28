.PHONY: save push load

TMPATH=$(GOPATH)/src/github.com/tendermint/tendermint
AMOPATH=$(GOPATH)/src/github.com/amolabs/amoabci

all: amod-iamge

tendermint:
	-git clone https://github.com/tendermint/tendermint $(TMPATH)
	cd $(TMPATH); git checkout v0.31.5
	make -C $(TMPATH) get_tools
	make -C $(TMPATH) get_vendor_deps
	make -C $(TMPATH) build-linux
	cp $(TMPATH)/build/tendermint ./

amod:
	-git clone https://github.com/amolabs/amoabci $(AMOPATH)
	cd $(AMOPATH); git checkout v1.0-alpha6
	make -C $(AMOPATH) get_tools
	make -C $(AMOPATH) get_vendor_deps
	make -C $(AMOPATH) TARGET=linux build
	cp $(AMOPATH)/amod ./

amod-iamge: tendermint amod
	cp -f tendermint amod DOCKER_amod/
	docker build -t amolabs/amod DOCKER_amod

save: amod-image
	docker image save amolabs/amod | gzip > amod.tgz
	docker image save paust-db | gzip > pdb.tgz

push: save
	scp amod.tgz pdb.tgz root@amo-tokyo:testnet/
	scp amod.tgz pdb.tgz root@amo-dallas:testnet/
	scp amod.tgz pdb.tgz root@amo-frank:testnet/

load:
	zcat amod.tgz | docker image load
	zcat pdb.tgz | docker image load

clean:
	rm -f tendermint amod *.tgz docker-compose.yml
