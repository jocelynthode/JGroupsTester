#!/usr/bin/env bash
# This script needs to run in the container
MY_IP_ADDR=$(/bin/hostname -I)

echo 'Starting jgroup peer'
echo "${MY_IP_ADDR}"
echo "${PEER_NUMBER}"
echo "${FILENAME}"
MY_IP_ADDR=($MY_IP_ADDR)
echo "${MY_IP_ADDR[0]}"
exec java -Xms100m -Xmx210m -Djgroups.bind_addr="${MY_IP_ADDR[0]}" -Djava.net.preferIPv4Stack=true \
 -cp ./jgroups-tester-1.0-SNAPSHOT-all.jar EventTesterKt "$PEER_NUMBER" > "/data/${MY_IP_ADDR[0]}_${FILENAME}.txt" 2>&1