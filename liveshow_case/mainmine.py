import os, platform, json
import sys
import time
import re
import argparse
from typing import DefaultDict
from tqdm import tqdm

MAX_DATAGRAM_SIZE = 1350 # bytes
MAX_BLOCK_SIZE = 1000000 # 1Mbytes
order_preffix = " " if "windows" in platform.system().lower() else "sudo "

block_tracePath=''
logs_Path=''
# move shell scripts to tmp directory
tmp_dir_path = "./tmp"
if not os.path.exists(tmp_dir_path):
        os.mkdir(tmp_dir_path)
# move logs to log diectory
# logs_path = "./logs"
# if not os.path.exists(logs_path):
#     os.mkdir(logs_path)
# move results to result directory
results_path = "./results"
if not os.path.exists(results_path):
    os.mkdir(results_path)

# define parser

parser = argparse.ArgumentParser()
parser.add_argument('--ip', type=str, default=None, help="the ip of container_server_name that required")

parser.add_argument('--port', type=str, default="5555",help="the port of dtp_server that required,default is 5555, and you can randomly choose")

# parser.add_argument('--numbers', type=int, default=60, help="the numbers of blocks that you can control")

parser.add_argument('--server_name', type=str, default="dtp_server", help="the container_server_name ")

parser.add_argument('--client_name', type=str, default="dtp_client", help="the container_client_name ")

# parser.add_argument('--network', type=str, default=None, help="the network trace file ")

# parser.add_argument('--block', type=str, default=None, help="the block trace file ")

parser.add_argument('--run_path', type=str, default="/home/aitrans-server/", help="the path of aitrans_server")

parser.add_argument('--solution_files', type=str, default=None, help="the path of solution files")

parser.add_argument('--run_times', type=int, default=1, help="The times that you want run repeatly")

# parser.add_argument('--enable_print', type=bool, default=False, help="Whether or not print information of processing")

# parser.add_argument('--image_name', type=str, default="dtp-test-image", help="the image to create containers")

parser.add_argument('--config', type=str, default="config.json", help="the path to the config.json")

parser.add_argument('--dump', action="store_true", help="use tcpdump to capture packates")

# parse argument
# global params
params                = parser.parse_args()
server_ip             = params.ip
port                  = params.port
# numbers               = params.numbers
container_server_name = params.server_name
container_client_name = params.client_name
# network_trace         = params.network
# block_trace           = params.block
docker_run_path       = params.run_path
solution_files        = params.solution_files
run_times             = params.run_times
# image_name            = params.image_name
config_filepath       = params.config
# enable_print          = params.enable_print
enable_dump           = params.dump


# check whether local file path is right
# if block_trace and not os.path.exists(block_trace):
#     raise ValueError("no such block trace in '%s'" % (cur_path + block_trace))
# if network_trace and not os.path.exists(network_trace):
#     raise ValueError("no such network trace in '%s'" % (cur_path + network_trace))
if solution_files:
    if not os.path.exists(solution_files):
        raise ValueError("no such solution_files in '%s'" % (solution_files))
    tmp = os.listdir(solution_files)
    if not "solution.cxx" in tmp:
        raise ValueError("There is no solution.cxx in your solution path : %s" % (solution_files))
    if not "solution.hxx" in tmp:
        raise ValueError("There is no solution.hxx in your solution path : %s" % (solution_files))
    # TODO: if upload files that already finished compile
    # compile_preffix = '#' if "libsolution.so" in tmp else ''

# global docker settings
default_block_trace = './aitrans_block.txt'
gen_net_trace_path  = './tmp/traces.txt'
GEN_BLOCK_TRACE_PATH = "./tmp/aitrans_block.txt"
redundant_path = './tmp/redundant.cpp'
# enable tc limits
tc_preffix_c = ''
tc_preffix_s = ''
# enable compile
compile_preffix = ''

def set_server_tc(state: bool):
    '''enable(True) or disable(False) tc in the server container'''
    global tc_preffix_s
    tc_preffix_s = '' if state else '#'

def set_client_tc(state: bool):
    '''enable(True) or disable(False) tc in the client container'''
    global tc_preffix_c
    tc_preffix_c = '' if state else '#'

def parse_config(filepath: str):
    '''
    Parse the given config file and return the json obj
    '''
    with open(filepath, 'r') as f:
        return json.load(f)

def generate_block_file(config: dict):
    '''
    generate block file with the config
    '''

    block_size = min(int(config['block_size']), MAX_BLOCK_SIZE)
    if block_size <= 0:
        block_size = MAX_DATAGRAM_SIZE
    block_num = int(config['block_num'])
    block_gap = 0.001
    if config.get("block_gap"):
       block_gap = int(config["block_gap"])
    with open(os.path.join(tmp_dir_path, 'aitrans_block.txt'), 'w') as f:
        for i in range(block_num):
            f.write('%f    %d    %d    %d\n' % (block_gap * i, 2147483647, block_size, 0))

def generate_consistent_network_file(config):
    '''
    generate consistent network trace

    example: 0, 1, 0.00001, 0.1 # @0 second, 1Mbps, loss rate=0.00001, 100ms latency
    '''
    with open(os.path.join(tmp_dir_path, 'traces.txt'), 'w') as f:
        f.write('%d, %f, %f, %f' % (0, float(config['bw']), float(config['loss']), float(config['rtt']) / 2 / 1000))

def generate_redundancy_code_file(config):
    with open(os.path.join(tmp_dir_path, 'redundant.cpp'), 'w') as f:
        f.write( \
            '''
            #include "solution.hxx"
            float global_redundancy = {0};
            '''.format(max(0.0, float(config['redundancy']))) \
        )



def prepare_docker_files(config):
    '''
    Copy traces and some other files that are consistent in a single test described in `config`
    '''
    # init block trace
    block_trace = default_block_trace # default block trace
    if os.path.exists(str(config.get('block_trace'))):
        # assigned block trace
        block_trace = config.get('block_trace')
    elif config.get("block_num") and config.get("block_size"):
        # generated block trace
        block_trace = GEN_BLOCK_TRACE_PATH
    os.system(order_preffix + "docker cp " + block_trace + ' ' + container_server_name + ":%strace/block_trace/aitrans_block.txt" % (docker_run_path))
    # init network traces
    network_trace = gen_net_trace_path
    if os.path.exists(str(config.get('network_trace'))):
        network_trace = config.get('network_trace')
    if tc_preffix_s == '':
        os.system(order_preffix + "docker cp " + network_trace + ' ' + container_server_name + ":%strace/traces.txt" % (docker_run_path))
    if tc_preffix_c == '':
        os.system(order_preffix + "docker cp " + network_trace + ' ' + container_client_name + ":%strace/traces.txt" % (docker_run_path))
    # init solution files
    if solution_files:
        os.system(order_preffix + "docker cp " + solution_files + ' ' + container_server_name + ":%sdemo/" % (docker_run_path))
    # init redundancy
    # generate_redundancy_code_file(config)
    # os.system(order_preffix + "docker cp " + redundant_path + ' ' + container_server_name + ":%sdemo/redundant.cpp" % (docker_run_path))
    block_tracePath=block_trace
def prepare_shell_code(server_ip, port):

    client_run_line = 'LD_LIBRARY_PATH=./lib RUST_LOG=debug ./client {0} {1} --no-verify > client_err.log 2>&1'
    client_run_line = client_run_line.format(server_ip, port)

    client_run = '''
    #!/bin/bash
    cd {0}
    {1} python3 traffic_control.py -load trace/traces.txt > tc.log 2>&1 &
    rm client.log > tmp.log 2>&1
    sleep 0.2
    {2}
    {1} python3 traffic_control.py --reset eth0
    '''.format(docker_run_path, tc_preffix_c , client_run_line)

    server_run_line = 'LD_LIBRARY_PATH=./lib RUST_LOG=debug ./bin/server {0} {1} trace/block_trace/aitrans_block.txt > ./log/server_err.log 2>&1 &'
    server_run_line = server_run_line.format(server_ip, port)

    server_run = '''
    #!/bin/bash
    cd {0}
    {1} python3 traffic_control.py -aft 3.1 -load trace/traces.txt > tc.log 2>&1 &

    cd {0}demo
    {3} rm libsolution.so ../lib/libsolution.so
    {3} g++ -shared -fPIC solution.cxx -I. -o libsolution.so > compile.log 2>&1
    cp libsolution.so ../lib

    # check port
    a=`lsof -i:{2} | awk '/server/ {{print$2}}'`
    if [ $a > 0 ]; then
        kill -9 $a
    fi

    # check tcpdump
    a=`ps | grep tcpdump | awk '{{print$1}}'`
    if [ $a > 0 ]; then
        kill -9 $a
    fi

    cd {0}
    rm log/server_aitrans.log
    {5} tcpdump -i eth0 -w target.pcap > tcpdump.log 2>&1 &
    {4}
    '''.format(docker_run_path, tc_preffix_s, port, compile_preffix, server_run_line, '' if enable_dump else '#')

    with open(tmp_dir_path + "/server_run.sh", "w", newline='\n')  as f:
        f.write(server_run)

    with open(tmp_dir_path + "/client_run.sh", "w", newline='\n') as f:
        f.write(client_run)

# run shell order
order_list = [
    order_preffix + " docker cp ./traffic_control.py " + container_server_name + ":" + docker_run_path,
    order_preffix + " docker cp ./traffic_control.py " + container_client_name + ":" + docker_run_path,
    order_preffix + " docker cp %s/server_run.sh " %(tmp_dir_path) + container_server_name + ":" + docker_run_path,
    order_preffix + " docker cp %s/client_run.sh " %(tmp_dir_path) + container_client_name + ":" + docker_run_path,
    order_preffix + " docker exec -it " + container_server_name + " nohup /bin/bash %sserver_run.sh" % (docker_run_path)
]

def run_dockers(exp_store_dir, server_ip, port):
    global order_list
    run_seq = 0
    retry_times = 0
    run_times = 1
    while run_seq < run_times:
        print("The %d round :" % (run_seq))

        print("--restart docker--")
        os.system("docker restart %s %s" % (container_server_name, container_client_name))
        time.sleep(5)
        # get server ip after restart docker
        if not server_ip:
            out = os.popen("docker inspect %s" % (container_server_name)).read()
            out_dt = json.loads(out)
            server_ip = out_dt[0]["NetworkSettings"]["IPAddress"]

        prepare_shell_code(server_ip, port)
        #run server and...
        for idx, order in enumerate(order_list):
            print(idx, " ", order)
            os.system(order)

        # ensure server established succussfully
        time.sleep(3)
        print("run client")
        os.system(order_preffix + " docker exec -it " + container_client_name + "  /bin/bash %sclient_run.sh" % (docker_run_path)) #block until exec finished
        #execute each line
        # ensure connection closed
        time.sleep(4)
       
        stop_server = '''
        #!/bin/bash
        cd {0}
        a=`lsof -i:{1} | awk '/server/ {{print$2}}'`
        if [ $a > 0 ]; then
            kill -9 $a
        fi

        # kill tcpdump
        a=`ps | grep tcpdump | awk '{{print$1}}'`
        if [ $a > 0 ]; then
            kill -9 $a
        fi
        {2} kill `ps -ef | grep python | awk '/traffic_control/ {{print $2}}'`
        {2} python3 traffic_control.py --reset eth0
        '''.format(docker_run_path, port, tc_preffix_s)

        with open(tmp_dir_path + "/stop_server.sh", "w", newline='\n')  as f:
            f.write(stop_server)

        print("stop server")
        os.system(order_preffix + " docker cp %s/stop_server.sh " %(tmp_dir_path) + container_server_name + ":%s" % (docker_run_path))
        os.system(order_preffix + " docker exec -it " + container_server_name + "  /bin/bash %sstop_server.sh" % (docker_run_path))
        # move logs
        logs_path = os.path.join(exp_store_dir, "logs")
        logs_Path=logs_path
        if not os.path.exists(logs_path):
                os.mkdir(logs_path)
        os.system(order_preffix + " rm -rf %s/*" % logs_path)
        os.system(order_preffix + " docker cp " + container_client_name + ":%sclient.log %s/." % (docker_run_path, logs_path))
       # print("mid")
       # print(order_preffix + " docker cp " + container_client_name + ":%sclient_err.log %s/." % (docker_run_path, logs_path))
        os.system(order_preffix + " docker cp " + container_client_name + ":%sclient_err.log %s/." % (docker_run_path, logs_path))
        os.system(order_preffix + " docker cp " + container_server_name + ":%slog/ %s/." % (docker_run_path, logs_path))
        os.system(order_preffix + " docker cp " + container_server_name + ":%sdemo/compile.log %s/compile.log" % (docker_run_path, logs_path))
        if tc_preffix_s == '':
            os.system(order_preffix + " docker cp " + container_server_name + ":%stc.log %s/server_tc.log" % (docker_run_path, logs_path))
        if tc_preffix_c == '':
            os.system(order_preffix + " docker cp " + container_client_name + ":%stc.log %s/client_tc.log" % (docker_run_path, logs_path))
        # move .so file
        # os.system(order_preffix + " docker cp " + container_server_name + ":%slib/libsolution.so %s/." % (docker_run_path, logs_path))
        # os.system(order_preffix + " docker cp " + container_client_name + ":%sclient.csv %s/." % (docker_run_path, logs_path))
        # copy pcap file
        if enable_dump:
            os.system(order_preffix + " docker cp " + container_server_name + ":%starget.pcap %s/target.pcap" % (docker_run_path, logs_path))
            os.system(order_preffix + " docker cp " + container_server_name + ":%stcpdump.log %s/tcpdump.log" % (docker_run_path, logs_path))

        # rerun main.py if server fail to start
        try:
            f = open("%s/client.log" % (logs_path), 'r')
            if len(f.readlines()) <= 5:
                print("server run fail, begin restart!")
                retry_times += 1
                continue
        except:
            print("Can not find %s/client.log, file open fail!" % (logs_path))
        run_seq += 1

def start_dockers(config):
    os.system(order_preffix + " docker stop " + container_server_name)
    os.system(order_preffix + " docker stop " + container_client_name)
    os.system(order_preffix + " docker rm " + container_server_name)
    os.system(order_preffix + " docker rm " + container_client_name)
    os.system(order_preffix + " docker run --privileged -dit --cap-add=NET_ADMIN --name %s %s" % (container_server_name, config["image_name"]))
    os.system(order_preffix + " docker run --privileged -dit --cap-add=NET_ADMIN --name %s %s" % (container_client_name, config["image_name"]))

CLIENT_LOG_PATTERN = re.compile(r'connection closed, recv=(-?\d+) sent=(-?\d+) lost=(-?\d+) rtt=(?:(?:(\d|.+)ms)|(?:(-1))) cwnd=(-?\d+), total_bytes=(-?\d+), complete_bytes=(-?\d+), good_bytes=(-?\d+), total_time=(-?\d+)')
CLIENT_STAT_INDEXES = ["c_recv", "c_sent", "c_lost", "c_rtt(ms)", "c_cwnd", "c_total_bytes", "c_complete_bytes", "c_good_bytes", "c_total_time(us)", "qoe", "retry_times"]
CLIENT_BLOCKS_INDEXES = ["BlockID", "bct", "BlockSize", "Priority", "Deadline"]

def parse_client_log(dir_path):
    '''
    Parse client.log and get two dicts of information.

    `client_blocks_dict` stores information in client.log about block's stream_id, bct, deadline and priority
    `client_stat_dict` stores statistics offered in client.log. Some important information is like goodbytes and total running time(total time)
    '''
    # collect client blocks information
    client_blocks_dict = {}
    for index in CLIENT_BLOCKS_INDEXES:
        client_blocks_dict[index] = []
    # collect client stats
    client_stat_dict = {}
    for index in CLIENT_STAT_INDEXES:
        client_stat_dict[index] = []

    with open(os.path.join(dir_path, "client.log")) as client:
        client_lines = client.readlines()

        for line in client_lines[4:-1]:
            if len(line) > 1:
               client_line_list = line.split()
               if len(client_line_list) != len(CLIENT_BLOCKS_INDEXES):
                   print("A client block log line has error format in : %s. This happens sometime." % dir_path)
                   continue
               for i in range(len(client_line_list)):
                   client_blocks_dict[CLIENT_BLOCKS_INDEXES[i]].append(client_line_list[i])

        # try to parse the last line of client log
        try:
            match = CLIENT_LOG_PATTERN.match(client_lines[-1])
            if match == None:
                raise ValueError("client re match returns None in : %s" % dir_path, client_lines[-1])


            client_stat_dict["c_recv"].append(float(match.group(1)))
            client_stat_dict["c_sent"].append(float(match.group(2)))
            client_stat_dict["c_lost"].append(float(match.group(3)))

            if match.group(4) is None:
               client_stat_dict["c_rtt(ms)"].append(float(-1))
            else:
               client_stat_dict["c_rtt(ms)"].append(float(match.group(4)))

            client_stat_dict["c_cwnd"].append(float(match.group(6)))
            client_stat_dict["c_total_bytes"].append(float(match.group(7)))
            client_stat_dict["c_complete_bytes"].append(float(match.group(8)))
            client_stat_dict["c_good_bytes"].append(float(9))
            client_stat_dict["c_total_time(us)"].append(float(match.group(10)))

            # invalid stat
            client_stat_dict["qoe"].append(-1)
            client_stat_dict["retry_times"].append(-1)

            return client_blocks_dict, client_stat_dict

        except Exception:
            print(dir_path)
            print(client_lines[-1])
            if match is not None:
                print(match.groups())
            raise ValueError("Could not parse client's last line")

def parse_client_result(config, cc_algo, logs_path, store_path):
    '''
    Parse the content in client.log and write the BCT as results in store_path

    Results looks like the following example:

    ```txt
    {"block_size": 50, "block_num": 10, "redundancy": 0.0, "cc": "bbr", "bw": 100, "rtt": 50, "loss": 0} # the current config
    {"bct(ms)": "146"} # bct result of the first block
    {"bct(ms)": "231"} # ...
    ```
    '''
    client_blocks_dict, _ = parse_client_log(logs_path)
    new_config = config.copy()
    new_config['cc'] = cc_algo
    with open(store_path, 'w') as f:
        f.write(json.dumps(new_config))
        f.write('\n')
        for _, bct in enumerate(client_blocks_dict['bct']):
            obj = {
                'bct(ms)': bct
            }
            f.write(json.dumps(obj))
            f.write('\n')

if __name__ == "__main__":
    # parse configs from 'config.json'
    configs = parse_config(config_filepath)
    if type(configs) != list:
        print('Configs parse error: configs should be json list')
    if len(configs) == 0:
        print("There is no config in the file")

    total = len(configs)

    # start testing
    with tqdm(configs) as pbar:
        for config in pbar:
            # decide the name of the experiment log
            exp_dir = "t" + str(time.time_ns())
            if config.get("dir_name") is not None:
                exp_dir = config["dir_name"]
            exp_store_dir = os.path.join(results_path, exp_dir)
            if not os.path.exists(exp_store_dir):
                os.mkdir(exp_store_dir)
            print("Results lie in: %s" % exp_store_dir)

            print(config)
            if config.get("block_trace") is None and \
                config.get("block_num") is not None and \
                config.get("block_size") is not None:
                print("block_trace: None. Generating block trace ...")
                generate_block_file(config)

            if config.get("network_trace") is None or config["network_trace"] == "":
                if config.get("rtt") is not None and \
                    config.get("bw") is not None and \
                    config.get("loss") is not None:
                        # generate network trace
                        generate_consistent_network_file(config)
                        print("Creating consistent network trace with \{rtt:%s, bw: %s, loss:%s\}" %
                              (str(config["rtt"]), str(config["bw"], str(config["loss"]))))
                        set_server_tc(True)
                        set_client_tc(True)
                else:
                    # disable tc
                    print("No network control")
                    set_server_tc(False)
                    set_client_tc(False)
            else:
                # load network trace file
                print("Use network trace: %s" % config["network_trace"])
                set_server_tc(True)
                set_client_tc(True)


            start_dockers(config)
            prepare_docker_files(config)
            run_dockers(exp_store_dir, server_ip, port)

            # store_path = os.path.join(exp_store_dir, "%d_%s" % (idx, cc_algo))
            # parse_client_result(config, cc_algo, store_path)

            with open(os.path.join(exp_store_dir, 'config.json'), 'w') as f:
                json.dump(config, f)
    #print main results by reading logs //temprary ways
    #blocks num lines of blocks
    '''   sendBlockNum=len(open('./aitrans_block.txt','r').readlines())

    servErrPath='./results/test1/logs/log/server_err.log'
    logs_Path='./results/test1/logs'
    
    blockDropNum=0
    servErrLog=open(servErrPath)
    for line in servErrLog:
        if line!='' and line[0]=='b' and line[1]=='l':
            blockDropNum +=1
    blockSentNum=sendBlockNum-blockDropNum

    clientLog=open(logs_Path+'/client.log')
    totalBct=0
    highPriNum=0	#高优先级块数
    lateHighPri=0	#超时到达高优先级块数
    lateBlock =0 	#超时块数
    recvBlock =0        #总接收块
    line=clientLog.readline()
    for line in clientLog:
        if line == 'BlockID  bct  BlockSize  Priority  Deadline\n':
            break

    for line in clientLog:

        if line =='connection closed\n':
            break
        else:
            recvBlock+=1
            p=re.findall(r'\b\d+\b',line)
            p=list(map(int,p))
            bct=p[1]
            totalBct+=bct
            if p[3]==1:
                highPriNum+=1
            if bct>p[4]:
                lateBlock+=1
                if p[3]==1:
                    lateHighPri +=1
    print('指标\t\t\t\t\t数量\t\t比例\n'.format(recvBlock))
    print('总块数:\t\t\t\t\t{}\t\t{}%\n'.format(sendBlockNum,sendBlockNum/sendBlockNum*100))
    print('总发送块:\t\t\t\t{}\t\t{}%\n'.format(blockSentNum,blockSentNum/sendBlockNum*100))
    print('总接收块:\t\t\t\t{}\t\t{}%\n'.format(recvBlock,recvBlock/sendBlockNum*100))
    print('所有块按时完成率:\t\t\t{}\t\t{}%\n'.format(recvBlock-lateBlock,(recvBlock-lateBlock)/sendBlockNum*100))
    print('高优先级块按时完成率:\t\t\t{}\t\t{}%\n'.format(highPriNum,100*(highPriNum-lateHighPri)/highPriNum))
    print('所有块平均完成时间:\t\t\t{}\t\t\n'.format(round(totalBct/recvBlock,2)))


'''

