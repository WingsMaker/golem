from unittest import TestCase

from golem.core.chat_session import ChatSession
from golem.core.context import Context
from golem.core.dialog_manager import DialogManager
from golem.core.entity_value import EntityValue
from golem.core.interfaces.test import TestInterface


# mock_redis = mockredis.mock_redis_client()


# def get_fake_redis():
#      return mock_redis


class TestContext(TestCase):

    #@patch('redis.Redis', mockredis.mock_redis_client)
    #@patch('redis.StrictRedis', mockredis.mock_strict_redis_client)
    def setUp(self):
        self.session = ChatSession(TestInterface, 'test_id')
        self.dialog = DialogManager(self.session)

    def test_context_get_set(self):
        context = Context(dialog=self.dialog, entities={}, history=[], counter=0)
        context.intent = "greeting"
        context.intent = "goodbye"
        intent = context.intent.current_v()
        self.assertEquals(intent, "goodbye")
        cnt = context.intent.count()
        self.assertEquals(cnt, 2)

    def test_context_message_age_filter(self):
        context = Context(dialog=self.dialog, entities={}, history=[], counter=0)
        context.myentity = 1
        context.counter += 1
        context.myentity = 2
        context.counter += 1
        context.myentity = 3
        self.assertTrue('myentity' in context)
        self.assertFalse('myentityy' in context)
        self.assertFalse('myent' in context)
        self.assertEquals(context.counter, 2)
        self.assertEquals(context.myentity.current_v(), 3)
        self.assertEquals(context.myentity.latest_v(), 3)
        self.assertEquals(context.myentity.count(), 3)
        self.assertEquals(context.myentity.exactly(messages=1).latest_v(), 2)
        self.assertEquals(context.myentity.newer_than(messages=1).count(), 1)
        self.assertEquals(context.myentity.older_than(messages=1).count(), 1)
        self.assertEquals(context.myentity.older_than(messages=1).latest_v(), 1)
        self.assertEquals(context.myentity.older_than(messages=0).count(), 2)
        self.assertEquals(context.myentity.newer_than(messages=3).count(), 3)

    def test_set(self):
        context = Context(dialog=self.dialog, entities={}, history=[], counter=0)
        context.myent = "foo"
        context.foo = EntityValue(context, "foo", raw={"value": "foo"})
        self.assertEqual(context.myent.current_v(), "foo")
        self.assertEqual(context.foo.current_v(), "foo")
