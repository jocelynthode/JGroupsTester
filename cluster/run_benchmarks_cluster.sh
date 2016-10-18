#!/usr/bin/env bash
# This scripts runs the benchmarks on a remote cluster
MANAGER_IP=172.16.2.119
PEER_NUMBER=$1

if [ -z "$PEER_NUMBER" ]
  then
    echo "you have to indicate number of peers"
    exit
fi

function getlogs {
    while read ip; do
        rsync --remove-source-files -av "${ip}:~/data/" ../data/
    done <hosts
}

echo "START..."

# Clean everything at Ctrl+C
trap '(docker rm -f $(docker ps -aqf ancestor=swarm-m:5000/jgroups)&);\
parallel-ssh -t 0 -h hosts "docker rm -f \$(docker ps -aqf ancestor=swarm-m:5000/jgroups)"; getlogs;  exit' TERM INT

echo "Pulling images"
docker pull swarm-m:5000/jgroups:latest &
parallel-ssh -t 0 -h hosts "docker pull swarm-m:5000/jgroups:latest"

echo "Starting images"
# 100 nodes across 12 vms
for i in {1..12}; do docker run --network host -d --env "FILENAME=${i}" -m 250m \
--env "PEER_NUMBER=$PEER_NUMBER" -v /home/debian/data:/data swarm-m:5000/jgroups; done &
parallel-ssh -t 0 -h hosts "for i in {1..8}; do docker run --network host -d --env \"FILENAME=\${i}\" \
 --env \"PEER_NUMBER=$PEER_NUMBER\" -m 250m -v /home/debian/data:/data swarm-m:5000/jgroups; done"

sleep 2m
docker rm -f $(docker ps -aqf ancestor=swarm-m:5000/jgroups) &
parallel-ssh -t 0 -h hosts "docker rm -f \$(docker ps -aqf ancestor=swarm-m:5000/jgroups)"

getlogs
