#!/bin/bash

#export SCRAM_ARCH=slc7_amd64_gcc700

mkdir -p /data/CRABTesting/
cd /data/CRABTesting/

git clone https://github.com/dmwm/CRABClient
git clone https://github.com/dmwm/CRABServer

cp CRABServer/src/python/ServerUtilities.py CRABClient/src/python/
cp CRABServer/src/python/RESTInteractions.py CRABClient/src/python/

git clone https://github.com/dmwm/WMCore
cd WMCore; git checkout 1.3.3; cd ..

git clone https://github.com/dmwm/DBS
cd DBS; git checkout 3.10.0; cd ..

set +x

