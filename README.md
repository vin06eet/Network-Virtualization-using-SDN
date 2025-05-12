# SDN-based OpenFlow Virtualization of 5G Networks

## About the Project
  The main aim of this project is to demonstrate the working of 5G Network Virtualization using Software Defined Networking (SDN) Controllers. This approach represents a significant evolution from traditional network architecture. In conventional networking systems, the control plane (which makes decisions about where traffic is sent) and the data plane (which forwards traffic to the selected destination) are tightly integrated within the network devices, such as routers and switches. However, in SDN, these two planes are decoupled, which brings flexibility, programmability, and centralized control to the network.<br><br>
In SDN-enabled networks, the control layer is handled by an SDN controller, which is a centralized software program that manages the flow of data across the network. The forwarding layer is managed by virtual switches such as Open vSwitch (OVS). These virtual switches are not responsible for making routing decisions themselves. Instead, they communicate with the SDN controller via well-defined APIs like OpenFlow, which allows the controller to push flow rules to the switches dynamically.<br><br>
For this project, we have chosen the following tools to simulate a virtualized 5G environment:<br>
1. <b>Ryu:</b> An open-source, component-based SDN controller written in Python. It provides a clean interface to interact with OpenFlow-enabled switches.<br>
2. <b>Mininet:</b> A network emulator that allows rapid prototyping of software-defined networks by simulating virtual hosts, switches, links, and controllers.<br>
3. <b>Open vSwitch:</b> A multilayer virtual switch designed to enable massive network automation while supporting standard management interfaces and protocols.<br>
4. <b>OpenFlow:</b> A communications protocol that gives access to the forwarding plane of a switch or router over the network.<br><br>
Since these tools are designed to run on Linux systems, we utilize Multipass, a lightweight virtual machine, to spin up an Ubuntu VM on macOS.<br>

### SDN Flow Logic
One of the central ideas in SDN is that the switch does not make forwarding decisions. When a packet arrives at a switch and it does not have a corresponding flow rule in its flow table, it sends the packet to the controller. The controller then evaluates the packet’s header fields — such as source/destination IP, protocol, or port number — and determines the appropriate action (e.g., forward to a particular port, drop, or modify). It then sends back the action to the switch and installs the flow rule in the switch’s flow table for future matching. This process greatly reduces decision-making latency for recurring traffic and enhances performance.<br><br>
Flow rules enable the controller to dictate how traffic should flow through the network, which is useful for implementing network policies, Quality of Service (QoS), and traffic engineering. Moreover, the SDN controller can also learn and store MAC addresses dynamically, improving efficiency in Layer 2 forwarding.<br>

### Virtualization in 5G Networks
While the SDN controller manages traffic within a single control domain, network virtualization enables the creation of multiple isolated virtual networks on top of a shared physical infrastructure. This is especially critical in 5G networks, where different types of services — such as video streaming, voice calls, IoT connectivity, and mission-critical communications — may coexist but require different performance, security, and control characteristics.<br>

Using SDN, we can assign different flow rules and control logic to different virtual slices of the network. These slices function like Virtual LANs (VLANs), but on a more advanced and scalable level. For instance:<br>
1. One slice could handle voice traffic with low latency.<br>
2. Another could manage high-bandwidth applications like video streaming.<br>
3. Yet another slice might serve IoT devices with lightweight but highly reliable communication needs.<br><br>

This kind of network slicing is fundamental to 5G architecture, allowing network operators to deliver customized experiences for various use cases — from autonomous vehicles to smart cities.<br><br>
In our project, we mimic this concept by creating multiple isolated networks within the same Mininet topology, each governed by a common controller but with independent flow rules and communication constraints. These isolated environments do not communicate unless explicitly configured to do so via trunking protocols, enhancing network security and ensuring that traffic from one virtual slice does not interfere with another.<br><br>















