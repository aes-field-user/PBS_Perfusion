import requests
import argparse
import logging
from pycomm3 import LogixDriver
from pycomm3.exceptions import CommError, ResponseError
import time
import datetime
import os
import yaml

def getConfig():
    global demo, debug, plcIP, slot, dataTag, scanTime, waitTime, REST_URL, refreshct

    with open("config.yaml", 'r') as yamlfile:
            d = yaml.load(yamlfile, Loader=yaml.FullLoader)
            
    demo        = d['PBS15Alpha']['demo']       # True to disable PLC requests
    plcIP       = d['PBS15Alpha']['plcIP']      # CompactLogix IP address
    slot        = d['PBS15Alpha']['slot']       # target on PLC
    dataTag     = d['PBS15Alpha']['dataTag']    # udt tag on plc
    scanTime    = d['PBS15Alpha']['scanTime']   # seconds        
    waitTime    = d['PBS15Alpha']['waitTime']   # json timeout, seconds      
    REST_URL    = d['PBS15Alpha']['REST_URL']   # web service url - PBS unit
    refreshct   = d['PBS15Alpha']['refreshct']  # refresh config every x cycles
    
def getJSON():
    global jsonFail
    requests.packages.urllib3.disable_warnings()
    try:   #### set or reset jsonFailure attr in UDT based on rest results
        json = requests.get(REST_URL,verify=False, timeout=waitTime).json()
        jsonFail = False
        return json
    except requests.exceptions.RequestException:
        jsonFail = True
        print('PBS connection timeout likely, check VPN connection and URL, and try again')

jsonFail = False
getConfig()
configRefresh = 0
firstConnect = False

if not demo:
    while not firstConnect:
        print('Connecting to PLC: '+plcIP+'/'+slot)
        try:   
            with LogixDriver(plcIP+'/'+slot) as plc:
                print(plc)
                print('')
                print(plc.info) 
                print('')
            time.sleep(scanTime)
            firstConnect = True
        except (CommError, ResponseError):
            print('Can\'t connect to PLC! Check target IP and slot')
            getConfig()
            time.sleep(2)
        
os.system('cls')

while True:
    writingDict = {}
    try:
        res = getJSON()
        if res != None:
            for key in res.keys():
                for key2 in res[key]:
                    newKey = key+'_'+key2
                    value = res[key][key2]
                    writingDict[newKey]=value

        if not demo:
            try:
                with LogixDriver(plcIP+'/'+slot) as AES_CL:

                    #### Signal if json is not returning
                    #### Need to write these two directly instead of via udt because UDT needs entire structure
                    #### or write will fail
                    AES_CL.write(dataTag+'.jsonFailure',jsonFail)
                    #### Invert heartbeat attr to indicate good Python<->PLC exchange
                    hb = AES_CL.read(dataTag+'.exchangeHeartbeat')[1]
                    hb = not hb
                    AES_CL.write(dataTag+'.exchangeHeartbeat',hb)
                    #### update UDT with above values when good so it succeeds
                    writingDict['jsonFailure']=jsonFail
                    writingDict['exchangeHeartbeat']=hb
                    ######################################################################
                    
                    #### Main data write 
                    writeCheck = AES_CL.write(dataTag,writingDict)
                    if writeCheck[3] != None: # Check error on tag write
                        print('\n***'+writeCheck[3])
                    print('Last update at',datetime.datetime.now())
                    ###########################################################################
                    
                    
                    #### Use to read tags 
                    # readUDT = AES_CL.read(dataTag)
                    # for a in readUDT[1].keys():
                        # print(a, readUDT[1][a])
                    #######################################
                    
                    # controllerTags = AES_CL.get_tag_list(program='*') can be used to compare tagDBs
                  
                    #### use for finding bad tag writes
                    # for key in writingDict.keys():
                        # check = AES_CL.write(dataTag.+key, writingDict[key])
                        # print(check)
                        # input('Press Enter to continue...')
                    ###################################################################    

            except CommError:
                print('Can\'t reach PLC, check connection info!')
                
        time.sleep(scanTime)
        configRefresh = configRefresh + 1
        if configRefresh == refreshct:
            getConfig()
            configRefresh = 0
        
        
    except KeyboardInterrupt:
        input('\nPlease close window when complete')
        break
