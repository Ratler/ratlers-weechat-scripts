# -*- coding: utf-8 -*-
#
# Copyright (C) 2014  Stefan Wold <ratler@stderr.eu>
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
# (This script requires WeeChat 0.4.3 or higher).
#
# WeeChat script for responsive layout based on terminal height and width.
#
#
# Source and changes available on GitHUB: https://github.com/Ratler/ratlers-weechat-scripts
#
# Configuration:
#
# Commands:
#


SCRIPT_NAME    = "responsive_layout"
SCRIPT_AUTHOR  = "Stefan Wold <ratler@stderr.eu>"
SCRIPT_VERSION = "0.1dev"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Responsive layout"
SCRIPT_COMMAND = "rlayout"

SETTINGS = {
    "nicklist": ("on", "Global setting to always show nicklist when layout switches.")
}

LAYOUT_LIST = []

import_ok = True

try:
    import weechat
except ImportError:
    print "This script must be run under WeeChat."
    import_ok = False

try:
    import re
    from operator import itemgetter
except ImportError as err:
    print "Missing module(s) for %s: %s" % (SCRIPT_NAME, err)
    import_ok = False


def responsive_cb(data, signal, signal_data):
    term_height = int(weechat.info_get("term_height", ""))
    term_width = int(weechat.info_get("term_width", ""))

    try:
        apply_layout = None
        for layout, width, height in LAYOUT_LIST:
            if term_height <= int(height) or term_width <= int(width):
                apply_layout = layout
                break

        if apply_layout is None:
            # Always apply the last layout if term width/height is larger than configured layouts
            apply_layout = LAYOUT_LIST[-1][0]

        if layout_exist(apply_layout) and not layout_current(apply_layout):
            weechat.prnt("", "Applying layout %s" % apply_layout)
            weechat.command("", "/layout apply %s" % apply_layout)
            toggle_nick_list(apply_layout)

    except ValueError:
        weechat.prnt("", "height or width is not a number, ignored.")

    return weechat.WEECHAT_RC_OK


def layout_current(layout):
    infolist = weechat.infolist_get("layout", "", "")
    current = False

    while weechat.infolist_next(infolist):
        if weechat.infolist_integer(infolist, "current_layout") == 1 and \
           weechat.infolist_string(infolist, "name") == layout:
            current = True
            break

    weechat.infolist_free(infolist)
    return current


def layout_exist(layout):
    infolist = weechat.infolist_get("layout", "", "")
    found = False

    while weechat.infolist_next(infolist):
        if layout == weechat.infolist_string(infolist, "name"):
            found = True
            break

    weechat.infolist_free(infolist)
    return found


def toggle_nick_list(layout):
    """
    Check configuration whether nick list bar should be on or off for the provided layout.
    """
    value = weechat.config_get_plugin("layout.%s.nicklist" % layout)
    if value == "":
        value = weechat.config_get_plugin("nicklist")

    if value == "on":
        weechat.command("", "/bar show nicklist")
    elif value == "off":
        weechat.command("", "/bar hide nicklist")


def update_layout_list():
    """
    Updates global LAYOUT_LIST with a sorted array containing layout tuples, ie (layout_name, width, height)
    """
    global LAYOUT_LIST

    layouts = []
    layout_tuples = []
    pattern = re.compile(r"^plugins\.var\.python\.%s\.layout\.(.+)\." % SCRIPT_NAME)
    infolist = weechat.infolist_get("option", "", "plugins.var.python.%s.layout.*" % SCRIPT_NAME)

    while weechat.infolist_next(infolist):
        layout = re.search(pattern, weechat.infolist_string(infolist, "full_name")).groups()
        if layout not in layouts:
            layouts.append(layout)

    weechat.infolist_free(infolist)

    for layout in layouts:
        width = weechat.config_get_plugin("layout.%s.width" % layout)
        height = weechat.config_get_plugin("layout.%s.height" % layout)

        if width is not "" and height is not "":
            tup = ('%s' % layout, int(width), int(height))
            layout_tuples.append(tup)

    layout_tuples.sort(key=itemgetter(1, 2))
    LAYOUT_LIST = layout_tuples


def rlayout_cmd_cb(data, buffer, args):
    """
    Callback for /rlayout command.
    """
    if args == "":
        weechat.command("", "/help %s" % SCRIPT_COMMAND)
        return weechat.WEECHAT_RC_OK

    argv = args.strip().split(" ", 1)
    if len(argv) == 0:
        return weechat.WEECHAT_RC_OK

    if len(argv) < 2:
        weechat.prnt("", "Too few args")
        return weechat.WEECHAT_RC_OK

    if argv[0] == "size":
        try:
            layout, width, height = argv[1].split(" ")

            if layout_exist(layout):
                weechat.config_set_plugin("layout.%s.width" % layout, width)
                weechat.config_set_plugin("layout.%s.height" % layout, height)
                update_layout_list()
            else:
                weechat.prnt("", "Layout '%s' doesn't exist, see /help layout to create one.")
        except ValueError:
            weechat.prnt("", "Invalid number of arguments, ex /rlayout size <layout> <width> <height>")
    elif argv[0] == "nicklist":
        try:
            layout, nicklist = argv[1].split(" ")

            if layout_exist(layout):
                if nicklist == "on" or nicklist == "off":
                    weechat.config_set_plugin("layout.%s.nicklist" % layout, nicklist)
                else:
                    weechat.prnt("", "Invalid argument '%s', ex /rlayout nicklist <layout> <on|off>" % nicklist)
            else:
                weechat.prnt("", "Layout '%s' doesn't exist, see /help layout to create one.")
        except ValueError:
            weechat.prnt("", "Invalid number of arguments, ex /rlayout nicklist <layout> <on|off>")

    return weechat.WEECHAT_RC_OK


def rlayout_completion_bool_cb(data, completion_item, buffer, completion):
    for bool in ("on", "off"):
        weechat.hook_completion_list_add(completion, bool, 0, weechat.WEECHAT_LIST_POS_SORT)
    return weechat.WEECHAT_RC_OK


if __name__ == "__main__" and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
        version = weechat.info_get("version_number", "") or 0
        if int(version) < 0x00040300:
            weechat.prnt("", "%s requires WeeChat >= 0.4.3 for terminal height and width support." % SCRIPT_NAME)
            weechat.command("", "/wait 1ms /python unload %s" % SCRIPT_NAME)

        weechat.hook_command(SCRIPT_COMMAND,
                             "WeeChat responsive layout",
                             "size <layout> <width> <height> || nicklist <layout> <on|off>",
                             "    size: bla bla\n"
                             "nicklist: blabla\n\n",
                             "size %(layouts_names)"
                             " || nicklist %(layouts_names) %(rlayout_bool_value)",
                             "rlayout_cmd_cb",
                             "")

        # Default settings
        for option, default_value in SETTINGS.items():
            if weechat.config_get_plugin(option) == "":
                weechat.config_set_plugin(option, default_value[0])
            weechat.config_set_desc_plugin(option, '%s (default: %s)' % (default_value[1], default_value[0]))

        weechat.hook_completion("rlayout_bool_value", "list of bool values", "rlayout_completion_bool_cb", "")
        update_layout_list()
        hook = weechat.hook_signal("signal_sigwinch", "responsive_cb", "")
