#!/usr/bin/env bash
# This scripts runs the benchmarks on a remote cluster

MANAGER_IP=172.16.2.119
LOG_STORAGE=/home/debian/data
PEER_NUMBER=$1
TIME_ADD=$2
EVENTS_TO_SEND=$3
RATE=$4
CHURN=$5

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

function getlogs {
    while read ip; do
        rsync --remove-source-files -av "${ip}:~/data/*.txt" ../data/
        rsync --remove-source-files -av "${ip}:~/data/capture/*.csv" ../data/capture/
    done <hosts
}

echo "START..."

# Clean everything at Ctrl+C
trap 'docker service rm jgroups-service; docker service rm jgroups-tracker; \
sleep 15s; getlogs; exit' TERM INT

docker pull swarm-m:5000/jgroups:latest
docker pull swarm-m:5000/jgroups-tracker:latest

docker swarm init && \
(TOKEN=$(docker swarm join-token -q worker) && \
parallel-ssh -t 0 -h hosts "docker swarm join --token ${TOKEN} ${MANAGER_IP}:2377" && \
docker network create -d overlay --subnet=172.111.0.0/16 jgroups_network || exit)


for i in {1..10}
do
    docker service create --name jgroups-tracker --network jgroups_network --replicas 1 \
    --constraint 'node.role == manager' --limit-memory 300m swarm-m:5000/jgroups-tracker:latest
    until docker service ls | grep "1/1"
    do
        sleep 1s
    done

    TIME=$(( $(date +%s%3N) + $TIME_ADD ))
    docker service create --name jgroups-service --network jgroups_network --replicas ${PEER_NUMBER} \
    --env "PEER_NUMBER=${PEER_NUMBER}" --env "TIME=$TIME" --env "EVENTS_TO_SEND=${EVENTS_TO_SEND}" --env "RATE=$RATE" \
    --limit-memory 300m --restart-condition=none \
    --mount type=bind,source=${LOG_STORAGE},target=/data swarm-m:5000/jgroups:latest

    if [ -n "$CHURN" ]
    then
        echo "Running churn"
        ./cluster/churn.py -v --delay 160 --kill-coordinator ${CHURN} 5 \
        --synthetic 0,${PEER_NUMBER} 1,0 1,0 1,0 1,0 1,0 1,0 1,0 1,0 1,0 1,0 &
        churn_pid=$!

        # wait for service to end
        until docker service ls | grep -q " 10/$(($PEER_NUMBER + 0))"
        do
            sleep 5s
        done
    else
        echo "Running without churn"
        # wait for service to end
        until docker service ls | grep -q " 0/$PEER_NUMBER"
        do
            sleep 5s
        done
    fi
    echo "Running JGroups tester -> Experiment: $i"

    docker service rm jgroups-tracker
    docker service rm jgroups-service

    echo "Services removed"
    sleep 30s

    parallel-ssh -t 0 -h hosts "mkdir -p data/test-$i/capture &&  mv data/*.txt data/test-$i \
    && mv data/capture/*.csv data/test-$i/capture"
    mkdir -p ~/data/test-${i}/capture
    mv ~/data/*.txt ~/data/test-${i}
    mv ~/data/capture/*.csv ~/data/test-${i}/capture
done
