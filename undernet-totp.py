# -*- coding: utf-8 -*-
#
# Copyright (C) 2013  Stefan Wold <ratler@stderr.eu>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
# WeeChat script for UnderNET's X OATH-TOTP authentication
#
#

SCRIPT_NAME    = "undernet-totp"
SCRIPT_AUTHOR  = "Stefan Wold <ratler@stderr.eu>"
SCRIPT_VERSION = "0.1dev"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "UnderNET X service OATH-TOTP authentication"
SCRIPT_COMMAND = "uotp"

import_ok = True

try:
    import weechat
except ImportError:
    print "This script must be run under WeeChat."
    import_ok = False

try:
    import hmac
    import base64
    import hashlib
    import struct
    import time
    import re
except ImportError as err:
    print "Missing module(s) for %s: %s" % (SCRIPT_NAME, err)
    import_ok = False


def totp_login_modifier_cb(data, modifier, modifier_data, cmd):
    if re.match(r'^PRIVMSG x@channels.undernet.org :login .+ .+', cmd):
        otp = generate_totp()
        if otp is not None:
            cmd += " %s" % otp
    return cmd


def get_otp_cb(data, buffer, args):
    otp = generate_totp()
    if otp is not None:
        weechat.prnt("", "UnderNET OTP: %s" % otp)
    return weechat.WEECHAT_RC_OK


def generate_totp():
    seed = weechat.string_eval_expression("${sec.data.undernet_token}", {}, {}, {})
    if seed is "":
        weechat.prnt("", "No Oath-TOTP base32 encoded secret set, use: /secure set undernet_token <secret>")
        return None
    s = base64.b32decode(seed, True)
    m = struct.pack(">Q", int(time.time())//30)
    h = hmac.new(s, m, hashlib.sha1).digest()
    o = ord(h[19]) & 15
    h = (struct.unpack(">I", h[o:o+4])[0] & 0x7fffffff) % 1000000

    return '%06d' % h

if __name__ == "__main__" and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                        SCRIPT_DESC, "", ""):
        version = weechat.info_get("version_number", "") or 0
        if int(version) < 0x00040200:
            weechat.prnt("", "%s requires WeeChat >= 0.4.2 for secure_data support." % SCRIPT_NAME)
            weechat.command("", "/wait 1ms /python unload %s" % SCRIPT_NAME)

        weechat.hook_command(SCRIPT_COMMAND, "UnderNET X OATH-TOTP", "", "", "", "get_otp_cb", "")
        weechat.hook_modifier("irc_out_privmsg", "totp_login_modifier_cb", "")