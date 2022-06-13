
    #!/bin/bash
    cd /home/qwe/aitrans-server/
     python3 traffic_control.py -aft 3.1 -load trace/traces.txt > tc.log 2>&1 &

    cd /home/qwe/aitrans-server/demo
     g++ -shared -fPIC solution.cxx -I. -o libsolution.so > compile.log 2>&1
    cp libsolution.so ../lib

    # check port
    a=`lsof -i:5555 | awk '/server/ {print$2}'`
    if [ $a > 0 ]; then
        kill -9 $a
    fi

    # check tcpdump
    a=`ps | grep tcpdump | awk '{print$1}'`
    if [ $a > 0 ]; then
        kill -9 $a
    fi

    cd /home/qwe/aitrans-server/
    # tcpdump -i eth0 -w target.pcap > tcpdump.log 2>&1 &
    LD_LIBRARY_PATH=./lib RUST_LOG=debug ./server 127.0.0.1 5555 trace/block_trace/aitrans_block.txt > ./log/server_err.log 2>&1 &

