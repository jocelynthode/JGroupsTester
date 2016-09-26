#!/usr/bin/env bash
# This scripts runs the benchmarks on a remote cluster

MANAGER_IP=172.16.2.53
PEER_NUMBER=$1


echo "START..."

# Clean everything at Ctrl+C
trap 'docker service rm jgroups-service && \
parallel-ssh -h hosts "docker swarm leave" && docker network rm jgroups-network && \
docker swarm leave --force && exit' TERM INT

docker pull swarm-m:5000/jgroups:latest

docker swarm init
TOKEN=$(docker swarm join-token -q worker)
parallel-ssh -h hosts "docker swarm join --token ${TOKEN} ${MANAGER_IP}:2377"

# If networking doesn't work use ingress
docker network create -d overlay --subnet=10.0.93.0/24 jgroups-network
docker service create --name jgroups-service --network jgroups-network --replicas ${PEER_NUMBER} \
 --limit-memory 500m --log-driver=journald --mount type=bind,source=/home/debian/data,target=/data swarm-m:5000/jgroups

echo "Fleshing out the network..."
sleep 180s

#wait for apps to finish
for i in {1..60} :
do
	sleep 20s
    echo "waiting..."
done

docker service rm jgroups-service
docker network rm jgroups-network
parallel-ssh -h hosts "docker swarm leave"
docker swarm leave --force


#while read ip; do
#    rsync -av ${ip}:~/data/ ../data/
#done <hosts
