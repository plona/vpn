#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Options:
[-s | --start]
[-k | --kill]
[-r | --restart]
[-n | --noicon]              - no icon in tray, log to stdout
[-t | --textonly]            - text mode
[-h | --help | <none>]

Configuration in <script_name>.secret, log in <script_name>.log in scripts
home dir.
Attention! Option -t causes writes out full pexpect log (includes username
and password(s)) to stdout.
"""

import getopt
import pexpect
from vpn_lib import *


class openconnect():
    def __init__(self):
        self.__noicon = myVPN.noicon
        self.__textonly = myVPN.textonly
        if self.__textonly:
            self.__logFile = sys.stdout
        else:
            self.__logFile = open(homeDir + "/" + scriptName + ".log", "w")
        myVPN.checkPidFile()
        try:
            self.__vpnServer = myVPN.config.get("vpn", "vpnServer")
            self.__serverCert = myVPN.config.get("vpn", "servercert")
            self.__authGroup = myVPN.config.get("vpn", "authgroup")

            self.__adUser = myVPN.config.get("auth", "adUser")
            self.__adPasswd = myVPN.config.get("auth", "adPasswd")
            self.__tokenPrefix = myVPN.config.get("auth", "tokenPrefix")

            self.__cmd = myVPN.config.get("vpn", "openconnect") + " "
        except:
            msg = "Bad credentials file format"
            self.__logFile.write(msg + ":\n" + traceback.format_exc())
            if not self.__textonly:
                n = notify2.Notification(msg, "Check file: " + scriptName + ".log")
                n.set_urgency(2)
                n.show()
            raise

        # self.__cmd += "--juniper "
        self.__cmd += "--authgroup=" + self.__authGroup + " "
        self.__cmd += "--servercert " + self.__serverCert + " "
        self.__cmd += self.__vpnServer

    def startVPN(self):
        tokenPass = [""]
        myVPN.getTokenPass(tokenPass)
        gtk.main()
        self.__logFile.write("spawning:\n" + self.__cmd + "\n")
        self.__logFile.write(80 * "-" + "\n")
        msg = "Setting up connection " + scriptName
        if not self.__textonly:
            n = notify2.Notification(msg, "", connectingIcon)
            n.set_urgency(0)
            n.show()
        else:
            print msg

        myVPN.sysCmds("preVPNstart")
        try:
            vpn = pexpect.spawn(self.__cmd)
            if self.__textonly:
                vpn.logfile = self.__logFile
            else:
                vpn.logfile_read = self.__logFile

            if 0 == vpn.expect_exact("username:"): vpn.sendline(s=self.__adUser)
            if 0 == vpn.expect_exact("password:"): vpn.sendline(self.__tokenPrefix + tokenPass[0])
            if 0 == vpn.expect_exact("user#2:"): vpn.sendline(self.__adUser)
            if 0 == vpn.expect_exact("password#2:"): vpn.sendline(self.__adPasswd)
            # Ustawienie DTLS się nie powiodło. Używanie SSL zamiast tego
            i = vpn.expect(["DTLS", "SSL"])
            if i in (0, 1):
                # self.startSSHuttle()
                file(homeDir + "/" + scriptName + ".pid", "w").write(str(os.getpid()))
                myVPN.sysCmds("postVPNstart")
                msg = "Connection " + scriptName + " ready"
                if not self.__textonly:
                    n.update(msg, "" if self.__noicon == True else "Right click to close", connectionOKIcon)
                    n.set_urgency(1)
                    n.show()
                    if not self.__noicon :
                        myVPN.set_icon(homeDir + "/" + scriptName + ".png")
                        gtk.main()
                else:
                    print msg
                vpn.wait()

        except pexpect.EOF:
            self.__logFile.write("pexpect: EOF\n")
            if not self.__textonly:
                n.update("pexpect: EOF", "", errorIcon)
        except pexpect.TIMEOUT:
            self.__logFile.write("Connection timeout\n")
            if not self.__textonly:
                n.update("Connection timeout", "", errorIcon)
        except:
            self.__logFile.write("Unhandled error: " + traceback.format_exc())
            if not self.__textonly:
                n.update("Unhandled error", traceback.format_exc(), errorIcon)
            raise
        finally:
            if not self.__textonly:
                n.set_urgency(2)
                n.show()


def main(argv):

    def usage():
        print(globals()['__doc__'])
        sys.exit(2)

    if len(argv) == 0: usage()

    try:
        opts, args = getopt.getopt(argv, "skrnith",
                                   ["start",
                                    "kill",
                                    "restart",
                                    "noicon",
                                    "textonly",
                                    "help"])
    except getopt.GetoptError: usage()

    noicon = textonly = False
    for opt, arg in opts:
        if   opt in ("-n", "--noicon"):
            noicon = True
        elif opt in ("-t", "--textonly"):
            textonly = True
        elif opt in ("-h", "--help"):
            usage()

    global myVPN
    myVPN = vpn_lib(homeDir, scriptName, textonly, noicon)
    for opt, arg in opts:
        if opt in ("-k", "--kill"):
            myVPN.killVpn()
        elif opt in ("-s", "--start"):
            vpn = openconnect()
            vpn.startVPN()
        elif opt in ("-r", "--restart"):
            myVPN.killVpn()
            time.sleep(1)
            vpn = openconnect()
            vpn.startVPN()

    return 0


if __name__ == "__main__":
    global scriptName, homeDir
    scriptName = os.path.basename(sys.argv[0])[0:-3]
    homeDir = os.path.dirname(sys.argv[0])
    main(sys.argv[1:])

