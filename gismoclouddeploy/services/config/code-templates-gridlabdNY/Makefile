
DER_VALUE="10 kW"

MAKEFLAGS=-j1
SOURCES=$(wildcard feeder*/*.glm)
TARGETS=$(patsubst %.glm,%.csv,$(SOURCES))

all: $(TARGETS)

clean:
	rm -f hosting_capacity.csv gridlabd.log gridlabd.json feeder*/*.csv

%.csv: %.glm
	@echo "Processing $<..." | tee -a gridlabd.log
	@test ! -f hosting_capacity.csv && echo "feeder,der_value,node_count,link_count,load_count,runtime" > hosting_capacity.csv || true
	@gridlabd $< config.glm hosting_capacity.glm 1>>hosting_capacity.csv 2>>gridlabd.log && gridlabd $< config.glm hosting_capacity.glm 1>>hosting_capacity.csv 2>>gridlabd.log -D DER_VALUE=$(DER_VALUE) || true
