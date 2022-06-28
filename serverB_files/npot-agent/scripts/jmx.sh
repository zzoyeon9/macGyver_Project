#!/bin/bash

AGENT_PATH=/home1/irteam/npot-agent
if [ ! -f $AGENT_PATH/conf/jmx.yml ]; then
  echo "No ${AGENT_PATH}/conf/jmx.yml exists" >&2
  exit 13
else
  /usr/bin/env java -Dsun.rmi.transport.tcp.handshakeTimeout=15000 -Dsun.rmi.transport.tcp.responseTimeout=30000 -Xms32m -Xmx256m -jar $AGENT_PATH/scripts/jmx-collector.jar $AGENT_PATH/conf/jmx.yml
fi
