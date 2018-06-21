from typing import Optional

import importlib
import re

from golem.core.responses import AttachmentMessage
from .templates import Templates


class Flow:
    def __init__(self, name, dialog, definition):
        self.name = name
        self.dialog = dialog
        self.states = {}
        self.current_state_name = 'root'
        self.intent = definition.get('intent') or name
        for state_name, state_definition in definition['states'].items():
            self.states[state_name] = State(name + '.' + state_name, dialog=dialog, definition=state_definition)

    def get_state(self, state_name):
        return self.states.get(state_name)

    def __str__(self):
        return self.name + ":flow"


class State:
    def __init__(self, name, dialog, definition):
        from .dialog_manager import DialogManager
        self.name = name  # type: str
        self.dialog: DialogManager = dialog  # type: DialogManager
        self.intent_transitions = definition.get('intent_transitions') or {}
        self.intent = definition.get('intent')
        self.init = self.create_action(definition.get('init'))
        self.accept = self.create_action(definition.get('accept'))

    def create_action(self, definition):
        if not definition:
            return None
        if callable(definition):
            return definition
        template = definition.get('template')
        params = definition.get('params') or None
        if hasattr(Templates, template):
            fn = getattr(Templates, template)
        else:
            raise ValueError('Template %s not found, create a static method Templates.%s' % (template))

        return fn(**params)

    def get_intent_transition(self, intent):
        for key, state_name in self.intent_transitions.items():
            if re.match(key, intent): return state_name
        return None

    def __str__(self):
        return self.name + ":state"

    def __repr__(self):
        return str(self)


def require_one_of(entities=[]):
    def decorator_wrapper(func):
        def func_wrapper(state):
            all_entities = entities + ['intent', '_state']
            if not state.dialog.context.has_any(all_entities, max_age=0):
                print('No required entities present, moving to default.root: {}'.format(all_entities))
                return None, 'default.root:accept'
            return func(state)

        return func_wrapper

    return decorator_wrapper


class NewState:
    def __init__(self, name: str, action, intent=None, requires=None, is_temporary=False, is_blocking=False, supported: set=None):
        """
        Construct a conversation state.
        :param name:            name of this state
        :param action:          function that will run when moving to this state
        :param intent
        :param requires
        :param is_temporary     whether the action should fire just once,
                                 after that, the state will be used just as a basis for transitions
                                 and unrecognized messages will move to default.root instead.
        :param is_blocking      disallows all state changes caused by entities
        :param supported        entities that will not trigger a state change (- state can handle them)
        """
        self.name = str(name)
        self.action = action
        self.intent = intent
        self.requires = requires
        self.is_temporary = is_temporary
        self.is_blocking = is_blocking
        self.supported = supported or set()

    @staticmethod
    def load(definition: dict, relpath: Optional[str]) -> tuple:
        """
        Loads state from a dictionary definition.
        :param definition:      a dict containing the state definition (e.g. from YAML)
        :param relpath:         base path for relative action imports
        :return: tuple (state_name, state)
        """
        name = definition['name']
        action = None
        if 'action' in definition:
            action = definition['action']
            action = NewState.make_action(action, relpath)
        requires = NewState.parse_requirements(definition.get('require'), relpath)
        intent = definition.get("intent")
        is_temporary = definition.get("temporary", False)
        is_blocking = definition.get("block", False)
        supported = set(definition.get("supports", [])).union([r.entity for r in requires])  # TODO add local entities
        s = NewState(
            name=name,
            action=action,
            intent=intent,
            requires=requires,
            is_temporary=is_temporary,
            is_blocking=is_blocking,
            supported=supported
        )
        return name, s

    @staticmethod
    def make_action(action, relpath: Optional[str] = None):
        """
        Loads action from a definition.
        :param action:      either a string or a function pointer
        :param relpath:     base path for relative imports
        :return:    The loaded action, a function pointer.
        """

        if isinstance(relpath, str):
            relpath = relpath.replace("/", ".")

        if callable(action):
            # action already given as object, everything ok
            return action
        elif isinstance(action, str):
            # dynamically load the function

            try:
                rel_module, fn_name = action.rsplit(".", maxsplit=1)
                try:
                    abs_module = relpath + "." + rel_module
                    module = importlib.import_module(abs_module)
                except:
                    module = importlib.import_module(rel_module)

                fn = getattr(module, fn_name)
                return fn
            except Exception as e:
                raise ValueError("Action {} is undefined or malformed".format(action)) from e
        elif isinstance(action, dict):
            # load a static action, such as text or image
            return NewState.make_default_action(action)

        raise ValueError("Action class {} not supported".format(type(action)))

    @staticmethod
    def make_default_action(action_dict):
        """
        Creates an action from a non-function definition.
        :param action_dict:
        :return: The created action, a function pointer.
        """
        from golem.core.responses import TextMessage
        next = action_dict.get("next")
        message = None
        if 'type' in action_dict:
            type = action_dict['type'].lower()
            if type == 'qa':
                if 'context' not in action_dict:
                    raise ValueError("QA context not set")
                # TODO
            elif type == 'free_input': pass
            elif type == 'seq2seq': pass
            message = TextMessage("TO DO")
        elif 'text' in action_dict:
            message = TextMessage(action_dict['text'])
            if 'replies' in action_dict:
                message.with_replies(action_dict['replies'])
        elif 'image_url' in action_dict:
            message = AttachmentMessage('image', action_dict['image_url'])

        if not message:
            raise ValueError("Unknown action: {}".format(action_dict))
        return dynamic_response_fn(message, next)

    @staticmethod
    def parse_requirements(reqs_raw, relpath: Optional[str]):
        reqs = []
        if reqs_raw is None:
            return reqs

        for req in reqs_raw:
            reqs.append(Requirement(
                slot=req.get("slot"),
                entity=req.get("entity"),
                filter=req.get("filter"),
                action=NewState.make_action(req.get("action"), relpath)
            ))

        return reqs

    def set_requires(self, **kwargs):
        """Add required entities to this state. Useful to check for e.g. user's location."""
        self.requires.append(Requirement(**kwargs))
        return self

    def check_requirements(self, context) -> bool:
        """Checks whether the requirements of this state are met."""
        for requirement in self.requires:
            if not requirement.matches(context):
                return False
        return True

    def get_first_requirement(self, context):
        """Returns the first requirement of this state."""
        for requirement in self.requires:
            if not requirement.matches(context):
                return requirement
        return True

    def is_supported(self, msg_entities: list) -> bool:
        return self.is_blocking or not self.supported.isdisjoint(msg_entities)

    def __str__(self):
        return "state:" + self.name


class NewFlow:
    def __init__(self, name: str, states=None, intent=None):
        """
        Construct a new flow instance.
        :param name:   name of this flow
        :param states: dict of states (optional)
        :param intent: accepted intents regex (optional)
        """
        self.name = str(name)
        self.states = states or {}
        self.intent = intent or self.name
        self.accepted = set()

    @staticmethod
    def load(name, data: dict):
        relpath = data.get("relpath")  # directory of relative imports
        states = dict(NewState.load(s, relpath) for s in data["states"])
        intent = data.get("intent", name)
        flow = NewFlow(name=name, states=states, intent=intent)
        flow.accepted = set(data.get('accepts', {}))
        return flow

    def __getitem__(self, state_name: str):
        return self.states[state_name]

    def get_state(self, state_name: str):
        return self.states.get(state_name)

    def add_state(self, state: NewState):
        """Adds a state to this flow."""
        if isinstance(state, NewState):
            self.states[state.name] = state
            return self
        raise ValueError("Argument must be an instance of State")

    def get_state_for_intent(self, intent) -> str or None:
        """Returns name of the first state that receives an intent."""
        for name, state in self.states.items():
            if state.intent and re.match(state.intent, intent):
                return self.name + "." + name
        return None

    def matches_intent(self, intent) -> bool:
        """Checks whether this flow accepts an intent."""
        return re.match(intent, self.intent) is not None

    def set_accepts(self, entity_name):
        """Add accepted entity."""
        self.accepted.add(entity_name)
        return self

    def accepts_message(self, entities: list) -> bool:
        """Checks whether this flow accepts a message with given entities."""
        return len(self.accepted.union(entities)) > 0  # TODO or current state accepts it

    def __str__(self):
        return "flow:" + self.name


class Requirement():
    def __init__(self, slot, entity, filter=None, message=None, action=None):
        self.slot = slot
        self.entity = entity
        self.filter = filter
        self.action = action or dynamic_response_fn(message)
        if not self.action:
            raise ValueError("Requirement has no message nor action")

    def matches(self, context) -> bool:
        if self.entity not in context:
            return False
        if self.filter is not None:
            from golem.core.entity_query import EntityQuery
            # TODO move to new class PreparedFilter
            eq = EntityQuery.from_yaml(context, self.entity, self.filter)
            return eq.count() > 0
        return True


def load_flows_from_definitions(data: dict):
    flows = {}
    for flow_name, flow_definition in data.items():
        flow = NewFlow.load(flow_name, flow_definition)
        flows[flow_name] = flow
    return flows


def dynamic_response_fn(messages, next=None):
    def fn(dialog):
        dialog.send_response(messages, next)
    return fn
