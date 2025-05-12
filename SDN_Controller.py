from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, vlan, ipv4, ether_types
from ryu.lib import mac

class VLANAwareSwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    # VLAN to subnet mapping for inter-VLAN routing
    VLAN_TO_SUBNET = {
        10: '10.0.1.0/24',
        20: '10.0.2.0/24'
    }

    def __init__(self, *args, **kwargs):
        super(VLANAwareSwitch, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        # Virtual router MAC - will be used for inter-VLAN routing
        self.virtual_router_mac = '00:00:00:00:00:01'
        self.ip_to_mac = {}  # Dictionary to store IP to MAC mappings

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        # Install table-miss flow entry
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
  mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        dpid = datapath.id

        pkt = packet.Packet(data=msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        
        # Ignore LLDP packets
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        # Extract VLAN tags
        vlan_header = None
        for p in pkt:
            if isinstance(p, vlan.vlan):
                vlan_header = p
                break
        
vlan_id = vlan_header.vid if vlan_header else None
        
        # Initialize mac_to_port tables if needed
        self.mac_to_port.setdefault(dpid, {})
        if vlan_id is not None:
            self.mac_to_port[dpid].setdefault(vlan_id, {})
        else:
            # Handle untagged packets for trunk ports
            self.mac_to_port[dpid].setdefault(0, {})  # 0 = untagged
        
        # Learn MAC address
        if vlan_id is not None:
            self.mac_to_port[dpid][vlan_id][eth.src] = in_port
        else:
            self.mac_to_port[dpid][0][eth.src] = in_port
        
        # Learn IP to MAC mapping if this is an IP packet
        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        if ip_pkt:
            self.ip_to_mac[ip_pkt.src] = eth.src
            self.logger.info(f"Learned IP-MAC mapping: {ip_pkt.src} -> {eth.src}")
            
            # If this is a packet to a different VLAN, handle inter-VLAN routing
            if vlan_id is not None and self.is_inter_vlan_destination(ip_pkt.dst, vlan_id):
                self.handle_inter_vlan_routing(datapath, pkt, eth, ip_pkt, vlan_id, in_port)
                return
        
      # Normal intra-VLAN forwarding
        self.logger.info(f"Packet in s{dpid}: src={eth.src} dst={eth.dst} in_port={in_port} vlan={vlan_id}")
        
        # If we know where the destination MAC is, forward there
        # Otherwise, flood within the VLAN
        if vlan_id is not None and eth.dst in self.mac_to_port[dpid][vlan_id]:
            out_port = self.mac_to_port[dpid][vlan_id][eth.dst]
        elif vlan_id is None and eth.dst in self.mac_to_port[dpid][0]:
            out_port = self.mac_to_port[dpid][0][eth.dst]
        else:
            out_port = ofproto.OFPP_FLOOD
        
        actions = []
        
        # If we're flooding, make sure we only flood within the same VLAN
        if out_port == ofproto.OFPP_FLOOD:
            # We need to identify all ports in the same VLAN
            vlan_ports = set()
            for mac_addr, port in self.mac_to_port[dpid].get(vlan_id, {}).items():
                vlan_ports.add(port)
            
            # Send to each port in the VLAN except the input port
            for port in vlan_ports:
                if port != in_port:
                    actions = [parser.OFPActionOutput(port)]
                    out = parser.OFPPacketOut(
                        datapath=datapath,
                        buffer_id=ofproto.OFP_NO_BUFFER,
                        in_port=in_port,
                        actions=actions,
                        data=msg.data)
                    datapath.send_msg(out)
            
            # For trunk ports, forward with VLAN tag intact
            for mac_addr, port in self.mac_to_port[dpid].get(0, {}).items():
                if port != in_port:
                    # We assume trunk ports are in VLAN 0 (untagged)
                    actions = [parser.OFPActionOutput(port)]
                    out = parser.OFPPacketOut(
                        datapath=datapath,
                        buffer_id=ofproto.OFP_NO_BUFFER,
                        in_port=in_port,
                        actions=actions,
                        data=msg.data)
                    datapath.send_msg(out)
            
            return
        
        # Forward to a single port
        actions = [parser.OFPActionOutput(out_port)]
  # Install flow for future packets if we're not flooding
        if out_port != ofproto.OFPP_FLOOD:
            if vlan_id is not None:
                match = parser.OFPMatch(
                    in_port=in_port,
                    eth_dst=eth.dst,
                    vlan_vid=(ofproto.OFPVID_PRESENT | vlan_id))
            else:
                match = parser.OFPMatch(
                    in_port=in_port,
                    eth_dst=eth.dst)
            
            self.add_flow(datapath, 1, match, actions)
        
        # Send the packet out
        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=ofproto.OFP_NO_BUFFER,
            in_port=in_port,
            actions=actions,
            data=msg.data)
        datapath.send_msg(out)

    def is_inter_vlan_destination(self, ip_dst, src_vlan_id):
        """Determine if the destination IP is in a different VLAN"""
        # Find which VLAN the destination IP belongs to
        dst_vlan = None
        for vlan_id, subnet in self.VLAN_TO_SUBNET.items():
            if self.is_ip_in_subnet(ip_dst, subnet):
                dst_vlan = vlan_id
                break
        
        # If destination VLAN is different from source VLAN, it's inter-VLAN
        return dst_vlan is not None and dst_vlan != src_vlan_id
    
    def is_ip_in_subnet(self, ip, subnet):
        """Check if an IP is in the given subnet"""
        network, bits = subnet.split('/')
        bits = int(bits)
        
        # Convert IP and network to integers
        ip_int = self.ip_to_int(ip)
        net_int = self.ip_to_int(network)
        
        # Create mask based on prefix length
        mask = (0xFFFFFFFF << (32 - bits)) & 0xFFFFFFFF
        
        # Apply mask and compare
        return (ip_int & mask) == (net_int & mask)
 
    def ip_to_int(self, ip):
        """Convert IP address to integer"""
        octets = ip.split('.')
        return int(octets[0]) << 24 | int(octets[1]) << 16 | int(octets[2]) << 8 | int(octets[3])
    
    def handle_inter_vlan_routing(self, datapath, pkt, eth, ip_pkt, src_vlan_id, in_port):
        """Handle inter-VLAN routing"""
        self.logger.info(f"Inter-VLAN routing: src={ip_pkt.src} dst={ip_pkt.dst} from VLAN {src_vlan_id}")
        
        # Determine destination VLAN
        dst_vlan_id = None
        for vlan_id, subnet in self.VLAN_TO_SUBNET.items():
            if self.is_ip_in_subnet(ip_pkt.dst, subnet):
                dst_vlan_id = vlan_id
                break
        
        if dst_vlan_id is None:
            self.logger.error(f"Could not determine destination VLAN for IP {ip_pkt.dst}")
            return
        
        self.logger.info(f"Routing from VLAN {src_vlan_id} to VLAN {dst_vlan_id}")
        
        # Find destination MAC address
        dst_mac = self.ip_to_mac.get(ip_pkt.dst)
        if dst_mac is None:
            self.logger.error(f"Unknown MAC for IP {ip_pkt.dst}, cannot route")
            
            # Flood to all ports in the destination VLAN
            self.flood_to_vlan(datapath, pkt, dst_vlan_id, in_port, src_vlan_id)
            return
        
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        dpid = datapath.id
        
        # Find the output port for the destination MAC in destination VLAN
        out_port = None
        if dst_vlan_id in self.mac_to_port[dpid] and dst_mac in self.mac_to_port[dpid][dst_vlan_id]:
            out_port = self.mac_to_port[dpid][dst_vlan_id][dst_mac]
        
        if out_port is None:
            self.logger.error(f"Unknown port for MAC {dst_mac} in VLAN {dst_vlan_id}, cannot route")
            return
        
        # Create actions for inter-VLAN routing:
        # 1. Pop the source VLAN tag
        # 2. Push the destination VLAN tag
        # 3. Set destination MAC
        # 4. Output to the destination port
        actions = [
 parser.OFPActionPopVlan(),
            parser.OFPActionPushVlan(ether_types.ETH_TYPE_8021Q),
            parser.OFPActionSetField(vlan_vid=(ofproto.OFPVID_PRESENT | dst_vlan_id)),
            parser.OFPActionSetField(eth_dst=dst_mac),
            parser.OFPActionOutput(out_port)
        ]
        
        # Update packet data
        data = pkt.data
        
        # Send packet out
        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=ofproto.OFP_NO_BUFFER,
            in_port=in_port,
            actions=actions,
            data=data)
        datapath.send_msg(out)
        
        # Install flow for future packets
        match = parser.OFPMatch(
            in_port=in_port,
            eth_type=ether_types.ETH_TYPE_IP,
            ipv4_dst=ip_pkt.dst,
            vlan_vid=(ofproto.OFPVID_PRESENT | src_vlan_id))
        
        self.add_flow(datapath, 2, match, actions)  # Higher priority than regular flows
    
    def flood_to_vlan(self, datapath, pkt, dst_vlan_id, in_port, src_vlan_id):
        """Flood packet to all ports in the destination VLAN"""
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        dpid = datapath.id
        
        # Get all ports in the destination VLAN
        vlan_ports = set()
        for mac, port in self.mac_to_port[dpid].get(dst_vlan_id, {}).items():
            vlan_ports.add(port)
        
        # Also include trunk ports
        for mac, port in self.mac_to_port[dpid].get(0, {}).items():
            vlan_ports.add(port)
        
        # Flood to all ports in destination VLAN except input port
        for port in vlan_ports:
            if port != in_port:
                actions = [
                    parser.OFPActionPopVlan(),
                    parser.OFPActionPushVlan(ether_types.ETH_TYPE_8021Q),
                    parser.OFPActionSetField(vlan_vid=(ofproto.OFPVID_PRESENT | dst_vlan_id)),
                    parser.OFPActionOutput(port)
                ]
                
                out = parser.OFPPacketOut(
                    datapath=datapath,
                    buffer_id=ofproto.OFP_NO_BUFFER,
                    in_port=in_port,
                    actions=actions,
                    data=pkt.data)
                datapath.send_msg(out)




