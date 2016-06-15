#!/usr/bin/env bash
# This script needs to run in the container

addtime() {
    while IFS= read -r line; do
        echo "$(date +%s%N | cut -b1-13) $line"
    done
}

cd /code/scripts

MY_IP_ADDR=$(ifconfig eth0 | grep "inet addr" | cut -d ':' -f 2 | cut -d ' ' -f 1)
TMP=$(dig -x $MY_IP_ADDR +short)
MY_NAME=(${TMP//./ })

# wait for all peers
sleep 1m

echo 'Starting epto peer: starting java' | addtime > localhost.txt 2>&1
exec java -Xms50m -Xmx250m -Djava.net.preferIPv4Stack=true -cp ../build/libs/jgroups-tester-1.0-SNAPSHOT-all.jar EventTesterKt | addtime >> localhost.txt 2>&1

