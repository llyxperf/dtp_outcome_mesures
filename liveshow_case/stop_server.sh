
        #!/bin/bash
        cd /home/qwe/aitrans-server/
        a=`lsof -i:5555 | awk '/server/ {print$2}'`
        if [ $a > 0 ]; then
            kill -9 $a
        fi

        # kill tcpdump
        a=`ps | grep tcpdump | awk '{print$1}'`
        if [ $a > 0 ]; then
            kill -9 $a
        fi
         kill `ps -ef | grep python | awk '/traffic_control/ {print $2}'`
         python3 traffic_control.py --reset ens33
        
