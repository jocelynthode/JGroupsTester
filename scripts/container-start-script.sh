#!/usr/bin/env bash
# This script needs to run in the container

addtime() {
    while IFS= read -r line; do
        echo "$(date +%s%N | cut -b1-13) $line"
    done
}

MY_IP_ADDR=$(/bin/hostname -i)

# wait for all peers
sleep 20s
echo 'Starting jgroup peer'
echo "${MY_IP_ADDR}"
echo "${PEER_NUMBER}"
MY_IP_ADDR=($MY_IP_ADDR)
echo "${MY_IP_ADDR[0]}"
exec java -Xms150m -Xmx330m -Djgroups.bind_addr="${MY_IP_ADDR[0]}" -Djava.net.preferIPv4Stack=true \
 -cp ./jgroups-tester-1.0-SNAPSHOT-all.jar EventTesterKt > "/data/${MY_IP_ADDR[0]}.txt" 2>&1
ls