import linecache
import time
import os
import re
#graph
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

def parse_log(logPath,blockConfPath):

    logStart='BlockID  bct  BlockSize  Priority  Deadline\n'
    
    while os.path.isfile(logPath)==False:
        #a=os.system(prefix+' docker cp '+containerName+':'+containerPath+'/'+logPath+' '+destDir)
        continue
        
    flag=True
    
    lineNum=1 #offset
    
    while flag:
       #读头
       line=linecache.getline(logPath,lineNum)
       if line==logStart:
           lineNum+=1
           break
       elif line!='' and line!='\n':
           lineNum+=1
           #print(line,end='')
       elif lineNum==3:
           lineNum+=1
       else:
           #time.sleep(1) 
           #a=os.system(prefix+' docker cp '+containerName+':'+containerPath+'/'+logPath+' '+destDir)
           #更新log缓存
           time.sleep(0.3)
           linecache.updatecache(logPath)


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
        #wait
        curTime+=interval
        time.sleep(interval)
        #wait till client write some logs.
        #a=os.system(prefix+' docker cp '+containerName+':'+containerPath+' '+destDir)#flush
        
        _=linecache.updatecache(logPath)
        blank=False
        while blank!=True:
            line=linecache.getline(logPath,lineNum)
            if line=='':
                blank=True
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
        if changeFlag==True:
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

    print('指标\t\t\t\t\t数量\t\t比例\n'.format(recvBlockNum))
    print('总块数:\t\t\t\t\t{}\t\t{}%\n'.format(sendBlockNum,round(sendBlockNum/sendBlockNum*100,2)))
    print('总发送块:\t\t\t\t{}\t\t{}%\n'.format(blockSentNum,round(blockSentNum/sendBlockNum*100,2)))
    print('总接收块:\t\t\t\t{}\t\t{}%\n'.format(recvBlockNum,round(recvBlockNum/sendBlockNum*100,2)))
    print('所有块按时完成率:\t\t\t{}\t\t{}%\n'.format(recvBlockNum-total_late,round((recvBlockNum-total_late)/sendBlockNum*100,2)))
    print('高优先级块按时完成率:\t\t\t{}\t\t{}%\n'.format(highPriNum-highPri_late,round(100*(highPriNum-highPri_late)/highPriNum,2)))
    print('所有块平均完成时间:\t\t\t{}ms\t\t\n'.format(round(totalBct/recvBlockNum,2)))

    os.system('rm '+logPath)
#icopy
#containerName='dtp_client'
#containerPath='/home/aitrans-server'
#destDir='.'
#prefix='sudo'
#testName='test1'

#testPath='.' #aitrans
#resultPath=testPath+'/results/'+testName

if __name__ == "__main__":
    logPath='client.log'
    blockConfPath='./trace/block_trace/aitrans_block.txt'
    parse_log(logPath,blockConfPath)






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
'''
    print('指标\t\t\t\t\t数量\t\t比例\n'.format(recvBlockNum))
    print('总块数:\t\t\t\t\t{}\t\t{}%\n'.format(sendBlockNum,round(sendBlockNum/sendBlockNum*100,2)))
    print('总发送块:\t\t\t\t{}\t\t{}%\n'.format(blockSentNum,round(blockSentNum/sendBlockNum*100,2)))
    print('总接收块:\t\t\t\t{}\t\t{}%\n'.format(recvBlockNum,round(recvBlockNum/sendBlockNum*100,2)))
    print('所有块按时完成率:\t\t\t{}\t\t{}%\n'.format(recvBlockNum-total_late,round((recvBlockNum-total_late)/sendBlockNum*100,2)))
    print('高优先级块按时完成率:\t\t\t{}\t\t{}%\n'.format(highPriNum-highPri_late,round(100*(highPriNum-highPri_late)/highPriNum,2)))
    print('所有块平均完成时间:\t\t\t{}ms\t\t\n'.format(round(totalBct/recvBlockNum,2)))

'''
    return resDict
