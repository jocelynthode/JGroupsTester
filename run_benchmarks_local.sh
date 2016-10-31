#!/usr/bin/env bash
# This scripts runs the benchmarks on a remote cluster

MANAGER_IP=172.16.2.119
PEER_NUMBER=$1
TIME_ADD=$2
EVENTS_TO_SEND=$3
RATE=$4

if [ -z "$PEER_NUMBER" ]
  then
    echo "You have to indicate number of peers"
    exit
fi

if [ -z "$TIME_ADD" ]
  then
    echo "You have to indicate by how much you want to delay JGroups start"
    exit
fi

if [ -z "$EVENTS_TO_SEND" ]
  then
    echo "You have to indicate how many events you want to send in total per peers"
    exit
fi

if [ -z "$RATE" ]
  then
    echo "You have to indicate at which rate you want to send events on each peers in ms"
    exit
fi

echo "START..."
./gradlew docker

# Clean everything at Ctrl+C
trap 'docker service rm jgroups-service; docker service rm jgroups-tracker; docker service rm jgroups-coordinator; exit' TERM INT

docker swarm init && docker network create -d overlay --subnet=172.110.0.0/16 jgroups_network

docker service create --name jgroups-tracker --network jgroups_network --replicas 1 \
--constraint 'node.role == manager' --limit-memory 250m jgroups-tracker:latest
until docker service ls | grep "1/1"
do
    sleep 1s
done

TIME=$(( $(date +%s%3N) + $TIME_ADD ))
docker service create --name jgroups-coordinator --network jgroups_network --replicas 1 \
--constraint 'node.role == manager' \
--env "PEER_NUMBER=${PEER_NUMBER}" --env "TIME=$TIME" --env "EVENTS_TO_SEND=${EVENTS_TO_SEND}" --env "RATE=$RATE" \
--limit-memory 250m --log-driver=journald --restart-condition=none \
--mount type=bind,source=/home/jocelyn/tmp/data,target=/data jgroups:latest

docker service create --name jgroups-service --network jgroups_network --replicas $(($PEER_NUMBER - 1)) \
--env "PEER_NUMBER=${PEER_NUMBER}" --env "TIME=$TIME" --env "EVENTS_TO_SEND=${EVENTS_TO_SEND}" --env "RATE=$RATE" \
--limit-memory 250m --log-driver=journald --restart-condition=none \
--mount type=bind,source=/home/jocelyn/tmp/data,target=/data jgroups:latest

while docker service ls | grep "0/1"
do
    sleep 1s
done

while docker service ls | grep " 0/$PEER_NUMBER"
do
    sleep 1s
done
echo "Running JGroups tester..."
# wait for service to end
until docker service ls | grep -q " 0/1"
do
    sleep 5s
done
until docker service ls | grep -q "0/$PEER_NUMBER"
do
    sleep 5s
done

docker service rm jgroups-tracker
docker service rm jgroups-coordinator
docker service rm jgroups-service

echo "Services removed"
