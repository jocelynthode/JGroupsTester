#!/usr/bin/env bash
# This script needs to run in the container
MY_IP_ADDR=$(/bin/hostname -I)

echo 'Starting jgroup peer'
echo "${MY_IP_ADDR}"
echo "${PEER_NUMBER}"
echo "$PROTOCOL_STACK"
echo "$TIME"
MY_IP_ADDR=($MY_IP_ADDR)
echo "${MY_IP_ADDR[0]}"

dstat -n -N eth0 --output "/data/capture/${MY_IP_ADDR[0]}.csv" &
dstat_pid=$!
exec java -Xms100m -Xmx210m -Djgroups.bind_addr="${MY_IP_ADDR[0]}" -Djava.net.preferIPv4Stack=true \
-Djgroups.tcpping.initial_hosts="172.110.0.3[7800],172.110.0.4[7800],172.110.0.5[7800],172.110.0.6[7800],172.110.0.7[7800]" \
-cp ./jgroups-tester-1.0-SNAPSHOT-all.jar -Dlogfile.name="${MY_IP_ADDR[0]}" EventTesterKt "$PEER_NUMBER" \
"$(cat /host_etc/hostname).xml"  "$TIME"
kill ${dstat_pid}
