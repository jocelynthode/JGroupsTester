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

echo "START..."
./gradlew docker

# Clean everything at Ctrl+C
trap 'docker service rm jgroups-service; docker service rm jgroups-tracker; exit' TERM INT

docker swarm init && docker network create -d overlay --subnet=172.110.0.0/16 jgroups_network

docker service create --name jgroups-tracker --network jgroups_network --replicas 1 \
--constraint 'node.role == manager' --limit-memory 250m jgroups-tracker:latest

until docker service ls | grep "1/1"
do
    sleep 1s
done

TIME=$(( $(date +%s%3N) + $TIME_ADD ))
docker service create --name jgroups-service --network jgroups_network --replicas ${PEER_NUMBER} \
--env "PEER_NUMBER=${PEER_NUMBER}" --env "TIME=$TIME" \
--limit-memory 250m --log-driver=journald --restart-condition=none \
--mount type=bind,source=/home/jocelyn/tmp/data,target=/data jgroups:latest

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

docker service rm jgroups-tracker
docker service rm jgroups-service

echo "Services removed"



