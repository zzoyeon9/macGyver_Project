#!/bin/bash
cd /home1/irteam/npot-agent
bin/agent.sh stop
rm -f bin/npot-agent
cd bin
wget -q http://npot-dist.navercorp.com/dev/npot-agent/npot-agent
chmod 755 npot-agent
cd ..
bin/agent.sh start

