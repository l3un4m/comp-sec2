"""
Custom topology for the LINFO2347 - Computer System Security course.

Mimics a small enterprise network, with 2 workstations in a trusted LAN,
and service-providing servers in a DMZ LAN.

Adapted from https://stackoverflow.com/questions/46595423/mininet-how-to-create-a-topology-with-two-routers-and-their-respective-hosts
"""

import os
import time
import argparse
from mininet.net import Mininet
from mininet.topo import Topo
from mininet.examples.linuxrouter import LinuxRouter
from mininet.log import setLogLevel, info
from mininet.cli import CLI


class TopoSecu(Topo):
    """
    Custom Mininet topology
    """

    def __init__(self, apply_config=True):
        self.apply_config = apply_config
        Topo.__init__(self)

    def build(self):

        # Add 2 routers in two different subnets
        r1 = self.addHost('r1', cls=LinuxRouter, ip=None)  # Workstation LAN router
        r2 = self.addHost('r2', cls=LinuxRouter, ip=None)  # Internet router

        # Add 2 switches
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')

        # Add router-switch links in the same subnet
        self.addLink(s1, r1, intfName2='r1-eth0', params2={'ip': '10.1.0.1/24'})
        self.addLink(s2, r1, intfName2='r1-eth12', params2={'ip': '10.12.0.1/24'})
        self.addLink(s2, r2, intfName2='r2-eth12', params2={'ip': '10.12.0.2/24'})

        # Add outside host
        internet = self.addHost(name='internet', ip='10.2.0.2/24', defaultRoute='via 10.2.0.1')
        self.addLink(internet, r2, intfName2='r2-eth0', params2={'ip': '10.2.0.1/24'})

        # Adding hosts specifying the default route
        ws2 = self.addHost(name='ws2', ip='10.1.0.2/24', defaultRoute='via 10.1.0.1')
        ws3 = self.addHost(name='ws3', ip='10.1.0.3/24', defaultRoute='via 10.1.0.1')
        httpServer = self.addHost(name='http', ip='10.12.0.10/24', defaultRoute='via 10.12.0.2')
        dnsServer = self.addHost(name='dns', ip='10.12.0.20/24', defaultRoute='via 10.12.0.2')
        ntpServer = self.addHost(name='ntp', ip='10.12.0.30/24', defaultRoute='via 10.12.0.2')
        ftpServer = self.addHost(name='ftp', ip='10.12.0.40/24', defaultRoute='via 10.12.0.2')

        # Add host-switch links
        self.addLink(ws2, s1)
        self.addLink(ws3, s1)
        self.addLink(httpServer, s2)
        self.addLink(dnsServer, s2)
        self.addLink(ntpServer, s2)
        self.addLink(ftpServer, s2)


topos = {
    "secu": ( lambda: TopoSecu() )
}


def add_routes(net):
    ### STATIC ROUTES ###
    info(net['r1'].cmd("ip route add 10.2.0.0/24 via 10.12.0.2 dev r1-eth12"))
    info(net['r2'].cmd("ip route add 10.1.0.0/24 via 10.12.0.1 dev r2-eth12"))


def firewall(net, host, rules):
    """
    Applying Firewalls
    """
    if os.path.exists(rules):
        info(f"Applying {rules} in {host}\n")
        net[host.name].cmd(f'nft -f {rules}')
    else:
        info(f"{rules} not found!\n")
def start_services(net: Mininet, apply_config: bool) -> None:
    """
    Start services on servers.
    :param net: Mininet network
    """
    # Apache2 HTTP server
    info(net['http'].cmd("/usr/sbin/apache2ctl -DFOREGROUND &"))
    # dnsmasq DNS server
    info(net['dns'].cmd("/usr/sbin/dnsmasq -k &"))
    # NTP server
    info(net['ntp'].cmd("/usr/sbin/ntpd -d &"))
    # FTP server
    info(net['ftp'].cmd("/usr/sbin/vsftpd &"))

    # SSH server on all servers
    cmd = "/usr/sbin/sshd -D &"
    for host in ['http', 'ntp', 'ftp']:
        info(net[host].cmd(cmd))

        #Firewall
        if apply_config:
            hosts_fw = {
            'r1': '/home/student-linfo2347/Mininet/firewall/r1.nft',
            'r2': '/home/student-linfo2347/Mininet/firewall/r2.nft',
            }
            for host, rules in hosts_fw.items():
                firewall(net, net[host], rules)


def stop_services(net: Mininet) -> None:
    """
    Stop services on servers.
    :param net: Mininet network
    """
    # Apache2 HTTP server
    info(net['http'].cmd("killall apache2"))
    # dnsmasq DNS server
    info(net['dns'].cmd("killall dnsmasq"))
    # OpenNTPd NTP server
    info(net['ntp'].cmd("killall ntpd"))
    # FTP server
    info(net['ftp'].cmd("killall vsftpd"))


def run(apply_config=True):
    topo = TopoSecu(apply_config=apply_config)
    net = Mininet(topo=topo)

    add_routes(net)
    stop_services(net)
    time.sleep(1)
    start_services(net, apply_config)

    net.start()
    CLI(net)
    stop_services(net)
    net.stop()


def ping_all(apply_config=True):
    topo = TopoSecu(apply_config=apply_config)
    net = Mininet(topo=topo)

    add_routes(net)
    stop_services(net)
    start_services(net, apply_config)

    net.start()
    net.pingAll()
    stop_services(net)
    net.stop()


if __name__ == '__main__':

    # Command-line arguments
    parser = argparse.ArgumentParser(
        prog="topo.py",
        description="Mininet topology for the network attacks project of the course LINFO2347."
    )
    # Optional flag -p
    parser.add_argument("-p", "--pingall", action="store_true", help="Perform pingall test")
    parser.add_argument("-no-config", "--no-config", action="store_false", dest="apply_config", default=True, help="Disable applying nftables config")
    # Parse arguments
    args = parser.parse_args()

    setLogLevel('info')


    if args.pingall:
        # Deploy topology, run pingall test, then exit
        ping_all(args.apply_config)
    else:
        # Deploy topology, open CLI
        run(args.apply_config)

