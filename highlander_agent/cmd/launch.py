import sys
import eventlet
import glob

eventlet.monkey_patch(
    os=True,
    select=True,
    socket=True,
    thread=False if '--use-debugger' in sys.argv else True,
    time=True)

import ConfigParser
import os
import argparse

# If ../highlander_agent/__init__.py exists, add ../ to Python search path, so that
# it will override what happens to be installed in /usr/(local/)lib/python...
POSSIBLE_TOPDIR = os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir, os.pardir, os.pardir))

if os.path.exists(os.path.join(POSSIBLE_TOPDIR, 'highlander_agent', '__init__.py')):
    sys.path.insert(0, POSSIBLE_TOPDIR)

from highlander_agent.engine.default_agent import DefaultAgentService
from highlander_agent.rpc import RpcAPI
from highlander_agent.common.constants import Constant
from highlander_agent.common.util import AgentConfigParser


def launch_rpcserver(cfg, option):
    d = RpcAPI(cfg)

    print "option %s" % option

    if option == 'start':
        print "launching RPC server:"
        print d.launch_rpc_server()
    else:
        print "stopping RPC server:"
        print d.stop_rpc_server()


def launch_allserver(cfg, action, options):
    """
    This doesnt work bcox first daemon kills parent
    :param cfg:
    :param action:
    :param options:
    :return:
    """
    threads = [eventlet.spawn(LAUNCH_OPTIONS[option], cfg, action)
               for option in LAUNCH_OPTIONS.keys()]
    print(action + ' all server.')


def launch_listener(cfg, option):
    d = DefaultAgentService(cfg)
    if option == 'start':
        print "starting listener"
        d.start_listener()
    else:
        print "stopping listener"
        d.stop_listener()


LAUNCH_OPTIONS = {
    'rpcserver': launch_rpcserver,
    'listener': launch_listener

}





def main():
    try:

        parser = argparse.ArgumentParser()
        parser.add_argument("-l", help="listener : -l start or -l stop", dest="listener")
        parser.add_argument("-s", help="server: -s start or -s stop", dest="server")
        parser.add_argument("-a", help="all server: -a start or -a stop", dest="allserver")

        args = parser.parse_args()
        print args.allserver
        print args.listener
        print args.server

        # cfg = ConfigParser.ConfigParser()
        cfg = AgentConfigParser()

        cfg.read(os.path.abspath(os.path.join(os.path.dirname(__file__), '../config.cfg')))
        cfg = cfg.as_dic()

        # launch_rpcserver(ConfigSectionMap("RabbitMQ", cfg), "start")
        # exit(0)
        if args.allserver:
            # this is not working , since daemon process kills parent process

            launch_allserver(cfg, args.allserver, LAUNCH_OPTIONS.keys())
        else:
            if args.listener:
                launch_listener(cfg, args.listener)

            if args.server:
                launch_rpcserver(cfg, args.server)

                # thread = eventlet.spawn(launch_rpcserver, ConfigSectionMap("RabbitMQ", cfg))
        # print "wait"

        exit(0)
    except RuntimeError as excp:
        sys.stderr.write("ERROR: %s\n" % excp)
        sys.exit(1)


if __name__ == '__main__':
    main()
