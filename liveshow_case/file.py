import linecache
import time
import os
import re
#image
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker


filename='client.log'
lineNum=1
readFlag=True

#icopy
containerName='dtp_client'
#containerPath='/home/aitrans-server'
destDir='.'
prefix='sudo'
#testName='test1'

testPath='.' #aitrans
#resultPath=testPath+'/results/'+testName
while os.path.isfile(filename)==False:
    #a=os.system(prefix+' docker cp '+containerName+':'+containerPath+'/'+filename+' '+destDir)
    continue
flag=True
while flag:
   #读头
   line=linecache.getline(filename,lineNum)
   if line=='BlockID  bct  BlockSize  Priority  Deadline\n':
       lineNum+=1#next line
       break
   elif line!='' and line!='\n':
       lineNum+=1#next line
       print(line,end='')
   elif lineNum==3:
       lineNum+=1
   else:
       #time.sleep(1)
       #a=os.system(prefix+' docker cp '+containerName+':'+containerPath+'/'+filename+' '+destDir)
       time.sleep(0.3)
       linecache.updatecache(filename)


#analysing
sendBlockNum=len(open('./trace/block_trace/aitrans_block.txt','r').readlines())



totalBct=0
highPriNum=0	#高优先级块数
lateHighPri=0	#超时到达高优先级块数
lateBlock =0 	#超时块数
recvBlock =0        #总接收块
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

    _=linecache.updatecache(filename)
    blank=False
    while blank!=True:
        line=linecache.getline(filename,lineNum)
        if line=='':
            blank=True
        elif line=='connection closed\n':
            blank=True
            flag=False
        else:#parse
            p=re.findall(r'\b\d+\b',line)
            p=list(map(int,p))
            if len(p)!=5:
                break#ramdom bug
            changeFlag=True
            recvBlock+=1
            bct=p[1]
            totalBct+=bct
            lineNum+=1
            if p[3]==1:
                highPriNum+=1
            if bct>p[4]:
                lateBlock+=1
                if p[3]==1:
                    lateHighPri +=1
    #continue
    if changeFlag==True:
        #print('已接收{}块，平均完成时间为{}s,高优先级块按时完成率为{}%,所有块按时完成率为{}%'.format(recvBlock,round(totalBct/recvBlock,2),100*(highPriNum-lateHighPri)/highPriNum,(recvBlock-lateBlock)/sendBlockNum*100))
        avrTime=round(totalBct/recvBlock,2)
        highBlockRate=round(100*(highPriNum-lateHighPri)/highPriNum,2)
        blockRate=round((recvBlock-lateBlock)/recvBlock*100,2)

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
        print('已接收{}块，平均完成时间为{}ms,高优先级块按时完成率为{}%'.format(recvBlock,avrTime,highBlockRate))
   #blocks num lines of blocks


servErrPath='./log/server_err.log'
#logs_Path=resultPath+'/logs'

blockDropNum=0
servErrLog=open(servErrPath)
for line in servErrLog:
    if line!='' and line[0]=='b' and line[1]=='l':
        blockDropNum +=1
blockSentNum=sendBlockNum-blockDropNum

print('指标\t\t\t\t\t数量\t\t比例\n'.format(recvBlock))
print('总块数:\t\t\t\t\t{}\t\t{}%\n'.format(sendBlockNum,round(sendBlockNum/sendBlockNum*100,2)))
print('总发送块:\t\t\t\t{}\t\t{}%\n'.format(blockSentNum,round(blockSentNum/sendBlockNum*100,2)))
print('总接收块:\t\t\t\t{}\t\t{}%\n'.format(recvBlock,round(recvBlock/sendBlockNum*100,2)))
print('所有块按时完成率:\t\t\t{}\t\t{}%\n'.format(recvBlock-lateBlock,round((recvBlock-lateBlock)/sendBlockNum*100,2)))
print('高优先级块按时完成率:\t\t\t{}\t\t{}%\n'.format(highPriNum-lateHighPri,round(100*(highPriNum-lateHighPri)/highPriNum,2)))
print('所有块平均完成时间:\t\t\t{}ms\t\t\n'.format(round(totalBct/recvBlock,2)))

os.system('rm '+filename)

