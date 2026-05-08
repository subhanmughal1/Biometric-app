import psutil
import ipaddress
import subprocess
import concurrent.futures
import re
import socket
import sys

class Network():

    @staticmethod
    def _get_default_gateway_windows():
        try:
            output = subprocess.check_output(["route", "print", "-4"], text=True, errors="ignore")
        except Exception:
            return None, None

        # Look for default route: Network Destination 0.0.0.0, Netmask 0.0.0.0
        # Example line:
        # 0.0.0.0          0.0.0.0      192.168.1.1    192.168.1.100     25
        for line in output.splitlines():
            line = line.strip()
            if not line or not line.startswith("0.0.0.0"):
                continue
            parts = re.split(r"\s+", line)
            if len(parts) >= 5 and parts[0] == "0.0.0.0" and parts[1] == "0.0.0.0":
                gateway_ip = parts[2]
                interface_ip = parts[3]
                return gateway_ip, interface_ip

        return None, None

    @staticmethod
    def _get_default_gateway_linux():
        try:
            output = subprocess.check_output(["ip", "route", "show", "default"], text=True, errors="ignore")
        except Exception:
            return None, None

        # Example: default via 192.168.1.1 dev wlan0 proto dhcp metric 600
        for line in output.splitlines():
            line = line.strip()
            if not line.startswith("default"):
                continue
            m_gw = re.search(r"\bvia\s+(\d+\.\d+\.\d+\.\d+)", line)
            m_dev = re.search(r"\bdev\s+(\S+)", line)
            gateway_ip = m_gw.group(1) if m_gw else None
            interface_name = m_dev.group(1) if m_dev else None
            return gateway_ip, interface_name

        return None, None

    @staticmethod
    def _get_default_gateway_darwin():
        try:
            output = subprocess.check_output(["route", "-n", "get", "default"], text=True, errors="ignore")
        except Exception:
            return None, None

        # Parse lines like:
        # gateway: 192.168.1.1
        # interface: en0
        gateway_ip = None
        interface_name = None
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("gateway:"):
                gateway_ip = line.split(":", 1)[1].strip()
            elif line.startswith("interface:"):
                interface_name = line.split(":", 1)[1].strip()

        return gateway_ip, interface_name

    @staticmethod
    def _get_default_gateway_any():
        if sys.platform == "win32":
            gateway_ip, interface_ip = Network._get_default_gateway_windows()
            return gateway_ip, interface_ip
        if sys.platform.startswith("linux"):
            return Network._get_default_gateway_linux()
        if sys.platform == "darwin":
            return Network._get_default_gateway_darwin()
        return None, None
    
    # get default gateway ip : return ip
    @staticmethod
    def get_default_gateway_ip():
        gateway_ip, _ = Network._get_default_gateway_any()
        return gateway_ip
    
    # get default gateway : return ip,interface,range
    @staticmethod
    def get_default_gateway():
        gateway_ip, interface_ref = Network._get_default_gateway_any()
        if not gateway_ip or not interface_ref:
            return None, None, None

        # Windows returns interface IP; Linux/macOS returns interface name
        interface_name = None
        interface_ip = None
        subnet_mask = None

        addrs = psutil.net_if_addrs()
        if sys.platform == "win32":
            interface_ip = interface_ref
            for name, snics in addrs.items():
                for snic in snics:
                    if snic.family == socket.AF_INET and snic.address == interface_ip:
                        interface_name = name
                        subnet_mask = snic.netmask
                        break
                if interface_name:
                    break
        else:
            interface_name = interface_ref
            for snic in addrs.get(interface_name, []):
                if snic.family == socket.AF_INET:
                    interface_ip = snic.address
                    subnet_mask = snic.netmask
                    break

        if not interface_name or not interface_ip or not subnet_mask:
            return gateway_ip, interface_name, None

        ip_interface = ipaddress.IPv4Interface(f"{interface_ip}/{subnet_mask}")
        network_range = ip_interface.network
        return gateway_ip, interface_name, network_range

    # scan the default gateway for active ips
    @staticmethod
    def scan():
        _, _, network_range = Network.get_default_gateway()
        if not network_range:
            return []

        try:
            network_obj = ipaddress.IPv4Network(network_range, strict=False)
        except Exception:
            return []

        all_ips = list(network_obj.hosts())

        # Use ThreadPoolExecutor to parallelize pinging IPs
        with concurrent.futures.ThreadPoolExecutor(max_workers=60) as executor:
            results = executor.map(Network.ping_ip, [str(ip) for ip in all_ips])

        # Filter out None values (inactive IPs)
        return [ip for ip in results if ip is not None]


    # Ping an IP address silently
    @staticmethod
    def ping_ip(ip):
        # Use the system's ping command to check if the IP is alive
        try:
            if sys.platform == "win32":
                cmd = ["ping", ip, "-n", "1", "-w", "300"]
            elif sys.platform == "darwin":
                # macOS ping uses -W in milliseconds
                cmd = ["ping", "-c", "1", "-W", "1000", ip]
            else:
                # Linux ping uses -W in seconds
                cmd = ["ping", "-c", "1", "-W", "1", ip]

            if sys.platform == "win32":
                response = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,  # Suppress stdout
                    stderr=subprocess.PIPE,  # Suppress stderr
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=1,
                )
            else:
                response = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,  # Suppress stdout
                    stderr=subprocess.PIPE,  # Suppress stderr
                    timeout=1,
                )
            # Return the IP if active, else None
            return ip if response.returncode == 0 else None
        except Exception as e:
            # Handle exceptions (e.g., invalid IP format or subprocess errors)
            return None
        

    # ping an ip address
    @staticmethod
    def ping_ip_old(ip):
        # it should be silent
        # Use the system's ping command to check if the IP is alive
        response = subprocess.run(
            # ["ping", "-c", "1", "-w", "1", ip],
            ["ping", ip, "-n", "1", "-w", "1000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        # print(str(ip)+'ping response: '+str(response.returncode))
        return ip if response.returncode == 0 else None  #Return IP if active, else None

