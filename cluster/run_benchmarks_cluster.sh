#!/usr/bin/env bash
# This scripts runs the benchmarks on a remote cluster

MANAGER_IP=172.16.2.98
PEER_NUMBER=$1

if [ -z "$PEER_NUMBER" ]
  then
    echo "you have to indicate number of peers"
    exit
fi

function getlogs {
    while read ip; do
        rsync --remove-source-files -av "${ip}:~/data/*.txt" ../data/
    done <hosts
}

echo "START..."

# Clean everything at Ctrl+C
trap 'exit' TERM INT

echo "Pulling images"
docker pull swarm-m:5000/jgroups:latest
parallel-ssh -t 0 -h hosts "docker pull swarm-m:5000/jgroups:latest"

echo "Starting images"
# 100 nodes across 12 vms
parallel-ssh -t 0 -h hosts "for i in {1..8}; do docker run --network host -d --env \"FILENAME=\${i}\" \
 --env \"PEER_NUMBER=$PEER_NUMBER\" -v /home/debian/data:/data swarm-m:5000/jgroups; done"
for i in {1..12}; do docker run --network host -d --env "FILENAME=${i}" \
--env "PEER_NUMBER=$PEER_NUMBER" -v /home/debian/data:/data swarm-m:5000/jgroups; done


#while read ip; do
#    rsync -rv ${ip}:~/data/ ../data/
#done <hosts

#docker rm -f $(docker ps -f ancestor=swarm-m:5000/jgroups -q)
#parallel-ssh -t 0 -h hosts "docker rm -f \$(docker ps -f ancestor=swarm-m:5000/jgroups -q)"
