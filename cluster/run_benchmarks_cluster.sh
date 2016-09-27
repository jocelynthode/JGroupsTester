#!/usr/bin/env bash
# This scripts runs the benchmarks on a remote cluster

MANAGER_IP=172.16.2.53
PEER_NUMBER=$1


echo "START..."

# Clean everything at Ctrl+C
trap 'exit' TERM INT

docker pull swarm-m:5000/jgroups:latest
parallel-ssh -h hosts "docker pull swarm-m:5000/jgroups:latest"

parallel-ssh -h hosts "for i in {1..17}; do docker run --network host -d --env \"FILENAME=\${i}\" \
-v /home/debian/data:/data swarm-m:5000/jgroups; done"
for i in {1..13}; do docker run --network host -d --env "FILENAME=${i}" \
-v /home/debian/data:/data swarm-m:5000/jgroups; done

echo "Fleshing out the network..."
sleep 20s

#wait for apps to finish
for i in {1..100} :
do
	sleep 20s
    echo "waiting..."
done


#while read ip; do
#    rsync -av ${ip}:~/data/ ../data/
#done <hosts
