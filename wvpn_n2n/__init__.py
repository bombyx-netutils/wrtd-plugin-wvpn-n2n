#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import pwd
import grp
import time
import socket
import signal
import logging
import netifaces
import ipaddress
import subprocess
from gi.repository import GLib
from gi.repository import GObject


def get_plugin_list():
    return ["n2n"]


def get_plugin(name):
    if name == "n2n":
        return _PluginObject()
    else:
        assert False


class _PluginObject:

    def init2(self, cfg, tmpDir, upCallback, downCallback):
        self.cfg = cfg
        self.vpnIntfName = "vpnc"
        self.tmpDir = tmpDir
        self.upCallback = upCallback
        self.downCallback = downCallback
        self.logger = logging.getLogger(self.__module__ + "." + self.__class__.__name__)

        self.vpnTimer = None

        self.vpnProc = None
        self.dhcpClientProc = None
        self.localIp = None
        self.remoteIp = None
        self.netmask = None
        self.vpnRestartCountDown = None

    def start(self):
        self.vpnTimer = GObject.timeout_add_seconds(10, self._vpnTimerCallback)

    def stop(self):
        self.vpnRestartCountDown = None

        GLib.source_remove(self.vpnTimer)
        self.vpnTimer = None

        if self.vpnProc is not None:
            self.downCallback()

        self._vpnStop()

    def is_alive(self):
        # VPN is alive so long as self._vpnStop() is not called for other modules
        return self.vpnProc is not None

    def get_local_ip(self):
        return self.localIp

    def get_remote_ip(self):
        return self.remoteIp

    def get_netmask(self):
        return self.netmask

    def get_interface(self):
        return self.vpnIntfName

    def get_prefix_list(self):
        if self.localIp is not None:
            netobj = ipaddress.IPv4Network(self.localIp, self.netmask, False)
            return [(str(netobj.address), str(netobj.netmask))]
        else:
            return None

    def _vpnTimerCallback(self):
        if self.vpnRestartCountDown is None:
            if self._vpnCheck():
                return True
            else:
                # vpn is in bad state, stop it now, restart it in the next cycle
                self._vpnStop()
                self.vpnRestartCountDown = 6
                self.logger.info("VPN disconnected.")
                self.downCallback()
                return True

        if self.vpnRestartCountDown > 0:
            self.vpnRestartCountDown -= 1
            return True

        self.logger.info("Establishing VPN connection.")
        try:
            self._vpnStart()
            self.logger.info("VPN connected.")
            self.upCallback()
        except Exception as e:
            self._vpnStop()
            self.vpnRestartCountDown = 6
            self.logger.error("Failed to establish VPN connection, %s", e)

        return True

    def _vpnStart(self):
        try:
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
        except BaseException:
            self._vpnStop()

    def _vpnStop(self):
        self.netmask = None
        self.remoteIp = None
        self.localIp = None
        if self.dhcpClientProc is not None:
            self.dhcpClientProc.send_signal(signal.SIGINT)      # dhcpClientProc is written in python, kill it gracefully
            self.dhcpClientProc.wait()
            self.dhcpClientProc = None
        if self.vpnProc is not None:
            self.vpnProc.terminate()
            self.vpnProc.wait()
            self.vpnProc = None

    def _vpnCheck(self):
        if self.vpnProc.poll():
            return False
        if self.dhcpClientProc.poll():
            return False
        return True
