#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import pwd
import grp
import time
import socket
import signal
import netifaces
import subprocess


def get_plugin_list():
    return ["n2n"]


def get_plugin(name):
    if name == "n2n":
        return _PluginObject()
    else:
        assert False


class _PluginObject:

    def init2(self, cfg, vpnIntfName, tmpDir):
        self.cfg = cfg
        self.vpnIntfName = vpnIntfName
        self.tmpDir = tmpDir

    def start(self):
        self.vpnProc = None
        self.dhcpClientProc = None
        self.localIp = None
        self.remoteIp = None
        self.netmask = None

        # run n2n edge process
        cmd = "/usr/sbin/edge -f "
        cmd += "-l %s " % (self.cfg["supernode"])
        cmd += "-r -a dhcp:0.0.0.0 "
        cmd += "-d %s " % (self.vpnIntfName)
        cmd += "-c %s " % (self.cfg["community"])
        cmd += "-k %s " % (self.cfg["key"])
        cmd += "-u %d -g %d " % (pwd.getpwnam("nobody").pw_uid, grp.getgrnam("nobody").gr_gid)
        cmd += ">%s 2>&1" % (os.path.join(self.tmpDir, "edge.log"))
        self.vpnProc = subprocess.Popen(cmd, shell=True, universal_newlines=True)

        # wait for interface
        i = 0
        while True:
            if self.vpnIntfName not in netifaces.interfaces():
                if i >= 10:
                    raise Exception("Interface allocation time out.")
                time.sleep(1.0)
                i += 1
                continue
            break

        # create dhclient.conf, copied from nm-dhcp-dhclient-utils.c in networkmanager-1.4.4
        cfgf = os.path.join(self.tmpDir, "dhclient.conf")
        with open(cfgf, "w") as f:
            buf = ""
            buf += "send host-name \"%s\";\n" % (socket.gethostname())
            buf += "\n"
            buf += "option rfc3442-classless-static-routes code 121 = array of unsigned integer 8;\n"
            buf += "option wpad code 252 = string;\n"
            buf += "\n"
            buf += "also request rfc3442-classless-static-routes;\n"
            buf += "also request static-routes;\n"
            buf += "also request wpad;\n"
            buf += "also request ntp-servers;\n"
            buf += "\n"
            buf += "supersede routers 0.0.0.0;\n"               # reject, no way to remove an option, it is just a workaround, dhclient sucks
            f.write(buf)

        self.dhcpClientProc = subprocess.Popen([
            "/usr/bin/python3",
            os.path.join(os.path.dirname(os.path.realpath(__file__)), "subproc_dhclient.py"),
            self.tmpDir,
            cfgf,
            self.vpnIntfName,
        ])

        # wait for ip address
        i = 0
        while True:
            t = netifaces.ifaddresses(self.vpnIntfName)
            if 2 not in t:
                if i >= 10:
                    raise Exception("IP address allocation time out.")
                time.sleep(1.0)
                i += 1
                continue
            self.localIp = t[2][0]["addr"]
            self.remoteIp = ".".join(self.localIp.split(".")[:3] + ["1"])         # trick
            self.netmask = t[2][0]["netmask"]
            break

    def stop(self):
        if hasattr(self, "netmask"):
            del self.netmask
        if hasattr(self, "remoteIp"):
            del self.remoteIp
        if hasattr(self, "localIp"):
            del self.localIp
        if hasattr(self, "dhcpClientProc"):
            if self.dhcpClientProc is not None:
                self.dhcpClientProc.send_signal(signal.SIGINT)      # dhcpClientProc is written in python, kill it gracefully
                self.dhcpClientProc.wait()
            del self.dhcpClientProc
        if hasattr(self, "vpnProc"):
            if self.vpnProc is not None:
                self.vpnProc.terminate()
                self.vpnProc.wait()
            del self.vpnProc

    def is_alive(self):
        if not hasattr(self, "vpnProc"):
            return False
        if not hasattr(self, "dhcpClientProc"):
            return False
        if self.vpnProc.poll():
            return False
        if self.dhcpClientProc.poll():
            return False
        return True

    def get_local_ip(self):
        return self.localIp

    def get_remote_ip(self):
        return self.remoteIp

    def get_netmask(self):
        return self.netmask
