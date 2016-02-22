# -*- coding: utf-8 -*-

import unittest
from trac.test import EnvironmentStub, Mock

from estimationtools.utils import EstimationToolsBase


class EstimationToolsBaseTestCase(unittest.TestCase):

    def test_disabled_without_estimation_field(self):
        if not hasattr(EnvironmentStub, 'is_enabled'):
            return # 0.12+ feature of mock env
        class TestTool(EstimationToolsBase):
            pass
        env = EnvironmentStub(enable=['estimationtools.*'])
        messages = []
        env.log = Mock(error=lambda msg, *args: messages.append(msg % args))
        TestTool(env)
        self.assertEquals(False, env.is_enabled(TestTool))
        self.assertEquals(messages,
                ['EstimationTools (TestTool): Estimation field not configured. Component disabled.'])

    def test_enabled_with_estimation_field(self):
        if not hasattr(EnvironmentStub, 'is_enabled'):
            return # 0.12+ feature of mock env
        class TestTool(EstimationToolsBase):
            pass
        env = EnvironmentStub()
        env.config.set('ticket-custom', 'hours_remaining', 'text')
        env.config.set('estimation-tools', 'estimation_field', 'hours_remaining')
        env.config.set('components', 'estimationtools.*', 'enabled')
        messages = []
        env.log = Mock(error=lambda msg, *args: messages.append(msg))
        TestTool(env)
        self.assertEquals(True, env.is_enabled(TestTool))
        self.assertEquals(messages, [])


def suite():
    return unittest.makeSuite(EstimationToolsBaseTestCase)


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
