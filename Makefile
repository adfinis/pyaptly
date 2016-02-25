PROJECT := pyaptly

export HOME := $(shell pwd)
export PATH := $(HOME)/aptly_0.9.6_linux_amd64/:$(PATH)

include pyproject/Makefile

remote-test:
	vagrant up
	vagrant ssh -c "cd /vagrant && make test"
