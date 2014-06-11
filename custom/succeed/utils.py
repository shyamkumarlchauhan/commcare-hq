from django.utils.translation import ugettext as _, ugettext_noop
import dateutil
from corehq.apps.app_manager.models import ApplicationBase
from corehq.apps.domain.models import Domain

EMPTY_FIELD = "---"

SUCCEED_DOMAIN = 'succeed'
SUCCEED_CM_APPNAME = 'SUCCEED CM app'
SUCCEED_PM_APPNAME = 'SUCCEED PM app'
SUCCEED_CHW_APPNAME = 'SUCCEED CHW app'

CONFIG = {
    'groups': [
        dict(val="harbor", text=ugettext_noop("Harbor UCLA")),
        dict(val="lac-usc", text=ugettext_noop("LAC-USC")),
        dict(val="oliveview", text=ugettext_noop("Olive View Medical Center")),
        dict(val="rancho", text=ugettext_noop("Rancho Los Amigos")),
    ],
    'succeed_admin': 'SUCCEED Admin',
    'pm_role': 'Project Manager',
    'pi_role': 'Principal Investigator',
    'cm_role': 'Care Manager',
    'chw_role': 'Community Health Worker'
}


def is_succeed_admin(user):
    return user.get_role()['name'] in [CONFIG['succeed_admin'], 'Admin']


def is_pi(user):
    return user.get_role()['name'] in [CONFIG['pi_role']]


def is_cm(user):
    return user.get_role()['name'] in [CONFIG['cm_role']]


def is_chw(user):
    return user.get_role()['name'] in [CONFIG['chw_role']]


def is_pm_or_pi(user):
    return user.get_role()['name'] in [CONFIG['pm_role'], CONFIG['pi_role']]


def has_any_role(user):
    return user.get_role()['name'] in [CONFIG['pm_role'], CONFIG['pi_role'], CONFIG['cm_role'], CONFIG['chw_role']]


def get_app_build(app_dict):
    domain = Domain._get_by_name(app_dict['domain'])
    if domain.use_cloudcare_releases:
        return ApplicationBase.get(app_dict['_id']).get_latest_app()['_id']
    else:
        return ApplicationBase.get_latest_build(app_dict['domain'], app_dict['_id'])['_id']
    return None


def get_form_dict(case, form_xmlns):
    forms = case.get_forms()
    for form in forms:
        form_dict = form.form
        if form_xmlns == form_dict["@xmlns"]:
            return form_dict
    return None


def format_date(date_string, OUTPUT_FORMAT):
    if date_string is None or date_string == '' or date_string == EMPTY_FIELD or isinstance(date_string, (int, float)):
        return _("Bad Date Format!")

    if isinstance(date_string, basestring):
        try:
            date_string = dateutil.parser.parse(date_string)
        except (AttributeError, ValueError):
            return _("Bad Date Format!")

    return date_string.strftime(OUTPUT_FORMAT)
