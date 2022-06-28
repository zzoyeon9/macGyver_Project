#!/bin/bash

AGENT_PATH=/home1/irteam/npot-agent
if [ ! -f $AGENT_PATH/conf/kafkalag.yml ]; then
  echo "No ${AGENT_PATH}/conf/kafkalag.yml exists" >&2
  exit 13
else
  /usr/bin/env java -Xms32m -Xmx256m -Dlog4j.configuration="file:$AGENT_PATH/conf/kafkalag-log4j.properties" -jar $AGENT_PATH/scripts/kafkalag-collector.jar $AGENT_PATH/conf/kafkalag.yml
fi
