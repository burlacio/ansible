# -*- coding: utf-8 -*-
#
# Copyright (c) 2017 F5 Networks Inc.
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
import json
import sys

from nose.plugins.skip import SkipTest
if sys.version_info < (2, 7):
    raise SkipTest("F5 Ansible modules require Python >= 2.7")

from ansible.compat.tests import unittest
from ansible.compat.tests.mock import patch, Mock
from ansible.module_utils.f5_utils import AnsibleF5Client
from ansible.module_utils.six import iteritems
from units.modules.utils import set_module_args

try:
    from library.bigip_gtm_facts import Parameters
    from library.bigip_gtm_facts import ServerParameters
    from library.bigip_gtm_facts import PoolParameters
    from library.bigip_gtm_facts import WideIpParameters
    from library.bigip_gtm_facts import ModuleManager
    from library.bigip_gtm_facts import ServerFactManager
    from library.bigip_gtm_facts import PoolFactManager
    from library.bigip_gtm_facts import TypedPoolFactManager
    from library.bigip_gtm_facts import UntypedPoolFactManager
    from library.bigip_gtm_facts import WideIpFactManager
    from library.bigip_gtm_facts import TypedWideIpFactManager
    from library.bigip_gtm_facts import UntypedWideIpFactManager
    from library.bigip_gtm_facts import ArgumentSpec
    from ansible.module_utils.f5_utils import iControlUnexpectedHTTPError
    from f5.bigip.tm.gtm.pool import A
    from f5.utils.responses.handlers import Stats
except ImportError:
    try:
        from ansible.modules.network.f5.bigip_gtm_pool import Parameters
        from ansible.modules.network.f5.bigip_gtm_pool import ServerParameters
        from ansible.modules.network.f5.bigip_gtm_pool import PoolParameters
        from ansible.modules.network.f5.bigip_gtm_pool import WideIpParameters
        from ansible.modules.network.f5.bigip_gtm_pool import ModuleManager
        from ansible.modules.network.f5.bigip_gtm_pool import ServerFactManager
        from ansible.modules.network.f5.bigip_gtm_pool import PoolFactManager
        from ansible.modules.network.f5.bigip_gtm_pool import TypedPoolFactManager
        from ansible.modules.network.f5.bigip_gtm_pool import UntypedPoolFactManager
        from ansible.modules.network.f5.bigip_gtm_pool import WideIpFactManager
        from ansible.modules.network.f5.bigip_gtm_pool import TypedWideIpFactManager
        from ansible.modules.network.f5.bigip_gtm_pool import UntypedWideIpFactManager
        from ansible.modules.network.f5.bigip_gtm_pool import ArgumentSpec
        from ansible.module_utils.f5_utils import iControlUnexpectedHTTPError
        from f5.bigip.tm.gtm.pool import A
        from f5.utils.responses.handlers import Stats
    except ImportError:
        raise SkipTest("F5 Ansible modules require the f5-sdk Python library")

fixture_path = os.path.join(os.path.dirname(__file__), 'fixtures')
fixture_data = {}


def load_fixture(name):
    path = os.path.join(fixture_path, name)

    if path in fixture_data:
        return fixture_data[path]

    with open(path) as f:
        data = f.read()

    try:
        data = json.loads(data)
    except Exception:
        pass

    fixture_data[path] = data
    return data


class FakeStatResource(object):
    def __init__(self, obj):
        self.entries = obj


class FakeARecord(A):
    def __init__(self, *args, **kwargs):
        attrs = kwargs.pop('attrs', {})
        for key, value in iteritems(attrs):
            setattr(self, key, value)


class TestParameters(unittest.TestCase):
    def test_module_parameters(self):
        args = dict(
            include=['pool'],
            filter='name.*'
        )
        p = Parameters(args)
        assert p.include == ['pool']
        assert p.filter == 'name.*'


@patch('ansible.module_utils.f5_utils.AnsibleF5Client._get_mgmt_root',
       return_value=True)
class TestManager(unittest.TestCase):

    def setUp(self):
        self.spec = ArgumentSpec()

    def test_get_typed_pool_facts(self, *args):
        set_module_args(dict(
            include='pool',
            password='passsword',
            server='localhost',
            user='admin'
        ))

        fixture1 = load_fixture('load_gtm_pool_a_collection.json')
        fixture2 = load_fixture('load_gtm_pool_a_example_stats.json')
        collection = [FakeARecord(attrs=x) for x in fixture1['items']]
        stats = Stats(FakeStatResource(fixture2['entries']))

        client = AnsibleF5Client(
            argument_spec=self.spec.argument_spec,
            supports_check_mode=self.spec.supports_check_mode,
            f5_product_name=self.spec.f5_product_name
        )

        # Override methods in the specific type of manager
        tfm = TypedPoolFactManager(client)
        tfm.read_collection_from_device = Mock(return_value=collection)
        tfm.read_stats_from_device = Mock(return_value=stats.stat)

        tm = PoolFactManager(client)
        tm.version_is_less_than_12 = Mock(return_value=False)
        tm.get_manager = Mock(return_value=tfm)

        # Override methods to force specific logic in the module to happen
        mm = ModuleManager(client)
        mm.get_manager = Mock(return_value=tm)
        mm.gtm_provisioned = Mock(return_value=True)

        results = mm.exec_module()

        assert results['changed'] is True
        assert 'pool' in results
        assert len(results['pool']) > 0
        assert 'load_balancing_mode' in results['pool'][0]
