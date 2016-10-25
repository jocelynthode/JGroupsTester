#!/usr/bin/env bash
# This scripts runs the benchmarks on a remote cluster
MANAGER_IP=172.16.2.119
PEER_NUMBER=$1
TIME_ADD=$2

if [ -z "$PEER_NUMBER" ]
  then
    echo "you have to indicate number of peers"
    exit
fi

if [ -z "$TIME_ADD" ]
  then
    echo "you have to indicate by how much you want to delay JGroups start"
    exit
fi

function getlogs {
    while read ip; do
        rsync --remove-source-files -av "${ip}:~/data/" ../data/
    done <hosts
}

echo "START..."

# Clean everything at Ctrl+C
trap 'docker service rm jgroups-service;  getlogs;  exit' TERM INT

docker pull swarm-m:5000/jgroups:latest

docker swarm init && \
(TOKEN=$(docker swarm join-token -q worker) && \
parallel-ssh -t 0 -h hosts "docker swarm join --token ${TOKEN} ${MANAGER_IP}:2377" && \
docker network create -d overlay --subnet=172.110.0.0/16 jgroups_network || exit)

TIME=$(( $(date +%s%3N) + $TIME_ADD ))
docker service create --name jgroups-service --network jgroups_network --replicas ${PEER_NUMBER} \
--env "PEER_NUMBER=${PEER_NUMBER}" --env "TIME=$TIME" \
--limit-memory 250m --log-driver=journald --restart-condition=none \
--mount type=bind,source=/home/debian/data,target=/data \
--mount type=bind,source=/etc,target=/host_etc swarm-m:5000/jgroups:latest

# wait for service to start
while docker service ls | grep " 0/$PEER_NUMBER"
do
    sleep 1s
done
echo "Running JGroups tester..."
# wait for service to end
until docker service ls | grep -q " 0/$PEER_NUMBER"
do
    sleep 5s
done

#docker service rm jgroups-service

echo "Services removed"
getlogs
