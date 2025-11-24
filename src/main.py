#!/usr/bin/env python3
import asyncio
import socket
import sys
import logging
import uuid
import re
import netifaces

from datetime import datetime
from ssdp import aio, messages, network


class MyProtocol(aio.SimpleServiceDiscoveryProtocol):

  @classmethod
  def getTuple(self,headers,key):
    headerdict = dict(headers)
    lowerkeyheaderdict = dict((k.lower(), v) for k,v in headerdict.items())
    if(key.lower() in lowerkeyheaderdict.keys()):
      return(lowerkeyheaderdict[key.lower()])

  @classmethod
  def getUserAgent(self,headers):
     useragent1 = self.getTuple(headers,'user-agent')
     useragent2 = self.getTuple(headers,'user_agent')
     if(useragent1):
      return useragent1
     if(useragent2):
      return useragent2
     return None

  def setLocationPrefix(self,locationPrefix):
     self.__locationPrefix = locationPrefix     

  def setUSNPrefix(self,usnPrefix):
     self.__usnPrefix = usnPrefix

  def setST(self,st):
     self.__st = st
  
  def setTransport(self,transport):
     self.__transport = transport

  def setServices(self,services):
     self.__services = services

  def response_received(self, response, addr):
    logging.info("Response received from {}".format(addr))
    logging.debug("{} {}".format(addr,response))
    headersLC=dict()
    logging.info("Fixed User Agent {}".format(self.getUserAgent(response.headers)))


  def request_received(self, request, addr):
   #logging.info("Request received from {}".format(addr))
   logging.debug("{} {}".format(addr,request))
   headersLC=dict()
   if(re.match('M-SEARCH',str(request).upper())):
      logging.info("Received M-SEARCH from {}".format(addr))
      logging.info(request);
      if(re.search('devolo',str(self.getUserAgent(request.headers)).lower())):
         logging.info("Fixed User Agent {}".format(self.getUserAgent(request.headers)))
         #if(re.search('urn:dslforum-org:device:InternetGatewayDevice:1',str(request))):
         if(1==1):
            logging.info("respoding to urn:dslforum-org:device:InternetGatewayDevice:1")
            response = messages.SSDPResponse(200,'OK',headers={
                                 'CACHE-CONTROL':'max-age=300',
                                 'DATE':datetime.now().strftime('%a, %d %b %Y %X %Z'),
                                 'EXT':'',
                                 'ST':self.getTuple(request.headers,'ST'),
                                 'LOCATION':self.__locationPrefix+"/igddesc.xml",
                                 'USN':self.__usnPrefix,
                                 'SERVER':'PyOS/1 UPnP/2.0 1/0',
            })
            logging.info("%s:%s - - %s", *(addr + (response,)))
            #TODO: add correct service here
            response.sendto(self.__transport,addr=addr)


def get_first_ethernet_ip():
    """
    Returns the IP address of the first Ethernet adapter on macOS.
    
    :return: IP address as a string or None if not found.
    """
    interfaces = netifaces.interfaces()

    for interface in interfaces:
        if interface.startswith('en'):  # Typically, Ethernet interfaces on macOS start with 'en'
            addresses = netifaces.ifaddresses(interface)
            ipv4_info = addresses.get(netifaces.AF_INET)
            if ipv4_info:
                return ipv4_info[0]['addr']

    return None

logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')

#myip=get_first_ethernet_ip()
myip='192.168.178.1'
myport='49000'
if myip:
    logging.info(f"IP Address: {myip}")
else:
    logging.warning("Ethernet IP address not found.")


services = [
   ['upnp:rootdevice','rootdesc.xml'],
   ['urn:schemas-upnp-org:device:InternetGatewayDevice:1','igddesc.xml' ]
]

mac = str(hex(uuid.getnode()))[2:]
uuidstart="020DE842-1F7A-4155-8B02"
ssdpMulticastIP="239.255.255.250"
ssdpPort=1900


#loop = asyncio.get_event_loop()
if sys.version_info < (3, 10):
    loop = asyncio.get_event_loop()
else:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# subscribe to the ssdp multicast domain
mreq = socket.inet_aton(ssdpMulticastIP)
mreq += socket.inet_aton('0.0.0.0')
sock.setsockopt(
  socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq,
)

# bind to all interfaces and port 1900
sock.bind(('0.0.0.0',ssdpPort))
connect = loop.create_datagram_endpoint(MyProtocol, sock=sock)


transport, protocol = loop.run_until_complete(connect)
protocol.setTransport(transport)
protocol.setLocationPrefix("http://"+myip+":"+myport+"/")
protocol.setServices(services)
protocol.setUSNPrefix("uuid:"+uuidstart+"-"+mac+"::")


#notify the network about our capabilities
for service in services:
    notify = messages.SSDPRequest('NOTIFY', headers={'HOST':ssdpMulticastIP+':'+str(ssdpPort),
                                                    'Location':"http://"+myip+":"+myport+"/"+service[1],
                                                    'ST':service[0],
                                                    'USN':"uuid:"+uuidstart+"-"+mac+"::"+service[0],
                                                    'Ext':'',
                                                    'NTS':'ssdp:alive',
        })
    notify.sendto(transport, (network.MULTICAST_ADDRESS_IPV4, network.PORT))

# call everyone (just to be talkative)
#search = messages.SSDPRequest('M-SEARCH', headers={'HOST':'239.255.255.250:1900',
#                                                 'MAN':"ssdp:discover",
#                                                 'ST':'ssdp:all',
#                                                 })
#search.sendto(transport, (network.MULTICAST_ADDRESS_IPV4, network.PORT))


# wait for all others to speak
try:
  loop.run_forever()
except KeyboardInterrupt:
  pass

transport.close()
loop.close()
