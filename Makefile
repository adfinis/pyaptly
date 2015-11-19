PROJECT := pyaptly

include pyproject/Makefile

remote-test:
	vagrant up
	vagrant ssh -c "cd /vagrant && make test"
