"""
This module is used for processing the DTP block data genered by the sender and reciever
"""

import os, platform, json
import sys
import time
import re
import argparse
from typing import DefaultDict
from tqdm import tqdm

"""Process the result"""

#client.log

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


def calculate_statiscs(logPath='./client.log',draw=False):

"""
Parse the content tn the Client.log,return a dict contains the statistics of the outcome mesures.

keys:
'TotalBlockNum':Number of blocks planning to send by the server.
'BlockSentNum':Number of blocks sent by the server.
'BlockRecvNum':Number of blocks recieved by the client
'BlockInTime':Number of blocks arrived before the ddl.
'HighpriBlockInTime':the number of high priority blocks arrived before the ddl.
'AvrTime':Average BCT(ms)

if parameter draw set to True,Draw a picture with y value as block-in-time rate and x value as time.
"""


    logStart='BlockID  bct  BlockSize  Priority  Deadline\n'
    
    if os.path.isfile(logPath)==False:
        print("Error calculate_statiscs:clint.log not found")
        return
    flag=True
    
    lineNum=4 #offset

   #读头
    line=linecache.getline(logPath,lineNum)
    if line==logStart:
       lineNum+=1
    else:
       print("Error calculate_statiscs:incomplete clitnt.log")
       return

    #analysing
    
    endFlagstr='connection closed\n'
    sendBlockNum=len(open(blockConfPath,'r').readlines()) #发送块数
    totalBct=0      #总发送时间
    highPriNum=0	#高优先级块数
    highPri_late=0	#超时到达高优先级块数
    total_late =0 	#超时块数
    recvBlockNum=0        #总接收块
    flag=True

    #drawing

    timeX=[]
    high_rateY=[]
    rateY=[]
    avrTimeY=[]
    curTime=0

    interval=0.2 #sec

    #plt.ion()


    while flag:
        changeFlag=False#output when new lines arrive

        _=linecache.updatecache(logPath)
        blank=False
        while blank!=True:
            line=linecache.getline(logPath,lineNum)
            if line=='':
                print("Error calculate_statiscs:incomplete clitnt.log")
                return
            elif line==endFlagstr:
                blank=True
                flag=False
            else:#parse
                p=re.findall(r'\b\d+\b',line)
                p=list(map(int,p))
                if len(p)!=5:
                    break#ramdom bug
                changeFlag=True
                recvBlockNum+=1
                bct=p[1]
                totalBct+=bct
                lineNum+=1
                if p[3]==1:
                    highPriNum+=1
                if bct>p[4]:
                    total_late+=1
                    if p[3]==1:
                        highPri_late +=1
        #continue
        if changeFlag==True and draw ==True:
            #print('已接收{}块，平均完成时间为{}s,高优先级块按时完成率为{}%,所有块按时完成率为{}%'.format(recvBlockNum,round(totalBct/recvBlockNum,2),100*(highPriNum-highPri_late)/highPriNum,(recvBlockNum-total_late)/sendBlockNum*100))
            avrTime=round(totalBct/recvBlockNum,2)
            highBlockRate=round(100*(highPriNum-highPri_late)/highPriNum,2)
            blockRate=round((recvBlockNum-total_late)/recvBlockNum*100,2)

            timeX.append(curTime)
            high_rateY.append(highBlockRate)
            rateY.append(blockRate)
            
            plt.clf()
           # print(curTime)
            #print(high_rateY)
            plt.gca().yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f %%'))
            plt.gca().xaxis.set_major_formatter(mticker.FormatStrFormatter('%.1fs'))
            plt.xlabel('time')
            plt.ylabel('rate')
            plt.title('DTP live show')
            plt.plot(timeX,high_rateY,label='HighPriority')
            plt.plot(timeX, rateY, label='Total')
            plt.legend()
            plt.pause(interval)
            print('已接收{}块，平均完成时间为{}ms,高优先级块按时完成率为{}%'.format(recvBlockNum,avrTime,highBlockRate))
       #blocks num lines of blocks


    servErrPath='./log/server_err.log'
    #logs_Path=resultPath+'/logs'

    blockDropNum=0
    servErrLog=open(servErrPath)
    for line in servErrLog:
        if line!='' and line[0]=='b' and line[1]=='l':
            blockDropNum +=1
    blockSentNum=sendBlockNum-blockDropNum
    
    
    resDict={'TotalBlockNum':sendBlockNum,'BlockSentNum':blockSentNum,'BlockRecvNum':recvBlockNum,'BlockInTime':recvBlockNum-total_late,'HighpriBlockInTime':highPriNum-highPri_late,'AvrTime':round(totalBct/recvBlockNum,2))}
    
    return resDict
