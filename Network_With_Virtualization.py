#!/usr/bin/python

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info

def build_topology():
    # Create a Mininet instance with our preferred parameters
    net = Mininet(controller=RemoteController, switch=OVSSwitch, link=TCLink)
    
    # Set up a remote controller pointing to the Ryu controller
    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
    
    # Add Hosts
    # Virtual Network 1: VLAN 10 (10.0.1.x)
    h1 = net.addHost('h1', ip='10.0.1.1/24', mac='00:00:00:00:01:01')
    h2 = net.addHost('h2', ip='10.0.1.2/24', mac='00:00:00:00:01:02')
    
    # Virtual Network 2: VLAN 20 (10.0.2.x)
    h3 = net.addHost('h3', ip='10.0.2.1/24', mac='00:00:00:00:02:01')
    h4 = net.addHost('h4', ip='10.0.2.2/24', mac='00:00:00:00:02:02')
    
    # Add Two Switches for segmentation
    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')
    
    # Create links between hosts and switches
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(h3, s2)
    net.addLink(h4, s2)
    
    # Connect the two switches together
    net.addLink(s1, s2)
    
    net.start()
    
    # Configure OVS to mark ports with VLAN tags
    info("Setting VLAN tags on switches...\n")
    
    # On s1: Set VLAN tag 10 on ports connecting to h1 and h2
    s1.cmd("ovs-vsctl set port s1-eth1 tag=10")
    s1.cmd("ovs-vsctl set port s1-eth2 tag=10")
    
    # On s2: Set VLAN tag 20 on ports connecting to h3 and h4
    s2.cmd("ovs-vsctl set port s2-eth1 tag=20")
    s2.cmd("ovs-vsctl set port s2-eth2 tag=20")
    
    # Configure trunk ports (links between switches)
 # These ports will carry traffic for all VLANs
    s1.cmd("ovs-vsctl clear port s1-eth3 tag")  # Clear any VLAN tags
    s1.cmd("ovs-vsctl set port s1-eth3 trunks=10,20")  # Set as trunk for VLANs 10 and 20
    
    s2.cmd("ovs-vsctl clear port s2-eth3 tag")  # Clear any VLAN tags
    s2.cmd("ovs-vsctl set port s2-eth3 trunks=10,20")  # Set as trunk for VLANs 10 and 20
    
    # Make sure the hosts know about each other
    # This is critical for inter-VLAN routing to work!
    # Add static ARP entries
    h1.cmd("arp -s 10.0.1.2 00:00:00:00:01:02")  # h1 -> h2
    h1.cmd("arp -s 10.0.2.1 00:00:00:00:02:01")  # h1 -> h3
    h1.cmd("arp -s 10.0.2.2 00:00:00:00:02:02")  # h1 -> h4
    
    h2.cmd("arp -s 10.0.1.1 00:00:00:00:01:01")  # h2 -> h1
    h2.cmd("arp -s 10.0.2.1 00:00:00:00:02:01")  # h2 -> h3
    h2.cmd("arp -s 10.0.2.2 00:00:00:00:02:02")  # h2 -> h4
    
    h3.cmd("arp -s 10.0.1.1 00:00:00:00:01:01")  # h3 -> h1
    h3.cmd("arp -s 10.0.1.2 00:00:00:00:01:02")  # h3 -> h2
    h3.cmd("arp -s 10.0.2.2 00:00:00:00:02:02")  # h3 -> h4
    
    h4.cmd("arp -s 10.0.1.1 00:00:00:00:01:01")  # h4 -> h1
    h4.cmd("arp -s 10.0.1.2 00:00:00:00:01:02")  # h4 -> h2
    h4.cmd("arp -s 10.0.2.1 00:00:00:00:02:01")  # h4 -> h3
    
    # Configure host routing options
    # Each host needs to know how to route to other VLANs
    # We're using direct routes instead of default gateways
    
    h1.cmd("ip route add 10.0.2.0/24 dev h1-eth0")  # Route to VLAN 20 subnet
    h2.cmd("ip route add 10.0.2.0/24 dev h2-eth0")  # Route to VLAN 20 subnet
    h3.cmd("ip route add 10.0.1.0/24 dev h3-eth0")  # Route to VLAN 10 subnet
    h4.cmd("ip route add 10.0.1.0/24 dev h4-eth0")  # Route to VLAN 10 subnet
    
    # Optional: Verify OVS configuration
    info("\nSwitch s1 configuration:\n")
    info(s1.cmd("ovs-vsctl show"))
    info("\nSwitch s2 configuration:\n")
    info(s2.cmd("ovs-vsctl show"))
    
    # Verify host configuration
    info("\nHost ARP tables:\n")
    info("h1: " + h1.cmd("arp -n"))
    info("h3: " + h3.cmd("arp -n"))
    
    info("\nHost routing tables:\n")
    info("h1: " + h1.cmd("ip route"))
    info("h3: " + h3.cmd("ip route"))
    
 info("\nTesting connectivity between hosts in different VLANs:\n")
    info("h1 (VLAN 10) pinging h3 (VLAN 20)...\n")
    info(h1.cmd("ping -c 2 10.0.2.1"))
    
    # Launch CLI for interactive tests
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    build_topology()


