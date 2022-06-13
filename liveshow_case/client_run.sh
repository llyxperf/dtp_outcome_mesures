
    #!/bin/bash
    cd /home/qwe/aitrans-server/
     python3 traffic_control.py -load trace/traces.txt > tc.log 2>&1 &
    rm client.log > tmp.log 2>&1
    sleep 0.2
    LD_LIBRARY_PATH=./lib RUST_LOG=debug ./client 127.0.0.1 5555 --no-verify > client_err.log 2>&1
     python3 traffic_control.py --reset ens33
    
