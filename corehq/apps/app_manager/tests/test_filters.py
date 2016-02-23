import datetime
from collections import namedtuple
from contextlib import contextmanager
from django.test import SimpleTestCase, TestCase
from mock import Mock, patch
from corehq.apps.app_manager.models import (
    CustomMonthFilter,
    _filter_by_case_sharing_group_id,
    _filter_by_location_id,
    _filter_by_parent_location_id,
    _filter_by_ancestor_location_type_id,
    _filter_by_username,
    _filter_by_user_id,
)
from corehq.apps.domain.models import Domain
from corehq.apps.locations.models import SQLLocation, LocationType
from corehq.apps.reports_core.filters import Choice
from corehq.apps.users.models import CommCareUser


Date = namedtuple('Date', ('year', 'month', 'day'))


DOMAIN = 'test_domain'
MAY_15 = Date(2015, 5, 15)
MAY_20 = Date(2015, 5, 20)
MAY_21 = Date(2015, 5, 21)


@contextmanager
def patch_today(year, month, day):
    date_class = datetime.date
    with patch('datetime.date') as date_patch:
        date_patch.today.return_value = date_class(year, month, day)
        date_patch.side_effect = lambda *args, **kwargs: date_class(*args, **kwargs)
        yield date_patch


class CustomMonthFilterTests(SimpleTestCase):

    def setUp(self):
        self.date_class = datetime.date

    # Assume it was May 15:
    # Period 0, day 21, you would sync April 21-May 15th
    # Period 1, day 21, you would sync March 21-April 20th
    # Period 2, day 21, you would sync February 21-March 20th

    def test_may15_period0(self):
        with patch_today(*MAY_15):
            filter_ = CustomMonthFilter(start_of_month=21, period=0)
            date_span = filter_.get_filter_value(user=None, ui_filter=None)
            self.assertEqual(date_span.startdate, self.date_class(year=2015, month=4, day=21))
            self.assertEqual(date_span.enddate, self.date_class(*MAY_15))

    def test_may15_period1(self):
        with patch_today(*MAY_15):
            filter_ = CustomMonthFilter(start_of_month=21, period=1)
            date_span = filter_.get_filter_value(user=None, ui_filter=None)
            self.assertEqual(date_span.startdate, self.date_class(year=2015, month=3, day=21))
            self.assertEqual(date_span.enddate, self.date_class(year=2015, month=4, day=20))

    def test_may15_period2(self):
        with patch_today(*MAY_15):
            filter_ = CustomMonthFilter(start_of_month=21, period=2)
            date_span = filter_.get_filter_value(user=None, ui_filter=None)
            self.assertEqual(date_span.startdate, self.date_class(year=2015, month=2, day=21))
            self.assertEqual(date_span.enddate, self.date_class(year=2015, month=3, day=20))

    # Assume it was May 20:
    # Period 0, day 21, you would sync April 21-May 20th
    # Period 1, day 21, you would sync March 21-April 20th
    # Period 2, day 21, you would sync February 21-March 20th

    def test_may20_period0(self):
        with patch_today(*MAY_20):
            filter_ = CustomMonthFilter(start_of_month=21, period=0)
            date_span = filter_.get_filter_value(user=None, ui_filter=None)
            self.assertEqual(date_span.startdate, self.date_class(year=2015, month=4, day=21))
            self.assertEqual(date_span.enddate, self.date_class(*MAY_20))

    def test_may20_period1(self):
        with patch_today(*MAY_20):
            filter_ = CustomMonthFilter(start_of_month=21, period=1)
            date_span = filter_.get_filter_value(user=None, ui_filter=None)
            self.assertEqual(date_span.startdate, self.date_class(year=2015, month=3, day=21))
            self.assertEqual(date_span.enddate, self.date_class(year=2015, month=4, day=20))

    def test_may20_period2(self):
        with patch_today(*MAY_20):
            filter_ = CustomMonthFilter(start_of_month=21, period=2)
            date_span = filter_.get_filter_value(user=None, ui_filter=None)
            self.assertEqual(date_span.startdate, self.date_class(year=2015, month=2, day=21))
            self.assertEqual(date_span.enddate, self.date_class(year=2015, month=3, day=20))

    # Assume it was May 21:
    # Period 0, day 21, you would sync May 21-May 21th
    # Period 1, day 21, you would sync April 21-May 20th
    # Period 2, day 21, you would sync March 21-April 20th

    def test_may21_period0(self):
        with patch_today(*MAY_21):
            filter_ = CustomMonthFilter(start_of_month=21, period=0)
            date_span = filter_.get_filter_value(user=None, ui_filter=None)
            self.assertEqual(date_span.startdate, self.date_class(*MAY_21))
            self.assertEqual(date_span.enddate, self.date_class(*MAY_21))

    def test_may21_period1(self):
        with patch_today(*MAY_21):
            filter_ = CustomMonthFilter(start_of_month=21, period=1)
            date_span = filter_.get_filter_value(user=None, ui_filter=None)
            self.assertEqual(date_span.startdate, self.date_class(year=2015, month=4, day=21))
            self.assertEqual(date_span.enddate, self.date_class(*MAY_20))

    def test_may21_period2(self):
        with patch_today(*MAY_21):
            filter_ = CustomMonthFilter(start_of_month=21, period=2)
            date_span = filter_.get_filter_value(user=None, ui_filter=None)
            self.assertEqual(date_span.startdate, self.date_class(year=2015, month=3, day=21))
            self.assertEqual(date_span.enddate, self.date_class(year=2015, month=4, day=20))

    # May 15 for 10 days from the end of the month (start_of_month = -10):
    # Period 0, day 21, you would sync April 21-May 15th
    # Period 1, day 21, you would sync March 21-April 20th
    # Period 2, day 21, you would sync February 18-March 20th

    def test_may15_minus10_period0(self):
        with patch_today(*MAY_15):
            filter_ = CustomMonthFilter(start_of_month=-10, period=0)
            date_span = filter_.get_filter_value(user=None, ui_filter=None)
            self.assertEqual(date_span.startdate, self.date_class(year=2015, month=4, day=21))
            self.assertEqual(date_span.enddate, self.date_class(*MAY_15))

    def test_may15_minus10_period1(self):
        with patch_today(*MAY_15):
            filter_ = CustomMonthFilter(start_of_month=-10, period=1)
            date_span = filter_.get_filter_value(user=None, ui_filter=None)
            self.assertEqual(date_span.startdate, self.date_class(year=2015, month=3, day=21))
            self.assertEqual(date_span.enddate, self.date_class(year=2015, month=4, day=20))

    def test_may15_minus10_period2(self):
        with patch_today(*MAY_15):
            filter_ = CustomMonthFilter(start_of_month=-10, period=2)
            date_span = filter_.get_filter_value(user=None, ui_filter=None)
            self.assertEqual(date_span.startdate, self.date_class(year=2015, month=2, day=18))
            self.assertEqual(date_span.enddate, self.date_class(year=2015, month=3, day=20))


class AutoFilterTests(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.domain = Domain(name=DOMAIN)
        cls.domain.save()

        cls.country = LocationType(domain=DOMAIN, name='country')
        cls.country.save()
        cls.state = LocationType(
            domain=DOMAIN,
            name='state',
            parent_type=cls.country,
        )
        cls.state.save()
        cls.city = LocationType(
            domain=DOMAIN,
            name='city',
            parent_type=cls.state,
            shares_cases=True,
        )
        cls.city.save()

        cls.usa = SQLLocation(
            domain=DOMAIN,
            name='The United States of America',
            location_id='usa',
            site_code='usa',
            location_type=cls.country,
        )
        cls.usa.save()
        cls.massachusetts = SQLLocation(
            domain=DOMAIN,
            name='Massachusetts',
            location_id='massachusetts',
            site_code='massachusetts',
            location_type=cls.state,
            parent=cls.usa,
        )
        cls.massachusetts.save()
        cls.new_york = SQLLocation(
            domain=DOMAIN,
            name='New York',
            location_id='new_york',
            site_code='new_york',
            location_type=cls.state,
            parent=cls.usa,
        )
        cls.new_york.save()

        cls.cambridge = SQLLocation(
            domain=DOMAIN,
            name='Cambridge',
            location_id='cambridge',
            site_code='cambridge',
            location_type=cls.city,
            parent=cls.massachusetts,
        )
        cls.cambridge.save()
        cls.somerville = SQLLocation(
            domain=DOMAIN,
            name='Somerville',
            location_id='somerville',
            site_code='somerville',
            location_type=cls.city,
            parent=cls.massachusetts,
        )
        cls.somerville.save()
        cls.nyc = SQLLocation(
            domain=DOMAIN,
            name='New York City',
            location_id='nyc',
            site_code='nyc',
            location_type=cls.city,
            parent=cls.new_york,
        )
        cls.nyc.save()

        cls.drew = CommCareUser(
            domain=DOMAIN,
            username='drew',
            location_id='nyc',
        )
        cls.jon = CommCareUser(
            domain=DOMAIN,
            username='jon',
            location_id='cambridge',
        )
        cls.nate = CommCareUser(
            domain=DOMAIN,
            username='nate',
            location_id='somerville',
        )
        cls.sheel = CommCareUser(
            domain=DOMAIN,
            username='sheel',
            location_id='somerville',
            last_login=datetime.now(),
            date_joined=datetime.now(),
        )
        cls.sheel.save()

    def setUp(self):
        self.ui_filter = Mock()
        self.ui_filter.name = 'test_filter'
        self.ui_filter.value.return_value = 'result'

    @classmethod
    def tearDownClass(cls):
        cls.sheel.delete()
        cls.nyc.delete()
        cls.somerville.delete()
        cls.cambridge.delete()
        cls.new_york.delete()
        cls.massachusetts.delete()
        cls.usa.delete()

    def test_filter_by_case_sharing_group_id(self):
        result = _filter_by_case_sharing_group_id(self.sheel, None)
        self.assertEqual(result, [Choice(value='somerville', display=None)])

    def test_filter_by_location_id(self):
        result = _filter_by_location_id(self.drew, self.ui_filter)
        self.ui_filter.value.assert_called_with(test_filter='nyc')
        self.assertEqual(result, 'result')

    def test_filter_by_parent_location_id(self):
        result = _filter_by_parent_location_id(self.jon, self.ui_filter)
        self.ui_filter.value.assert_called_with(test_filter='massachusetts')
        self.assertEqual(result, 'result')

    def test_filter_by_ancestor_location_type_id(self):
        result = _filter_by_ancestor_location_type_id(self.nate, None)
        self.assertEqual(result, [
            Choice(value=self.country.id, display='country'),
            Choice(value=self.state.id, display='state'),
            # Note: These are ancestors, so the user's own location type is excluded
        ])

    def test_filter_by_username(self):
        result = _filter_by_username(self.sheel, None)
        self.assertEqual(result, Choice(value='sheel', display=None))

    def test_filter_by_user_id(self):
        result = _filter_by_user_id(self.sheel, None)
        self.assertEqual(result, Choice(value=self.sheel._id, display=None))
