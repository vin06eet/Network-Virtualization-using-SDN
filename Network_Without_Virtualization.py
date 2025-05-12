#!/usr/bin/python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel

class NonSDNTopo(Topo):
    
    def build(self):
        # Add switches - using OVSSwitch in standalone mode (no controller)
        s1 = self.addSwitch('s1', cls=OVSSwitch, failMode='standalone')
        s2 = self.addSwitch('s2', cls=OVSSwitch, failMode='standalone')
        
        # Add hosts
        h1 = self.addHost('h1', ip='10.0.0.1/24')
        h2 = self.addHost('h2', ip='10.0.0.2/24')
        h3 = self.addHost('h3', ip='10.0.0.3/24')
        h4 = self.addHost('h4', ip='10.0.0.4/24')
        
        # Add links between hosts and switches
        self.addLink(h1, s1)
        self.addLink(h2, s1)
        self.addLink(h3, s2)
        self.addLink(h4, s2)
        
        # Connect the switches
        self.addLink(s1, s2)

def runTopo():
    """
    Create and test the network topology
    """
    setLogLevel('info')
    topo = NonSDNTopo()
    net = Mininet(topo=topo)
    net.start()
    CLI(net)
    net.stop()

if __name__ == '__main__':
    runTopo()
