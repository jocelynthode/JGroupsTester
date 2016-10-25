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
    echo "You have to indicate at which rate you want to send events on each peers"
    exit
fi

function getlogs {
    while read ip; do
        rsync --remove-source-files -av "${ip}:~/data/" ../data/
    done <hosts
}

echo "START..."

# Clean everything at Ctrl+C
trap 'docker service rm jgroups-service; docker service rm jgroups-tracker; getlogs; exit' TERM INT

docker pull swarm-m:5000/jgroups:latest
docker pull swarm-m:5000/jgroups-tracker:latest

docker swarm init && \
(TOKEN=$(docker swarm join-token -q worker) && \
parallel-ssh -t 0 -h hosts "docker swarm join --token ${TOKEN} ${MANAGER_IP}:2377" && \
docker network create -d overlay --subnet=172.111.0.0/16 jgroups_network || exit)


for i in {1..10}
do
    docker service create --name jgroups-tracker --network jgroups_network --replicas 1 \
    --constraint 'node.role == manager' --limit-memory 250m swarm-m:5000/jgroups-tracker:latest
    until docker service ls | grep "1/1"
    do
        sleep 1s
    done

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
    echo "Running JGroups tester -> Experiment: $i"
    # wait for service to end
    until docker service ls | grep -q " 0/$PEER_NUMBER"
    do
        sleep 5s
    done

    docker service rm jgroups-tracker
    docker service rm jgroups-service

    echo "Services removed"
    sleep 1m

    parallel-ssh -t 0 -h hosts "mkdir -p data/test-$i/capture &&  mv data/*.txt data/test-$i \
    && mv data/capture/*.csv data/test-$i/capture"
    mkdir -p ~/data/test-${i}/capture
    mv ~/data/*.txt ~/data/test-${i}
    mv ~/data/capture/*.csv ~/data/test-${i}/capture
done
