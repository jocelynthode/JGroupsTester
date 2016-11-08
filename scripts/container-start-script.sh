#!/usr/bin/env bash
# This script needs to run in the container
MY_IP_ADDR=$(/bin/hostname -I)
TRACKER_IP=$(dig +short jgroups-tracker)
echo 'Starting jgroup peer'
echo "${MY_IP_ADDR}"
echo "${PEER_NUMBER}"
echo "$TIME"
MY_IP_ADDR=($MY_IP_ADDR)
echo "${MY_IP_ADDR[0]}"
echo "${TRACKER_IP}[12001]"
echo "${EVENTS_TO_SEND}"
echo "${RATE}"


dstat -n -N eth0 --output "/data/capture/${MY_IP_ADDR[0]}.csv" &
dstat_pid=$!
exec java -Xms100m -Xmx260m -Djgroups.bind_addr="${MY_IP_ADDR[0]}" \
-Djgroups.tunnel.gossip_router_hosts="${TRACKER_IP}[12001]" -Djava.net.preferIPv4Stack=true \
-cp ./jgroups-tester-1.0-SNAPSHOT-all.jar -Dlogfile.name="${MY_IP_ADDR[0]}" EventTesterKt --events "$EVENTS_TO_SEND" \
--rate "$RATE" --fixed-rate 50 "$PEER_NUMBER" "$TIME"
kill ${dstat_pid}
