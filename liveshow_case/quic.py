import linecache
import time
import os
import re
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

interval=0.2 #sec

totalBct=0
highPriNum=0	#高优先级块数
lateHighPri=0	#超时到达高优先级块数
lateBlock =0 	#超时块数
recvBlock =0        #总接收块
flag=True

while flag:
    changeFlag=False#output when new lines arrive
    #wait
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
        print('已接收{}块，平均完成时间为{}ms,高优先级块按时完成率为{}%'.format(recvBlock,round(totalBct/recvBlock,2),round(100*(highPriNum-lateHighPri)/highPriNum,2)))
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
print('总块数:\t\t\t\t\t{}\t\t{}%\n'.format(sendBlockNum,sendBlockNum/sendBlockNum*100))
print('总发送块:\t\t\t\t{}\t\t{}%\n'.format(blockSentNum,blockSentNum/sendBlockNum*100))
print('总接收块:\t\t\t\t{}\t\t{}%\n'.format(recvBlock,recvBlock/sendBlockNum*100))
print('所有块按时完成率:\t\t\t{}\t\t{}%\n'.format(recvBlock-lateBlock,(recvBlock-lateBlock)/sendBlockNum*100))
print('高优先级块按时完成率:\t\t\t{}\t\t{}%\n'.format(highPriNum,100*(highPriNum-lateHighPri)/highPriNum))
print('所有块平均完成时间:\t\t\t{}ms\t\t\n'.format(round(totalBct/recvBlock,2)))

os.system('rm '+filename)

