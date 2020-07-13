#!/bin/bash

set -x
source /cvmfs/cms.cern.ch/cmsset_default.sh
export SCRAM_ARCH=slc6_amd64_gcc491
cd /data/CRABTesting/
cmsrel CMSSW_10_2_6
cd CMSSW_10_2_6/src
cmsenv

cd /data/CRABTesting/
GitDir=`pwd`

MY_DBS=${GitDir}/DBS/
MY_CRAB=${GitDir}/CRABClient
MY_WMCORE=${GitDir}/WMCore

export PYTHONPATH=${MY_DBS}/Client/src/python:${MY_DBS}/PycurlClient/src/python:$PYTHONPATH
export PYTHONPATH=${MY_WMCORE}/src/python:$PYTHONPATH
export PYTHONPATH=${MY_CRAB}/src/python:$PYTHONPATH

export PATH=${MY_CRAB}/bin:$PATH
source ${MY_CRAB}/etc/crab-bash-completion.sh

set +x
