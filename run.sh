#!/bin/bash
cd `dirname $0`
source .venv/bin/activate

opt=$1
if [ "$opt" = "--no-view" ]; then
    python run.py $opt
else
    python run.py
fi
