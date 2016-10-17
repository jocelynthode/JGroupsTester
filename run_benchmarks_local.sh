#!/usr/bin/env bash
# This scripts runs the benchmarks on a remote cluster

MANAGER_IP=172.16.2.119
PEER_NUMBER=$1

if [ -z "$PEER_NUMBER" ]
  then
    echo "you have to indicate number of peers"
    exit
fi

echo "START..."
./gradlew docker

# Clean everything at Ctrl+C
trap 'docker rm -f $(docker ps -aqf ancestor=jgroups) && exit' TERM INT

for i in $(seq 1 $PEER_NUMBER); do docker run --network host -d --env "FILENAME=${i}" -m 250m \
--env "PEER_NUMBER=$PEER_NUMBER" -v /home/jocelyn/tmp/data:/data jgroups; done

echo "Running JGroups tester..."
sleep 1m

docker rm -f $(docker ps -aqf ancestor=jgroups)
echo "Done"



