"""
Imports all extractor modules so their register() calls fire at import time.

Sub 1.5 (tier-1 extractors): slack, github, stripe, hubspot, linear,
notion, calendly, intercom, zendesk, salesforce.
Sub 1.6 (tier-2 extractors): asana, jira, microsoft_teams, discord, pagerduty,
clickup, greenhouse, mailchimp, twilio, zoom, loom, front, help_scout, freshdesk,
pipedrive, close, attio, bamboohr, gusto, ashby.
"""

from . import example_stub  # noqa: F401
from . import slack  # noqa: F401
from . import github  # noqa: F401
from . import stripe  # noqa: F401
from . import hubspot  # noqa: F401
from . import linear  # noqa: F401
from . import notion  # noqa: F401
from . import calendly  # noqa: F401
from . import intercom  # noqa: F401
from . import zendesk  # noqa: F401
from . import salesforce  # noqa: F401
# tier-2 extractors (sub 1.6)
from . import asana  # noqa: F401
from . import jira  # noqa: F401
from . import microsoft_teams  # noqa: F401
from . import discord  # noqa: F401
from . import pagerduty  # noqa: F401
from . import clickup  # noqa: F401
from . import greenhouse  # noqa: F401
from . import mailchimp  # noqa: F401
from . import twilio  # noqa: F401
from . import zoom  # noqa: F401
from . import loom  # noqa: F401
from . import front  # noqa: F401
from . import help_scout  # noqa: F401
from . import freshdesk  # noqa: F401
from . import pipedrive  # noqa: F401
from . import close  # noqa: F401
from . import attio  # noqa: F401
from . import bamboohr  # noqa: F401
from . import gusto  # noqa: F401
from . import ashby  # noqa: F401
