.PHONY: webserver
PROJECT := pyaptly

export HOME := $(shell pwd)
export PATH := $(HOME)/aptly_0.9.6_linux_amd64/:$(PATH)

include pyproject/Makefile

local-test: webserver test

.gnupg:
	bash -c '[[ "$$HOME" == *"pyaptly.src"* ]]'
	gpg --import < vagrant/key.pub
	gpg --import < vagrant/key.sec
	gpg --batch --no-default-keyring --keyring trustedkeys.gpg --import < vagrant/key.pub

.aptly:
	aptly repo create -architectures="amd64" fakerepo01
	aptly repo create -architectures="amd64" fakerepo02
	aptly repo add fakerepo01 vagrant/*.deb
	aptly repo add fakerepo02 vagrant/*.deb

.aptly/public: .aptly .gnupg
	aptly publish repo -gpg-key="650FE755" -distribution="main" fakerepo01 fakerepo01; true
	aptly publish repo -gpg-key="650FE755" -distribution="main" fakerepo02 fakerepo02; true
	touch .aptly/public

webserver: .aptly/public
	pkill -f -x "python -m SimpleHTTPServer 8421"; true
	pkill -f -x "python -m http.server 8421"; true
	cd .aptly/public && python -m SimpleHTTPServer 8421 > /dev/null 2> /dev/null &
	cd .aptly/public && python -m http.server 8421 > /dev/null 2> /dev/null &

remote-test:
	vagrant up
	vagrant ssh -c "cd /vagrant && make test"
