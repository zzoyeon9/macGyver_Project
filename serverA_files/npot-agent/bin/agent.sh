#! /usr/bin/env bash

NPOT_AGENT_HOME=/home1/irteam/npot-agent
NPOT_AGENT_OPTS=
USER=irteam
GROUP=irteam
STDLOG=no

if [ -r /lib/lsb/init-functions ]; then
    source /lib/lsb/init-functions
fi

if [ -z "$STDOUT" ]; then
    STDOUT=${NPOT_AGENT_HOME}/logs/npot-agent.out
fi
if [ ! -f "$STDOUT" ]; then
    mkdir -p `dirname $STDOUT`
fi

if [ -z "$STDERR" ]; then
    STDERR=${NPOT_AGENT_HOME}/logs/npot-agent.err
fi
if [ ! -f "$STDERR" ]; then
    mkdir -p `dirname $STDERR`
fi

function pidofproc() {
    if [ $# -ne 3 ]; then
        echo "Expected three arguments, e.g. $0 -p pidfile daemon-name"
    fi

    if [ ! -f "$2" ]; then
        return 1
    fi

    local pidfile=`cat $2`

    if [ "x$pidfile" == "x" ]; then
        return 1
    fi

    if ps --pid "$pidfile" | grep -q $(basename $3); then
        return 0
    fi

    return 1
}

function killproc() {
    if [ $# -ne 3 ]; then
        echo "Expected three arguments, e.g. $0 -p pidfile signal"
    fi

    pid=`cat $2`

    kill -s $3 $pid
}

function log_failure_msg() {
    echo "$@" "[ FAILED ]"
}

function log_success_msg() {
    echo "$@" "[ OK ]"
}

# Process name ( For display )
name=npot-agent

# Daemon name, where is the actual executable
daemon=${NPOT_AGENT_HOME}/bin/npot-agent

# pid file for the daemon
pidfile=${NPOT_AGENT_HOME}/npot-agent.pid
piddir=`dirname $pidfile`

if [ ! -d "$piddir" ]; then
    mkdir -p $piddir
    chown $USER:$GROUP $piddir
fi

# Configuration file
config=${NPOT_AGENT_HOME}/conf/agent.conf
confdir=${NPOT_AGENT_HOME}/conf

# If the daemon is not there, then exit.
[ -x $daemon ] || exit 5

case $1 in
    start)
        # Checked the PID file exists and check the actual status of process
        if [ -e $pidfile ]; then
            pidofproc -p $pidfile $daemon > /dev/null 2>&1 && status="0" || status="$?"
            # If the status is SUCCESS then don't need to start again.
            if [ "x$status" = "x0" ]; then
                log_failure_msg "$name process is running"
                exit 0 # Exit
            fi
        fi

        log_success_msg "Starting the process" "$name"
        if command -v startproc >/dev/null; then
            startproc -u "$USER" -g "$GROUP" -p "$pidfile" -q -- "$daemon" -pidfile "$pidfile" -config "$config" $NPOT_AGENT_OPTS
        elif which start-stop-daemon > /dev/null 2>&1; then
            if [ "$STDLOG" = "yes" ]; then
              start-stop-daemon --chuid $USER:$GROUP --start --quiet --pidfile $pidfile --exec $daemon -- -pidfile $pidfile -config $config $NPOT_AGENT_OPTS >>$STDOUT 2>>$STDERR &
            else
              start-stop-daemon --chuid $USER:$GROUP --start --quiet --pidfile $pidfile --exec $daemon -- -pidfile $pidfile -config $config $NPOT_AGENT_OPTS >>/dev/null 2>&1 &
            fi
        else
            if [ "$STDLOG" = "yes" ]; then
              /bin/sh -c "nohup $daemon -pidfile $pidfile -config $config $NPOT_AGENT_OPTS >>$STDOUT 2>>$STDERR &" $USER
            else
              /bin/sh -c "nohup $daemon -pidfile $pidfile -config $config $NPOT_AGENT_OPTS >>/dev/null 2>&1 &" $USER
            fi
        fi
        log_success_msg "$name process was started"
        ;;

    stop)
        # Stop the daemon.
        if [ -e $pidfile ]; then
            pidofproc -p $pidfile $daemon > /dev/null 2>&1 && status="0" || status="$?"
            if [ "$status" = 0 ]; then
                if killproc -p $pidfile SIGTERM && /bin/rm -rf $pidfile; then
                    log_success_msg "$name process was stopped"
                else
                    log_failure_msg "$name failed to stop service"
                fi
            fi
        else
            log_failure_msg "$name process is not running"
        fi
        ;;

    reload)
        # Reload the daemon.
        if [ -e $pidfile ]; then
            pidofproc -p $pidfile $daemon > /dev/null 2>&1 && status="0" || status="$?"
            if [ "$status" = 0 ]; then
                if killproc -p $pidfile SIGHUP; then
                    log_success_msg "$name process was reloaded"
                else
                    log_failure_msg "$name failed to reload service"
                fi
            fi
        else
            log_failure_msg "$name process is not running"
        fi
        ;;

    restart)
        # Restart the daemon.
        $0 stop && sleep 2 && $0 start
        ;;

    status)
        # Check the status of the process.
        if [ -e $pidfile ]; then
            if pidofproc -p $pidfile $daemon > /dev/null; then
                log_success_msg "$name Process is running"
                exit 0
            else
                log_failure_msg "$name Process is not running"
                exit 1
            fi
        else
            log_failure_msg "$name Process is not running"
            exit 3
        fi
        ;;

    version)
        $daemon version
        ;;

    *)
        # For invalid arguments, print the usage message.
        echo "Usage: $0 {start|stop|restart|status|version}"
        exit 2
        ;;
esac
