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
SCRIPT_DESC    = "UnderNET X OTP authentication"
SCRIPT_COMMAND = "uotp"

HOOKS = {}

SETTINGS = {
    "otp_server_name": "off",
}

import_ok = True

try:
    import weechat
except ImportError:
    print "This script must be run under WeeChat."
    import_ok = False

try:
    import hmac
    import re
    from base64 import b32decode
    from hashlib import sha1
    from struct import pack, unpack
    from time import time
    from binascii import unhexlify
except ImportError as err:
    print "Missing module(s) for %s: %s" % (SCRIPT_NAME, err)
    import_ok = False


def unhook(hook):
    global HOOKS

    if hook in HOOKS:
        weechat.unhook(HOOKS[hook])
        del HOOKS[hook]


def unhook_all():
    for hook in ['notice', 'modifier']:
        unhook(hook)


def hook_all(server):
    global HOOKS

    HOOKS['notice']   = weechat.hook_signal("%s,irc_raw_in_notice" % server, "auth_success_cb", "")
    HOOKS['modifier'] = weechat.hook_modifier("irc_out_privmsg", "totp_login_modifier_cb", "")


def totp_login_modifier_cb(data, modifier, modifier_data, cmd):
    if re.match(r'(?i)^PRIVMSG x@channels.undernet.org :login .+ .+', cmd):
        otp = generate_totp()
        if otp is not None:
            cmd += " %s" % otp
    return cmd


def auth_success_cb(data, signal, signal_data):
    if signal_data.startswith(":X!cservice@undernet.org NOTICE"):
        if re.match(r'^:X!cservice@undernet.org NOTICE .+ :AUTHENTICATION SUCCESSFUL', signal_data):
            unhook_all()

    return weechat.WEECHAT_RC_OK


def signal_cb(data, signal, signal_data):
    value = weechat.config_get_plugin('otp_server_name')

    if signal == 'irc_server_connecting':
        if value is not "off" and value == signal_data:
            hook_all(signal_data)
    elif signal == 'irc_server_disconnected':
        if value is not "off" and value == signal_data:
            unhook_all()

    return weechat.WEECHAT_RC_OK


def get_otp_cb(data, buffer, args):
    otp = generate_totp()

    if otp is not None:
        weechat.prnt("", "UnderNET OTP: %s" % otp)

    return weechat.WEECHAT_RC_OK


def generate_totp(period=30):
    seed = weechat.string_eval_expression("${sec.data.undernet_seed}", {}, {}, {})

    if seed is "":
        weechat.prnt("", "No OATH-TOTP secret set, use: /secure set undernet_seed <secret>")
        return None

    if len(seed) == 40:  # Assume hex format
        seed = unhexlify(seed)
    else:
        seed = b32decode(seed, True)

    t = pack(">Q", int(time() / period))
    _hmac = hmac.new(seed, t, sha1).digest()
    o = ord(_hmac[19]) & 15
    otp = (unpack(">I", _hmac[o:o+4])[0] & 0x7fffffff) % 1000000

    return '%06d' % otp


if __name__ == "__main__" and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                        SCRIPT_DESC, "", ""):
        version = weechat.info_get("version_number", "") or 0
        if int(version) < 0x00040200:
            weechat.prnt("", "%s requires WeeChat >= 0.4.2 for secure_data support." % SCRIPT_NAME)
            weechat.command("", "/wait 1ms /python unload %s" % SCRIPT_NAME)

        weechat.hook_command(SCRIPT_COMMAND, "UnderNET X OTP", "", "", "", "get_otp_cb", "")
        weechat.hook_signal("irc_server_connecting", "signal_cb", "")
        weechat.hook_signal("irc_server_disconnected", "signal_cb", "")

        for option, default_value in SETTINGS.items():
            if weechat.config_get_plugin(option) == "":
                weechat.config_set_plugin(option, default_value)
