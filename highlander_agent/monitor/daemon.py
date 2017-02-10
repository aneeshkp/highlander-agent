import atexit
import os
import sys
import time
from signal import SIGKILL

from highlander_agent.common import log
from highlander_agent.common.constants import Constant
from highlander_agent.common.util import InstanceConfigUtil

LOGGER = log.getLogger(Constant.LOGGER_MONITOR)


# logging.debug('This message should go to the log file')
# logging.info('So should this')
# logging.warning('And this, too')

class HighlanderMonitorDaemon:
    """
        A generic daemon class.
        Usage: subclass the Daemon class and override the run() method
    """
    startmsg = "RPC server started with pid %s"
    """
       A generic daemon class.

       Usage: subclass the Daemon class and override the run() method
       """

    def __init__(self, pidfile, instance_configuration_json, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile
        self._instance_configuration_json = instance_configuration_json
        if instance_configuration_json is not None:
            self._monitor_types, self._instance_id_to_monitor, self._instance_on_fail_event, self._instance_on_ok_event, self._network_on_fail_event, self._network_on_ok_event, self._instances, self._hypervisor_to_monitor = InstanceConfigUtil.prase_instanceconfig(
                self._instance_configuration_json)

    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """

        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)

        except OSError, e:
            LOGGER.info("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            print "fork #1 failed: %d (%s)\n" % (e.errno, e.strerror)
            sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(2)

        # decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError, e:
            LOGGER.info("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            print "fork #2 failed: %d (%s)\n" % (e.errno, e.strerror)
            sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(3)

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # write pidfile
        atexit.register(self.delpid)
        pid = str(os.getpid())
        file(self.pidfile, 'w+').write("%s\n" % pid)

    def delpid(self):
        os.remove(self.pidfile)

    def start(self):
        """
        Start the daemon
        """
        # Check for a pidfile to see if the daemon already runs
        try:
            pf = file(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError, e:
            LOGGER.info("IO Error failed: %d (%s)\n" % (e.errno, e.strerror))
            pid = None

        if pid:
            message = "pidfile %s already exist. Daemon already running?\n"
            sys.stderr.write(message % self.pidfile)
            LOGGER.info(message % self.pidfile)
            sys.exit(5)

        # Start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """
        Stop the daemon
        """
        try:
            # Get the pid from the pidfile
            try:
                pf = file(self.pidfile, 'r')
                pid = int(pf.read().strip())
                pf.close()
            except IOError:
                pid = None

            if not pid:
                message = "pidfile %s does not exist. Daemon not running?\n" % self.pidfile
                sys.stderr.write(message)
                return  # not an error in a restart

            # Try killing the daemon process
            try:
                while 1:
                    os.kill(pid, SIGKILL)
                    time.sleep(0.1)
            except OSError, err:
                err = str(err)
                if err.find("No such process") > 0:
                    if os.path.exists(self.pidfile):
                        os.remove(self.pidfile)
                else:
                    print str(err)
                    sys.exit(1)
        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()[:]
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            LOGGER.error("Failed to stop daemon: %s, %s, %s" % (exc_type, fname, exc_tb.tb_lineno))

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()

    def run(self):
        """
        You should override this method when you subclass Daemon. It will be called after the process has been
        daemonized by start() or restart().
        """

    def build_dic(self, seq, key):
        instance_item = next((item for item in seq if item['id'] == key), None)
        return instance_item
