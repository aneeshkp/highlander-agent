# highlander-agent

##Highlander agent  consiste of 3 server components 
1. RPC server
2. Listener Server
3. NodeJs server

###Setting up higlander agent for openstack cloud.  
On each hypervisor check out the code and run 3 server components  
* git clone https://github.com/aneeshkp/highlander-agent.git  
* edit rabbitmq infomation in the following file  
      * /highlander-agent/highlander_agent/config.cfg  
        ```
        [RabbitMQ]  
        ```  
        ``` 
        username : guest  
        ```  
        ``` 
        secret : guest  
        ```  
        ``` 
        host : 192.xxx.xxx.xx  
        ```  
      Do not change anything else.
* 
 ```
 cd highlander-agent/highlander_agent
 ```
* Run setup to download all dependencies
    ```
     highlander-agent$> python setup.py develop
     ```
* Run RPC server
     ```
     cd cmd  
     ```
     ```
     cmd$> python launch.py -s start  
     ```
* Run listener 
      ```
      cmd$> python launch.py -l start
      ```
* Run Nodejs server for hypervisor heartbeat
      * 
        ```
        cmd$>cd nodejs/hypervisor
        ```
         (nodejs required modules are at node-module directory)
          prerequist : install nodejs and NPM
      * 
        ```
         cmd$>nodejs server.js
        ```
At this point application is ready to test

#####To stop server use -s stop and -l stop 

#Testing
sample instance configuration file is   https://github.com/aneeshkp/highlander-agent/blob/master/highlander_agent/config/rpc_example.json  
##RPC Client  
Use rpc client for debugging or standalone testing, Change instance id in  rpc_example.json if required  

```
cd rpcclient
```
```
rpcclient$> client.py configure
```
This will read configuration from rpc_example.json

```
rpcclient$> client.py getconfig all
```
This will return configuration information back from rpc server.

```
rpcclient$> client.py monitor
```
This will start monitoring  hypervisor,instance and network

```
rpcclient$> client.py stopmonitor
```
This will stop monitoring.


# Measuring time from failure to recovery
Testing was done by deploying UFR package on two compute node and forcing primary to fail via network/process/hypervisor.

		


 **UFR testing**		                                                       

|  Network failure                                |Trial 1 | 	Trial 2  |    
|-------------------------------------------------|:---------:|:------:|  
|**Primary Node**                                 |           |        |  
|Detection to Nofity secondary with Response      | 3 ms	    | 3ms    |  
|**Secondary Node**                               |           |        |     
|Time to recive from Primary after send (RabbitMq)|	32 ms	    |21ms    |  
|Complete Excution of negotiator script 	         | 273ms    |285 ms  |  


|  Instance failure                                |Trial 1  | 
|-------------------------------------------------|:---------:
|**Primary Node**                                 |          |
|Detection to Nofity secondary with Response      | 3 ms	   |
|**Secondary Node**                               |          |
|Time to recive from Primary after send (RabbitMq)|	40 ms	   |
|Complete Excution of negotiator script 	        | 257ms    |




