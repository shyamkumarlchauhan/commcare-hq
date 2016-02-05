import json
from copy import deepcopy
from datetime import date
from unittest import TestCase

from django.test.testcases import SimpleTestCase

from corehq.apps.es.aggregations import TermsAggregation, FilterAggregation, FiltersAggregation, RangeAggregation, \
    AggregationRange
from corehq.elastic import ESError, SIZE_LIMIT
from .es_query import HQESQuery, ESQuerySet
from . import filters
from . import forms, users


class ElasticTestMixin(object):
    def checkQuery(self, query, json_output):
        msg = "Expected Query:\n{}\nGenerated Query:\n{}".format(
            json.dumps(json_output, indent=4),
            query.dumps(pretty=True),
        )
        # NOTE: This method thinks [a, b, c] != [b, c, a]
        self.assertEqual(query.raw_query, json_output, msg=msg)


class TestESQuery(ElasticTestMixin, TestCase):
    maxDiff = 1000

    def test_basic_query(self):
        json_output = {
            "query": {
                "filtered": {
                    "filter": {
                        "and": [
                            {"match_all": {}}
                        ]
                    },
                    "query": {"match_all": {}}
                }
            },
            "size": SIZE_LIMIT
        }
        self.checkQuery(HQESQuery('forms'), json_output)

    def test_query_size(self):
        json_output = {
            "query": {
                "filtered": {
                    "filter": {
                        "and": [
                            {"match_all": {}}
                        ]
                    },
                    "query": {"match_all": {}}
                }
            },
            "size": 0
        }
        # use `is not None`; 0 or 1000000 == 1000000
        self.checkQuery(HQESQuery('forms').size(0), json_output)
        json_output['size'] = 123
        self.checkQuery(HQESQuery('forms').size(123), json_output)

    def test_form_query(self):
        json_output = {
            "query": {
                "filtered": {
                    "filter": {
                        "and": [
                            {"term": {"doc_type": "xforminstance"}},
                            {"not": {"missing":
                                {"field": "xmlns"}}},
                            {"not": {"missing":
                                {"field": "form.meta.userID"}}},
                        ]
                    },
                    "query": {"match_all": {}}
                }
            },
            "size": SIZE_LIMIT
        }
        query = forms.FormES()
        self.checkQuery(query, json_output)

    def test_user_query(self):
        json_output = {
            "query": {
                "filtered": {
                    "filter": {
                        "and": [
                            {"term": {"is_active": True}},
                            {"term": {"base_doc": "couchuser"}},
                        ]
                    },
                    "query": {"match_all": {}}
                }
            },
            "size": SIZE_LIMIT
        }
        query = users.UserES()
        self.checkQuery(query, json_output)

    def test_filtered_forms(self):
        json_output = {
            "query": {
                "filtered": {
                    "filter": {
                        "and": [
                            {"term": {"domain.exact": "zombocom"}},
                            {"term": {"xmlns.exact": "banana"}},
                            {"term": {"doc_type": "xforminstance"}},
                            {"not": {"missing":
                                {"field": "xmlns"}}},
                            {"not": {"missing":
                                {"field": "form.meta.userID"}}},
                        ]
                    },
                    "query": {"match_all": {}}
                }
            },
            "size": SIZE_LIMIT
        }
        query = forms.FormES()\
                .filter(filters.domain("zombocom"))\
                .xmlns('banana')
        self.checkQuery(query, json_output)

    def test_remove_all_defaults(self):
        # Elasticsearch fails if you pass it an empty list of filters
        query = (users.UserES()
                 .remove_default_filter('not_deleted')
                 .remove_default_filter('active'))
        filters = query.raw_query['query']['filtered']['filter']['and']
        self.assertTrue(len(filters) > 0)


class TestESQuerySet(TestCase):
    example_response = {
        u'_shards': {u'failed': 0, u'successful': 5, u'total': 5},
        u'hits': {u'hits': [ {
            u'_id': u'8063dff5-460b-46f2-b4d0-5871abfd97d4',
            u'_index': u'xforms_1cce1f049a1b4d864c9c25dc42648a45',
            u'_score': 1.0,
            u'_type': u'xform',
            u'fields': {
                u'app_id': u'fe8481a39c3738749e6a4766fca99efd',
                u'doc_type': u'xforminstance',
                u'domain': u'mikesproject',
                u'xmlns': u'http://openrosa.org/formdesigner/3a7cc07c-551c-4651-ab1a-d60be3017485'
                }
            },
            {
                u'_id': u'dc1376cd-0869-4c13-a267-365dfc2fa754',
                u'_index': u'xforms_1cce1f049a1b4d864c9c25dc42648a45',
                u'_score': 1.0,
                u'_type': u'xform',
                u'fields': {
                    u'app_id': u'3d622620ca00d7709625220751a7b1f9',
                    u'doc_type': u'xforminstance',
                    u'domain': u'mikesproject',
                    u'xmlns': u'http://openrosa.org/formdesigner/54db1962-b938-4e2b-b00e-08414163ead4'
                    }
                }
            ],
            u'max_score': 1.0,
            u'total': 5247
            },
        u'timed_out': False,
        u'took': 4
    }
    example_error = {u'error': u'IndexMissingException[[xforms_123jlajlaf] missing]',
             u'status': 404}

    def test_response(self):
        hits = [
            {
                u'app_id': u'fe8481a39c3738749e6a4766fca99efd',
                u'doc_type': u'xforminstance',
                u'domain': u'mikesproject',
                u'xmlns': u'http://openrosa.org/formdesigner/3a7cc07c-551c-4651-ab1a-d60be3017485'
            },
            {
                u'app_id': u'3d622620ca00d7709625220751a7b1f9',
                u'doc_type': u'xforminstance',
                u'domain': u'mikesproject',
                u'xmlns': u'http://openrosa.org/formdesigner/54db1962-b938-4e2b-b00e-08414163ead4'
            }
        ]
        fields = [u'app_id', u'doc_type', u'domain', u'xmlns']
        response = ESQuerySet(
            self.example_response,
            HQESQuery('forms').fields(fields)
        )
        self.assertEquals(response.total, 5247)
        self.assertEquals(response.hits, hits)

    def test_error(self):
        with self.assertRaises(ESError):
            ESQuerySet(self.example_error, HQESQuery('forms'))


class TestESFacet(ElasticTestMixin, TestCase):
    def test_terms_facet(self):
        json_output = {
            "query": {
                "filtered": {
                    "filter": {
                        "and": [
                            {"match_all": {}}
                        ]
                    },
                    "query": {"match_all": {}}
                }
            },
            "facets": {
                "babies_saved": {
                    "terms": {
                        "field": "babies.count",
                        "size": 10,
                        "shard_size": SIZE_LIMIT,
                    }
                }
            },
            "size": SIZE_LIMIT,
        }
        query = HQESQuery('forms')\
                .terms_facet('babies.count', 'babies_saved', size=10)
        self.checkQuery(query, json_output)

    def test_facet_response(self):
        example_response = {
            "hits": {},
            "shards": {},
            "facets": {
                "user": {
                    "_type": "terms",
                    "missing": 0,
                    "total": 3406,
                    "other": 619,
                    "terms": [
                        {
                        "term": "92647b9eafd9ea5ace2d1470114dbddd",
                        "count": 579
                        },
                        {
                        "term": "df5123010b24fc35260a84547148de93",
                        "count": 310
                        },
                        {
                        "term": "df5123010b24fc35260a84547148d47e",
                        "count": 303
                        },
                        {
                        "term": "7334d1ab1cd8847c69fba75043ed43d3",
                        "count": 298
                        }
                    ]
                }
            }
        }
        expected_output = {
            "92647b9eafd9ea5ace2d1470114dbddd": 579,
            "df5123010b24fc35260a84547148de93": 310,
            "df5123010b24fc35260a84547148d47e": 303,
            "7334d1ab1cd8847c69fba75043ed43d3": 298,
        }
        query = HQESQuery('forms')\
                .terms_facet('form.meta.userID', 'user', size=10)
        res = ESQuerySet(example_response, query)
        output = res.facets.user.counts_by_term()
        self.assertEqual(output, expected_output)

    def test_bad_facet_name(self):
        with self.assertRaises(AssertionError):
            HQESQuery('forms')\
                .terms_facet('form.meta.userID', 'form.meta.userID', size=10)


class TestQueries(TestCase):
    def assertHasQuery(self, es_query, desired_query):
        generated = es_query.raw_query['query']['filtered']['query']
        msg = "Expected to find query\n{}\nInstead found\n{}".format(
            json.dumps(desired_query, indent=4),
            json.dumps(generated, indent=4),
        )
        self.assertEqual(generated, desired_query, msg=msg)

    def test_query(self):
        query = HQESQuery('forms').set_query({"fancy_query": {"foo": "bar"}})
        self.assertHasQuery(query, {"fancy_query": {"foo": "bar"}})

    def test_null_query_string_queries(self):
        query = HQESQuery('forms').search_string_query("")
        self.assertHasQuery(query, {"match_all": {}})

        query = HQESQuery('forms').search_string_query(None)
        self.assertHasQuery(query, {"match_all": {}})

    def test_basic_query_string_query(self):
        query = HQESQuery('forms').search_string_query("foo")
        self.assertHasQuery(query, {
            "query_string": {
                "query": "*foo*",
                "default_operator": "AND",
                "fields": None,
            }
        })

    def test_query_with_fields(self):
        default_fields = ['name', 'type', 'date']
        query = HQESQuery('forms').search_string_query("foo", default_fields)
        self.assertHasQuery(query, {
            "query_string": {
                "query": "*foo*",
                "default_operator": "AND",
                "fields": ['name', 'type', 'date'],
            }
        })

    def test_complex_query_with_fields(self):
        default_fields = ['name', 'type', 'date']
        query = (HQESQuery('forms')
                 .search_string_query("name: foo", default_fields))
        self.assertHasQuery(query, {
            "query_string": {
                "query": "name: foo",
                "default_operator": "AND",
                "fields": None,
            }
        })


class TestFilters(ElasticTestMixin, TestCase):
    def test_nested_filter(self):
        json_output = {
            "query": {
                "filtered": {
                    "filter": {
                        "and": [
                            {"nested": {
                                "path": "actions",
                                "filter": {
                                    "range": {
                                        "actions.date": {
                                            "gte": "2015-01-01",
                                            "lt": "2015-02-01"
                                        }
                                    }
                                }
                            }},
                            {"match_all": {}}
                        ]
                    },
                    "query": {"match_all": {}}
                }
            },
            "size": SIZE_LIMIT
        }

        start, end = date(2015, 1, 1), date(2015, 2, 1)
        query = (HQESQuery('cases')
                 .nested("actions",
                         filters.date_range("actions.date", gte=start, lt=end)))

        self.checkQuery(query, json_output)


class TestSourceFiltering(ElasticTestMixin, TestCase):
    def test_source_include(self):
        json_output = {
            "query": {
                "filtered": {
                    "filter": {
                        "and": [
                            {"match_all": {}}
                        ]
                    },
                    "query": {"match_all": {}}
                }
            },
            "size": SIZE_LIMIT,
            "_source": ["source_obj"]
        }
        q = HQESQuery('forms').source('source_obj')
        self.checkQuery(q, json_output)


class TestAggregations(ElasticTestMixin, SimpleTestCase):
    def test_nested_aggregation(self):
        json_output = {
            "query": {
                "filtered": {
                    "filter": {
                        "and": [
                            {"match_all": {}}
                        ]
                    },
                    "query": {"match_all": {}}
                }
            },
            "aggs": {
                "users": {
                    "terms": {"field": "user_id"},
                    "aggs": {
                        "closed": {
                            "filter": {
                                "term": {"closed": True}
                            }
                        }
                    }
                },
                "total_by_status": {
                    "filters": {
                        "filters": {
                            "closed": {"term": {"closed": True}},
                            "open": {"term": {"closed": False}}
                        }
                    }
                }
            },
            "size": SIZE_LIMIT
        }

        query = HQESQuery('cases').aggregations([
            TermsAggregation("users", 'user_id').aggregation(
                FilterAggregation('closed', filters.term('closed', True))
            ),
            FiltersAggregation('total_by_status')
                .add_filter('closed', filters.term('closed', True))
                .add_filter('open', filters.term('closed', False))
        ])
        self.checkQuery(query, json_output)

    def test_result_parsing_basic(self):
        query = HQESQuery('cases').aggregations([
            FilterAggregation('closed', filters.term('closed', True)),
            FilterAggregation('open', filters.term('closed', False))
        ])

        raw_result = {
            "aggregations": {
                "closed": {
                    "doc_count": 1
                },
                "open": {
                    "doc_count": 2
                }
            }
        }
        queryset = ESQuerySet(raw_result, deepcopy(query))
        self.assertEqual(queryset.aggregations.closed.doc_count, 1)
        self.assertEqual(queryset.aggregations.open.doc_count, 2)

    def test_result_parsing_complex(self):
        query = HQESQuery('cases').aggregation(
            TermsAggregation("users", 'user_id').aggregation(
                FilterAggregation('closed', filters.term('closed', True))
            ).aggregation(
                FilterAggregation('open', filters.term('closed', False))
            )
        ).aggregation(
            RangeAggregation('by_date', 'name', [
                AggregationRange(end='c'),
                AggregationRange(start='f'),
                AggregationRange(start='k', end='p')
            ])
        )

        raw_result = {
            "aggregations": {
                "users": {
                    "buckets": [
                        {
                            "closed": {
                                "doc_count": 0
                            },
                            "doc_count": 2,
                            "key": "user1",
                            "open": {
                                "doc_count": 2
                            }
                        }
                    ],
                    "doc_count_error_upper_bound": 0,
                    "sum_other_doc_count": 0
                },
                "by_date": {
                    "buckets": {
                        "*-c": {
                            "to": "c",
                            "doc_count": 3
                        },
                        "f-*": {
                            "from": "f",
                            "doc_count": 8
                        },
                        "k-p": {
                            "from": "k",
                            "to": "p",
                            "doc_count": 6
                        }
                    }
                }
            },
        }
        queryset = ESQuerySet(raw_result, deepcopy(query))
        self.assertEqual(queryset.aggregations.users.buckets.user1.key, 'user1')
        self.assertEqual(queryset.aggregations.users.buckets.user1.doc_count, 2)
        self.assertEqual(queryset.aggregations.users.buckets.user1.closed.doc_count, 0)
        self.assertEqual(queryset.aggregations.users.buckets.user1.open.doc_count, 2)
        self.assertEqual(queryset.aggregations.users.buckets_dict['user1'].open.doc_count, 2)
        self.assertEqual(queryset.aggregations.users.counts_by_bucket, {
            'user1': 2
        })
        self.assertEqual(queryset.aggregations.by_date.counts_by_bucket, {
            '*-c': 3,
            'f-*': 8,
            'k-p': 6,
        })

    def test_range_aggregation(self):
        json_output = {
            "query": {
                "filtered": {
                    "filter": {
                        "and": [
                            {"match_all": {}}
                        ]
                    },
                    "query": {"match_all": {}}
                }
            },
            "aggs": {
                "by_date": {
                    "range": {
                        "field": "name",
                        "keyed": True,
                        "ranges": [
                            {"to": "c"},
                            {"from": "f"},
                            {"from": "k", "to": "p", "key": "k-p"},
                        ]
                    }
                },
            },
            "size": SIZE_LIMIT
        }
        query = HQESQuery('cases').aggregation(
            RangeAggregation('by_date', 'name', [
                AggregationRange(end='c'),
                AggregationRange(start='f'),
                AggregationRange(start='k', end='p', key='k-p')
            ])
        )

        self.checkQuery(query, json_output)
