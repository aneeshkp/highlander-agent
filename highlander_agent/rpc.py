from highlander_agent.common.constants import Constant
from highlander_agent.rpcserver.default_server import DefaultRPCServer
import glob
import os
from signal import SIGKILL
import time

class RpcAPI:
    def __init__(self, cfg):
        self._cfg = cfg

    def launch_rpc_server(self):
        print "PIDFILE location %s" % self._cfg[Constant.CONFIG_PIDFILE_SECTION]["server"]

        rpcserver = DefaultRPCServer(self._cfg)
        rpcserver.start()
        print 'Server started'

    def stop_rpc_server(self):
        print "PIDFILE location %s" % self._cfg[Constant.CONFIG_PIDFILE_SECTION]["server"]
        # print cfg
        rpcserver = DefaultRPCServer(self._cfg)
        rpcserver.stop()
        self.cleanupallpid()
        print 'Server stopped'


    def cleanupallpid(self):
        """
        read all monitoring pid files
        """
        files=glob.glob(self._cfg["PidFile"]["pid_path"]+"/highlander_monitor*.pid")
        for file in files:
            print "cleaning file %s" % os.path.basename(file)
            try:
                # Get the pid from the pidfile
                try:
                    pf = open(file, 'r')
                    pid = int(pf.read().strip())
                    pf.close()
                except IOError:
                    pid = None

                # Try killing the daemon process
                try:
                    while 1:
                        os.kill(pid, SIGKILL)
                        time.sleep(0.1)
                except OSError, err:
                    err = str(err)
                    if err.find("No such process") > 0:
                        if os.path.exists(file):
                            os.remove(file)
            except Exception, e:
                print e


"""

import ConfigParser
import os
class AgentConfigParser(ConfigParser.ConfigParser):
    def as_dic(self):
        d = dict(self._sections)
        for k in d:
            d[k] = dict(self._defaults, **d[k])
            d[k].pop('__name__', None)
        return d
cfg = AgentConfigParser()
cfg.read(os.path.abspath(os.path.join(os.path.dirname(__file__), 'config.cfg')))
cfg=cfg.as_dic()
a=RpcAPI(cfg)
a.launch_rpc_server()"""

