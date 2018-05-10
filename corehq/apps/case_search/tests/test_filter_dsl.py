from __future__ import absolute_import, unicode_literals

from django.test import SimpleTestCase, TestCase
from elasticsearch.exceptions import ConnectionError
from eulxml.xpath import parse as parse_xpath

from casexml.apps.case.mock import CaseFactory, CaseIndex, CaseStructure
from corehq.apps.case_search.filter_dsl import build_filter_from_ast, CaseFilterError
from corehq.apps.es import CaseSearchES
from corehq.elastic import get_es_new, send_to_elasticsearch
from corehq.form_processor.tests.utils import FormProcessorTestUtils
from corehq.pillows.case_search import transform_case_for_elasticsearch
from corehq.pillows.mappings.case_search_mapping import CASE_SEARCH_INDEX_INFO
from corehq.util.elastic import ensure_index_deleted
from corehq.util.test_utils import trap_extra_setup
from pillowtop.es_utils import initialize_index_and_mapping


class TestFilterDsl(SimpleTestCase):
    def test_simple_filter(self):
        parsed = parse_xpath("name = 'farid'")
        expected_filter = {
            "nested": {
                "path": "case_properties",
                "query": {
                    "filtered": {
                        "query": {
                            "match_all": {}
                        },
                        "filter": {
                            "and": (
                                {
                                    "term": {
                                        "case_properties.key.exact": "name"
                                    }
                                },
                                {
                                    "term": {
                                        "case_properties.value.exact": "farid"
                                    }
                                }
                            )
                        }
                    }
                }
            }
        }
        built_filter = build_filter_from_ast("domain", parsed)
        self.assertEqual(expected_filter, built_filter)

    def test_date_comparison(self):
        parsed = parse_xpath("dob >= '2017-02-12'")
        expected_filter = {
            "nested": {
                "path": "case_properties",
                "query": {
                    "filtered": {
                        "filter": {
                            "term": {
                                "case_properties.key.exact": "dob"
                            }
                        },
                        "query": {
                            "range": {
                                "case_properties.value.date": {
                                    "gte": "2017-02-12",
                                }
                            }
                        }
                    }
                }
            }
        }
        self.assertEqual(expected_filter, build_filter_from_ast("domain", parsed))

    def test_numeric_comparison(self):
        parsed = parse_xpath("number <= '100.32'")
        expected_filter = {
            "nested": {
                "path": "case_properties",
                "query": {
                    "filtered": {
                        "filter": {
                            "term": {
                                "case_properties.key.exact": "number"
                            }
                        },
                        "query": {
                            "range": {
                                "case_properties.value.numeric": {
                                    "lte": 100.32,
                                }
                            }
                        }
                    }
                }
            }
        }
        self.assertEqual(expected_filter, build_filter_from_ast("domain", parsed))

    def test_case_property_existence(self):
        self.maxDiff = None
        parsed = parse_xpath("property != ''")
        expected_filter = {
            "and": (
                {
                    "nested": {
                        "path": "case_properties",
                        "query": {
                            "filtered": {
                                "filter": {
                                    "term": {
                                        "case_properties.key.exact": "property"
                                    }
                                },
                                "query": {
                                    "match_all": {
                                    }
                                }
                            }
                        }
                    }
                },
                {
                    "not": {
                        "nested": {
                            "path": "case_properties",
                            "query": {
                                "filtered": {
                                    "filter": {
                                        "and": (
                                            {
                                                "term": {
                                                    "case_properties.key.exact": "property"
                                                }
                                            },
                                            {
                                                "term": {
                                                    "case_properties.value.exact": ""
                                                }
                                            }
                                        )
                                    },
                                    "query": {
                                        "match_all": {
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            )
        }
        self.assertEqual(expected_filter, build_filter_from_ast("domain", parsed))


    def test_nested_filter(self):
        parsed = parse_xpath("(name = 'farid' or name = 'leila') and dob <= '2017-02-11'")
        expected_filter = {
            "and": (
                {
                    "or": (
                        {
                            "nested": {
                                "path": "case_properties",
                                "query": {
                                    "filtered": {
                                        "query": {
                                            "match_all": {
                                            }
                                        },
                                        "filter": {
                                            "and": (
                                                {
                                                    "term": {
                                                        "case_properties.key.exact": "name"
                                                    }
                                                },
                                                {
                                                    "term": {
                                                        "case_properties.value.exact": "farid"
                                                    }
                                                }
                                            )
                                        }
                                    }
                                }
                            }
                        },
                        {
                            "nested": {
                                "path": "case_properties",
                                "query": {
                                    "filtered": {
                                        "query": {
                                            "match_all": {
                                            }
                                        },
                                        "filter": {
                                            "and": (
                                                {
                                                    "term": {
                                                        "case_properties.key.exact": "name"
                                                    }
                                                },
                                                {
                                                    "term": {
                                                        "case_properties.value.exact": "leila"
                                                    }
                                                }
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    )
                },
                {
                    "nested": {
                        "path": "case_properties",
                        "query": {
                            "filtered": {
                                "filter": {
                                    "term": {
                                        "case_properties.key.exact": "dob"
                                    }
                                },
                                "query": {
                                    "range": {
                                        "case_properties.value.date": {
                                            "lte": "2017-02-11"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            )
        }

        built_filter = build_filter_from_ast("domain", parsed)
        self.assertEqual(expected_filter, built_filter)

    def test_self_reference(self):
        with self.assertRaises(CaseFilterError):
            build_filter_from_ast(None, parse_xpath("name = other_property"))

        with self.assertRaises(CaseFilterError):
            build_filter_from_ast(None, parse_xpath("name > other_property"))

        with self.assertRaises(CaseFilterError):
            build_filter_from_ast(None, parse_xpath("parent/name > other_property"))


class TestFilterDslLookups(TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super(TestFilterDslLookups, cls).setUpClass()
        with trap_extra_setup(ConnectionError):
            cls.es = get_es_new()
            initialize_index_and_mapping(cls.es, CASE_SEARCH_INDEX_INFO)

        cls.child_case_id = 'margaery'
        cls.parent_case_id = 'mace'
        cls.grandparent_case_id = 'olenna'
        cls.domain = "Tyrell"
        factory = CaseFactory(domain=cls.domain)
        grandparent_case = CaseStructure(
            case_id=cls.grandparent_case_id,
            attrs={
                'create': True,
                'case_type': 'grandparent',
                'update': {
                    "name": "Olenna",
                    "alias": "Queen of thorns",
                    "house": "Tyrell",
                },
            })

        parent_case = CaseStructure(
            case_id=cls.parent_case_id,
            attrs={
                'create': True,
                'case_type': 'parent',
                'update': {
                    "name": "Mace",
                    "house": "Tyrell",
                },
            },
            indices=[CaseIndex(
                grandparent_case,
                identifier='mother',
                relationship='child',
            )])

        child_case = CaseStructure(
            case_id=cls.child_case_id,
            attrs={
                'create': True,
                'case_type': 'child',
                'update': {
                    "name": "Margaery",
                    "house": "Tyrell",
                },
            },
            indices=[CaseIndex(
                parent_case,
                identifier='father',
                relationship='extension',
            )],
        )
        for case in factory.create_or_update_cases([child_case]):
            send_to_elasticsearch('case_search', transform_case_for_elasticsearch(case.to_json()))
        cls.es.indices.refresh(CASE_SEARCH_INDEX_INFO.index)

    @classmethod
    def tearDownClass(self):
        FormProcessorTestUtils.delete_all_cases()
        ensure_index_deleted(CASE_SEARCH_INDEX_INFO.index)
        super(TestFilterDslLookups, self).tearDownClass()

    def test_parent_lookups(self):
        parsed = parse_xpath("father/name = 'Mace'")
        # return all the cases who's parent (relationship named 'father') has case property 'name' = 'Mace'

        expected_filter = {
            "nested": {
                "path": "indices",
                "query": {
                    "filtered": {
                        "query": {
                            "match_all": {
                            },
                        },
                        "filter": {
                            "and": (
                                {
                                    "terms": {
                                        "indices.referenced_id": [self.parent_case_id],
                                    }
                                },
                                {
                                    "term": {
                                        "indices.identifier": "father"
                                    }
                                }
                            )
                        }
                    }
                }
            }
        }
        built_filter = build_filter_from_ast(self.domain, parsed)
        self.assertEqual(expected_filter, built_filter)
        self.assertEqual([self.child_case_id], CaseSearchES().filter(built_filter).values_list('_id', flat=True))

    def test_nested_parent_lookups(self):
        parsed = parse_xpath("father/mother/house = 'Tyrell'")

        expected_filter = {
            "nested": {
                "path": "indices",
                "query": {
                    "filtered": {
                        "query": {
                            "match_all": {
                            },
                        },
                        "filter": {
                            "and": (
                                {
                                    "terms": {
                                        "indices.referenced_id": [self.parent_case_id],
                                    }
                                },
                                {
                                    "term": {
                                        "indices.identifier": "father"
                                    }
                                }
                            )
                        }
                    }
                }
            }
        }
        built_filter = build_filter_from_ast(self.domain, parsed)
        self.assertEqual(expected_filter, built_filter)
        self.assertEqual([self.child_case_id], CaseSearchES().filter(built_filter).values_list('_id', flat=True))
