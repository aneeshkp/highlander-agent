import json
import logging
from highlander_agent.rpcserver.endpoint import RPCEndpoint


def callme(body):
    rpcservice = RPCEndpoint(None, None)

    data = body
    method = data["method"]
    arg = data["arg"]
    func = getattr(rpcservice, method)
    response = func(arg)


data = {
    "method": "configure",
    "arg": {"id": "1", "name": "adele"}
}

data2 = {
    "method": "monitor",
    "arg": "4235253236347"
}

#result = callme(data)
#print result
def callme(string):
    print "aa"+ string

def onConnection(string2,callablefn):
    return callablefn(string2)
class baby:
    def ok(self,value):
        return "girl baby" + value

    def daddy(self,value):
         func = getattr(self, "ok")
         if callable(func):
             response = func(value)
         else:
             response = "NoSuchMethod exception occurred"
         return response



logging.basicConfig(format="%(asctime)-15s %(message)s",filename='/tmp/highlander_agent_rpc_server.log', level=logging.DEBUG)
log=logging.getLogger("sddad")
a=baby()
d="{'id='1'}"
print a.daddy(d)
log.info(a.daddy(d))



