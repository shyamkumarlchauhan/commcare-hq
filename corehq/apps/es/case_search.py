"""
CaseSearchES
------

.. code-block:: python

from corehq.apps.es import case_search as case_search_es

    q = (case_search_es.CaseSearchES()
         .domain('testproject')
"""
from __future__ import absolute_import
from __future__ import unicode_literals

from warnings import warn

import six
from django.utils.dateparse import parse_date
from django.utils.translation import ugettext as _
from eulxml.xpath import parse as parse_xpath

from corehq.apps.case_search.const import (
    CASE_PROPERTIES_PATH,
    IDENTIFIER,
    INDICES_PATH,
    REFERENCED_ID,
    RELEVANCE_SCORE,
    VALUE,
)
from corehq.apps.es.aggregations import BucketResult, TermsAggregation
from corehq.apps.es.cases import CaseES, owner
from corehq.pillows.mappings.case_search_mapping import CASE_SEARCH_ALIAS

from . import filters, queries


class CaseSearchES(CaseES):
    index = CASE_SEARCH_ALIAS

    @property
    def builtin_filters(self):
        return [case_property_filter, blacklist_owner_id] + super(CaseSearchES, self).builtin_filters

    @property
    def _case_property_queries(self):
        """
        Returns all current case_property queries
        """
        try:
            return self.es_query['query']['filtered']['query']['bool']['must']
        except (KeyError, TypeError):
            return []

    def case_property_query(self, case_property_name, value, clause=queries.MUST, fuzzy=False):
        """
        Search for all cases where case property with name `case_property_name`` has text value `value`

        Usage: (CaseSearchES()
                .domain('swashbucklers')
                .case_property_query("name", "rebdeard", "must", fuzzy=True)
                .case_property_query("age", "15", "must")
                .case_property_query("has_parrot", "yes", "should")
                .case_property_query("is_pirate", "yes", "must_not"))

        Can be chained with regular filters . Running a set_query after this will destroy it.
        Clauses can be any of SHOULD, MUST, or MUST_NOT
        """
        if fuzzy:
            positive_clause = clause != queries.MUST_NOT
            return (
                # fuzzy match
                self._add_query(case_property_text_query(case_property_name, value, fuzziness='AUTO'), clause)
                # exact match. added to improve the score of exact matches
                ._add_query(exact_case_property_text_query(case_property_name, value),
                            queries.SHOULD if positive_clause else clause))
        else:
            return self._add_query(exact_case_property_text_query(case_property_name, value), clause)

    def regexp_case_property_query(self, case_property_name, regex, clause=queries.MUST):
        """
        Search for all cases where case property `case_property_name` matches the regular expression in `regex`
        """
        return self._add_query(
            _base_property_query(case_property_name, queries.regexp(
                "{}.{}".format(CASE_PROPERTIES_PATH, VALUE), regex)
            ),
            clause,
        )

    def numeric_range_case_property_query(self, case_property_name, gt=None,
                                          gte=None, lt=None, lte=None, clause=queries.MUST):
        """
        Search for all cases where case property `case_property_name` fulfills the range criteria.
        """
        return self._add_query(
            case_property_range_query(case_property_name, gt, gte, lt, lte),
            clause
        )

    def date_range_case_property_query(self, case_property_name, gt=None,
                                       gte=None, lt=None, lte=None, clause=queries.MUST):
        """
        Search for all cases where case property `case_property_name` fulfills the date range criteria.
        """
        return self._add_query(case_property_range_query(case_property_name, gt, gte, lt, lte), clause)

    def xpath_query(self, domain, xpath):
        """Search for cases using an XPath predicate expression.

        Enter an arbitrary XPath predicate in the context of the case. Also supports related case lookups.
        e.g you can do things like:

        - case properties: "first_name = 'dolores' and last_name = 'abernathy'"
        - date ranges: "first_came_online >= '2017-08-12' or died <= '2020-11-15"
        - numeric ranges: "age >= 100 and height < 1.25"
        - related cases: "mother/first_name = 'maeve' or parent/parent/host/age = 13"
        """
        from corehq.apps.case_search.filter_dsl import (
            CaseFilterError,
            build_filter_from_ast,
        )

        try:
            return self.filter(build_filter_from_ast(domain, parse_xpath(xpath)))
        except (TypeError, RuntimeError) as e:
            raise CaseFilterError(
                _("Malformed query: {}".format(e)),
                None,
            )

    def _add_query(self, new_query, clause):
        current_query = self._query.get(queries.BOOL)
        if current_query is None:
            return self.set_query(
                queries.BOOL_CLAUSE(
                    queries.CLAUSES[clause]([new_query])
                )
            )
        elif current_query.get(clause) and isinstance(current_query[clause], list):
            current_query[clause] += [new_query]
        else:
            current_query.update(
                queries.CLAUSES[clause]([new_query])
            )
        return self

    def get_child_cases(self, case_ids, identifier):
        """Returns all cases that reference cases with ids: `case_ids`
        """
        if isinstance(case_ids, six.string_types):
            case_ids = [case_ids]

        return self._add_query(
            reverse_index_case_query(case_ids, identifier),
            queries.MUST,
        )


def case_property_filter(case_property_name, value):
    warn("Use the query versions of this function from the case_search module instead", DeprecationWarning)
    return filters.nested(
        CASE_PROPERTIES_PATH,
        filters.AND(
            filters.term("{}.key.exact".format(CASE_PROPERTIES_PATH), case_property_name),
            filters.term("{}.{}".format(CASE_PROPERTIES_PATH, VALUE), value),
        )
    )


def exact_case_property_text_query(case_property_name, value):
    """Filter by case property.

    This performs an exact match on the value in the case property, including
    letter casing and punctuation.

    """
    return queries.nested(
        CASE_PROPERTIES_PATH,
        queries.filtered(
            queries.match_all(),
            filters.AND(
                filters.term('{}.key.exact'.format(CASE_PROPERTIES_PATH), case_property_name),
                filters.term('{}.{}.exact'.format(CASE_PROPERTIES_PATH, VALUE), value),
            )
        )
    )


def case_property_text_query(case_property_name, value, fuzziness='0'):
    """Filter by case_properties.key and do a text search in case_properties.value

    This does not do exact matches on the case property value. If the value has
    multiple words, they will be OR'd together in this query. You may want to
    use the `exact_case_property_text_query` instead.

    """
    return _base_property_query(
        case_property_name,
        queries.match(value, '{}.{}'.format(CASE_PROPERTIES_PATH, VALUE), fuzziness=fuzziness)
    )


def case_property_range_query(case_property_name, gt=None, gte=None, lt=None, lte=None):
    """Returns cases where case property `key` fall into the range provided.

    """
    kwargs = {'gt': gt, 'gte': gte, 'lt': lt, 'lte': lte}
    # if its a number, use it
    try:
        # numeric range
        kwargs = {key: float(value) for key, value in six.iteritems(kwargs) if value is not None}
        return _base_property_query(
            case_property_name,
            queries.range_query("{}.{}.numeric".format(CASE_PROPERTIES_PATH, VALUE), **kwargs)
        )
    except ValueError:
        pass

    # if its a date, use it
    # date range
    kwargs = {key: parse_date(value) for key, value in six.iteritems(kwargs) if value is not None}
    return _base_property_query(
        case_property_name,
        queries.date_range("{}.{}.date".format(CASE_PROPERTIES_PATH, VALUE), **kwargs)
    )


def reverse_index_case_query(case_ids, identifier=None):
    """Fetches related cases related by `identifier`.

    For example, in a regular parent/child relationship, given a list of parent
    case ids, this will return all the child cases which point to the parents
    with identifier `parent`.

    """
    if isinstance(case_ids, six.string_types):
            case_ids = [case_ids]

    if identifier is None:      # some old relationships don't have an identifier specified
        f = filters.term('{}.{}'.format(INDICES_PATH, REFERENCED_ID), list(case_ids)),
    else:
        f = filters.AND(
            filters.term('{}.{}'.format(INDICES_PATH, REFERENCED_ID), list(case_ids)),
            filters.term('{}.{}'.format(INDICES_PATH, IDENTIFIER), identifier),
        )
    return queries.nested(
        INDICES_PATH,
        queries.filtered(
            queries.match_all(),
            f
        )
    )


def case_property_exists(case_property_name):
    """Returns cases where case_property_name is set

    """
    return queries.nested(
        CASE_PROPERTIES_PATH,
        queries.filtered(
            queries.match_all(),
            filters.term('{}.key.exact'.format(CASE_PROPERTIES_PATH), case_property_name),
        )
    )


def _base_property_query(case_property_name, query):
    return queries.nested(
        CASE_PROPERTIES_PATH,
        queries.filtered(
            query,
            filters.term('{}.key.exact'.format(CASE_PROPERTIES_PATH), case_property_name),
        )
    )


def blacklist_owner_id(owner_id):
    return filters.NOT(owner(owner_id))


def flatten_result(hit):
    """Flattens a result from CaseSearchES into the format that Case serializers
    expect

    i.e. instead of {'name': 'blah', 'case_properties':{'key':'foo', 'value':'bar'}} we return
    {'name': 'blah', 'foo':'bar'}
    """
    result = hit['_source']
    result[RELEVANCE_SCORE] = hit['_score']
    case_properties = result.pop('case_properties', [])
    for case_property in case_properties:
        key = case_property.get('key')
        value = case_property.get('value')
        if key is not None and not key.startswith("@") and value:
            result[key] = value
    return result


class CasePropertyAggregationResult(BucketResult):

    @property
    def raw_buckets(self):
        return self.result[self.aggregation.field]['values']['buckets']

    @property
    def buckets(self):
        """returns a list of buckets rather than a namedtuple since case property values can
        have non-valid python names
        """
        return self.bucket_list


class CasePropertyAggregation(TermsAggregation):
    type = "case_property"
    result_class = CasePropertyAggregationResult

    def __init__(self, name, field, size=None):
        self.name = name
        self.field = field
        self.body = {
            "nested": {
                "path": "case_properties"
            },
            "aggs": {
                field: {
                    "filter": {
                        "term": {
                            "case_properties.key": field,
                        }
                    },
                    "aggs": {
                        "values": {
                            "terms": {
                                "field": "case_properties.value"
                            }
                        }
                    }
                }
            }
        }
