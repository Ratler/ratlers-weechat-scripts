# Copyright (C) 2012 Stefan Wold <ratler@stderr.eu>
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
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#
# Automatically join channels on UnderNET that get throttled due to "Target change too fast".

use strict;
use warnings;

my $SCRIPT_NAME = "join2fast";
my $VERSION = "0.3";
my $weechat_version = "";
my %hooks;
my %channel_list;


# Register script
weechat::register($SCRIPT_NAME, "Ratler <ratler\@stderr.eu>", $VERSION, "GPL3",
                  "Automatically join channels on UnderNET that get throttled due to \"Target change too fast\"", "", "");

$weechat_version = weechat::info_get("version_number", "");
if (($weechat_version eq "") or ($weechat_version < 0x00030200)) {
  weechat::print("", weechat::prefix("error") . "$SCRIPT_NAME: requires weechat >= v0.3.2");
  weechat::command("", "/wait 1ms /perl unload $SCRIPT_NAME");
}

# Callback for "Target changed too fast" events
weechat::hook_signal("*,irc_raw_in_439", "event_439_cb", "");

sub event_439_cb {
  # $_[1] - name of the event
  # $_[2] - the message (:server 439 nick #channel :Target change too fast. Please wait 17 seconds.)

  my $server = (split ",", $_[1])[0];
  my @msg = split " ", $_[2];
  my $channel = $msg[3];
  my $delay = $msg[10];

  # Check if channel has been already added or add it
  if (!exists($channel_list{$channel})) {
    $channel_list{$channel} = $server;
  }

  # Reset timer to the last delay received
  weechat::unhook($hooks{timer}) if $hooks{timer};
  $hooks{timer} = weechat::hook_timer(($delay + 1) * 1000, 0, 1, "join_channel_cb", "");

  return weechat::WEECHAT_RC_OK;
}

sub join_channel_cb {
  # Unhook timer
  weechat::unhook($hooks{timer}) if $hooks{timer};
  delete $hooks{timer};

  # Get first entry out of the hash (order doesn't matter)
  if (keys %channel_list > 0) {
    my $channel = (keys %channel_list)[-1];
    my $server = $channel_list{$channel};
    weechat::command("", "/wait 500ms /join -server $server $channel");
    delete $channel_list{$channel};

    # Setup a new timer
    if (keys %channel_list > 0) {
      $hooks{timer} = weechat::hook_timer(2 * 1000, 0, 1, "join_channel_cb", "");
    }
  }

  return weechat::WEECHAT_RC_OK;
}
