#!/usr/bin/env bash
# This script needs to run in the container


cd /code/scripts

MY_IP_ADDR=$(/bin/hostname -i)
TMP=$(dig -x $MY_IP_ADDR +short)
MY_NAME=(${TMP//./ })

# wait for all peers
sleep 2m

echo 'Starting jgroup peer'
exec java -Xms50m -Xmx100m -cp ../build/libs/jgroups-tester-1.0-SNAPSHOT-all.jar EventTesterKt > localhost.txt 2>&1
