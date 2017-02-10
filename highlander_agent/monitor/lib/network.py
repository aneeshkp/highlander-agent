#!/usr/bin/python
""" This application gathers the local machines IP Addresses and their matching
labels.  Thereafter, it will notify, via callback, any IP address changes. """

import socket
import struct
import sys
import thread
import time

from highlander_agent.common import log
from highlander_agent.common.constants import Constant

LOGGER = log.getLogger(Constant.LOGGER_MONITOR)
"""4 byte alignment"""


def align(inc):
    diff = inc % 4
    return inc + ((4 - diff) % 4)


class iflink:
    """Parse an iflink packet"""

    # https://www.kernel.org/doc/Documentation/networking/operstates.txt

    # Routing Attributes for link
    IFLA_UNSPEC = 0
    IFLA_ADDRESS = 1
    IFLA_BROADCAST = 2
    IFLA_IFNAME = 3
    IFLA_MTU = 4
    IFLA_LINK = 5
    IFLA_QDISK = 6
    IFLA_STATS = 7
    IFLA_TXQLEN = 13
    IFLA_OPERSTATE = 16
    IFLA_LINKMODE = 17
    IFLA_LINKINFO = 18
    IFLA_CARRIER = 33
    IFLA_PHYS_PORT_ID = 34

    ifla_map = {
        IFLA_UNSPEC: 'IFLA_UNSPEC',
        IFLA_ADDRESS: 'IFLA_ADDRESS',
        IFLA_BROADCAST: 'IFLA_BROADCAST',
        IFLA_IFNAME: 'IFLA_IFNAME',
        IFLA_MTU: 'IFLA_MTU',
        IFLA_LINK: 'IFLA_LINK',
        IFLA_STATS: 'IFLA_STATS',
        IFLA_OPERSTATE: 'IFLA_OPERSTATE',
        IFLA_LINKMODE: 'IFLA_LINKMODE',
        IFLA_LINKINFO: 'IFLA_LINKINFO',
        IFLA_CARRIER: 'IFLA_CARRIER',
        IFLA_PHYS_PORT_ID: 'IFLA_PHYS_PORT_ID',
        IFLA_TXQLEN: 'IFLA_TXQLEN'
    }

    # Standard interface flags (netdevice->flags).
    IFF_UP = 0x1  # interface is up
    IFF_BROADCAST = 0x2  # broadcast address valid
    IFF_DEBUG = 0x4  # turn on debugging
    IFF_LOOPBACK = 0x8  # is a loopback net
    IFF_POINTOPOINT = 0x10  # interface is has p-p link
    IFF_NOTRAILERS = 0x20  # avoid use of trailers
    IFF_RUNNING = 0x40  # interface RFC2863 OPER_UP
    IFF_NOARP = 0x80  # no ARP protocol
    IFF_PROMISC = 0x100  # receive all packets
    IFF_ALLMULTI = 0x200  # receive all multicast packets

    IFF_MASTER = 0x400  # master of a load balancer
    IFF_SLAVE = 0x800  # slave of a load balancer

    IFF_MULTICAST = 0x1000  # Supports multicast

    IFF_PORTSEL = 0x2000  # can set media type
    IFF_AUTOMEDIA = 0x4000  # auto media select active
    IFF_DYNAMIC = 0x8000  # dialup device with changing addresses

    IFF_LOWER_UP = 0x10000  # driver signals L1 up
    IFF_DORMANT = 0x20000  # driver signals dormant

    IFF_ECHO = 0x40000  # echo sent packets

    iff_map = {
        IFF_UP: 'IFF_UP',
        IFF_BROADCAST: 'IFF_BROADCAST',
        IFF_DEBUG: 'IFF_DEBUG',
        IFF_LOOPBACK: 'IFF_LOOPBACK',
        IFF_POINTOPOINT: 'IFF_POINTOPOINT',
        IFF_NOTRAILERS: 'IFF_NOTRAILERS',
        IFF_RUNNING: 'IFF_RUNNING',
        IFF_NOARP: 'IFF_NOARP',
        IFF_PROMISC: 'IFF_PROMISC',
        IFF_ALLMULTI: 'IFF_ALLMULTI',
        IFF_MASTER: 'IFF_MASTER',
        IFF_SLAVE: 'IFF_SLAVE',
        IFF_MULTICAST: 'IFF_MULTICAST',
        IFF_PORTSEL: 'IFF_PORTSEL',
        IFF_AUTOMEDIA: 'IFF_AUTOMEDIA',
        IFF_DYNAMIC: 'IFF_DYNAMIC',
        IFF_LOWER_UP: 'IFF_LOWER_UP',
        IFF_DORMANT: 'IFF_DORMANT',
        IFF_ECHO: 'IFF_ECHO'
    }

    def get_value_str(self):
        return "family: " + repr(self.family) + " type: " + repr(self.type) + " index: " + \
               repr(self.index) + " flags: " + format(self.flags, 'X')

    #  struct ifinfomsg {
    #         unsigned char   ifi_family;
    #         unsigned char   __ifi_pad;
    #         unsigned short  ifi_type;               /* ARPHRD_* */
    #         int             ifi_index;              /* Link index   */
    #         unsigned        ifi_flags;              /* IFF_* flags  */
    #         unsigned        ifi_change;             /* IFF_* change mask */
    #        };

    def __init__(self, nlmsghdr, packet):
        self.link_up = False;

        self.family, self.pad, self.type, self.index, self.flags, self.change = \
            struct.unpack("BBHiII", packet[:16])

        flag_string = []
        for k in self.iff_map:
            if bool(k & self.flags):
                flag_string.append(self.iff_map[k])

        LOGGER.info("Flags: " + ', '.join(flag_string))

        self.link_up = bool(self.flags & self.IFF_LOWER_UP)

        # The following code parses the attributes attached to the end of the iflink message
        # This info does not need to be read as we already have the interface index and status
        # This is just for reference
        #
        self.payload = None
        self.rtas = {}
        self.pos = 16  # skip the hdr
        while self.pos < nlmsghdr.msglen - 16:  # msglen includes hdr
            try:
                self.len, self.type = struct.unpack("HH", packet[self.pos:self.pos + 4])
                #        if self.type in self.ifla_map:
                #	        print "iflink: type " + self.ifla_map[self.type] + " len " + repr(self.len)
                #        else:
                #          print "iflink: type " + repr(self.type) + " len " + repr(self.len)
                if (self.type == self.IFLA_IFNAME):
                    self.payload = packet[self.pos + 4:self.pos + self.len].strip("\0")
                    LOGGER.info(repr(self.ifla_map[self.type]) + " -> " + repr(self.payload))
                else:
                    self.payload = packet[self.pos + 4:self.len]
            except:
                LOGGER.info("iflink: Unexpected error:", sys.exc_info())
                break

            self.pos += align(self.len)
            self.rtas[self.type] = self.payload


# print repr(self.type) + " -> " + repr(self.payload)

class rtattr:
    """Parse a rtattr packet (NETLINK_ROUTE)"""
    GRP_IPV4_IFADDR = 0x10
    GRP_LINK = 1
    GRP_NOTIFY = 2

    # Defined in /usr/include/linux/rtnetlink.h
    NEWLINK = 16
    DELLINK = 17
    GETLINK = 18
    SETLINK = 19

    NEWADDR = 20
    DELADDR = 21
    GETADDR = 22

    def __init__(self, packet):
        #  struct rtattr {
        #        unsigned short  rta_len;
        #        unsigned short  rta_type;
        #  };
        self.len, self.type = struct.unpack("HH", packet[:4])
        if self.type == ifaddr.LOCAL:
            addr = struct.unpack("BBBB", packet[4:self.len])
            self.payload = "%s.%s.%s.%s" % (addr[0], addr[1], addr[2], addr[3])
        elif self.type == ifaddr.LABEL:
            self.payload = packet[4:self.len].strip("\0")
        else:
            self.payload = packet[4:self.len]


class netlink:
    """Parse a netlink packet"""

    # Flag values
    NLM_F_REQUEST = 1  # must be set on all requests
    NLM_F_MULTI = 2  # part of a multipart message
    NLM_F_ACK = 3  # Request for an acknowledgment on success
    # Modifiers to GET request
    NLM_F_ROOT = 0x100  # Return the complete table instead of a single entry
    NLM_F_MATCH = 0x200  # Return all entries matching criteria passed in message content

    NLMSG_NOOP = 1  # Message is to be ignored
    NLMSG_ERROR = 2  # Payload contains nlmsgerr struct
    NLMSG_DONE = 3  # Terminates a mutlti-part message
    NLMSG_OVERRUN = 4

    def __init__(self, packet):
        # Parse the nlmsghdr structure defined in netlink(7), /usr/include/linux/netlink.h
        #     struct nlmsghdr {
        #        __u32 nlmsg_len;    /* Length of message including header. */
        #        __u16 nlmsg_type;   /* Type of message content. */
        #        __u16 nlmsg_flags;  /* Additional flags. */
        #        __u32 nlmsg_seq;    /* Sequence number. */
        #        __u32 nlmsg_pid;    /* Sender port ID. */
        #     };

        self.msglen, self.msgtype, self.flags, self.seq, self.pid = \
            struct.unpack("IHHII", packet[:16])

        self.pos = 16


class ip_monitor:
    def __init__(self, interfaces_to_monitor, callback=None, ):
        self._interfaces_to_monitor = interfaces_to_monitor
        if callback == None:
            callback = self.print_cb
        self._callback = callback

    def print_cb(self, label, value, interface):
        LOGGER.info(label + " => " + value)

    def request_addrs(self, sock):
        sock.send(struct.pack("IHHIIBBBBI", 24, rtattr.GETADDR, \
                              netlink.REQUEST | netlink.ROOT | netlink.MATCH, 0, sock.getsockname()[0], \
                              socket.AF_INET, 0, 0, 0, 0))

    def start_thread(self):
        thread.start_new_thread(self.run, ())

    def run(self):
        # open the NETLINK socket, raw socket, connect to the NETLINK_ROUTE system
        sock = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, socket.NETLINK_ROUTE)
        # select the GRP_LINK group
        sock.bind((0, rtattr.GRP_LINK))
        # self.request_addrs(sock)
        LOGGER.info("Starting ip monitoring thread")

        while True:
            # blocking read of the NETLINK SOCKET
            data = sock.recv(4096)
            pos = 0
            while pos < len(data):
                # attempt to convert the netlink message
                nl = netlink(data[pos:])
                if nl.msgtype == netlink.NLMSG_DONE:
                    break

                if nl.msgtype == rtattr.NEWLINK:
                    ifl = iflink(nl, data[pos + 16:])
                    if (ifl != None):
                        if repr(ifl.link_up) == "False":
                            if ifl.rtas[3] in self._interfaces_to_monitor:
                                self._callback("Link Up ", repr(ifl.link_up), ifl.rtas[3])
                                time.sleep(10)


                pos += align(nl.msglen)

                # if __name__ == "__main__":
                # ip_monitor().run()
