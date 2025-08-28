import uuid

# Action, Condition, Job 클래스 정의
# 이 파일은 이전 아키텍처 제안과 동일합니다.

class Action:
    def __init__(self, action_type, params=None):
        self.id = str(uuid.uuid4())
        self.type = action_type
        self.params = params if params is not None else {}

    def to_dict(self):
        return {"id": self.id, "type": self.type, "params": self.params}

    @staticmethod
    def from_dict(data):
        action = Action(data['type'], data.get('params', {}))
        action.id = data.get('id', str(uuid.uuid4()))
        return action

class Condition:
    def __init__(self, condition_type, params=None, enabled=True):
        self.id = str(uuid.uuid4())
        self.type = condition_type
        self.params = params if params is not None else {}
        self.enabled = enabled
        self.actions = []

    def add_action(self, action):
        self.actions.append(action)

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "params": self.params,
            "enabled": self.enabled,
            "actions": [action.to_dict() for action in self.actions]
        }

    @staticmethod
    def from_dict(data):
        condition = Condition(data['type'], data.get('params', {}), data.get('enabled', True))
        condition.id = data.get('id', str(uuid.uuid4()))
        condition.actions = [Action.from_dict(act_data) for act_data in data.get('actions', [])]
        return condition

class Job:
    def __init__(self, name, process_name):
        self.name = name
        self.process_name = process_name
        self.conditions = []

    def add_condition(self, condition):
        self.conditions.append(condition)

    def find_condition_by_id(self, condition_id):
        for cond in self.conditions:
            if cond.id == condition_id:
                return cond
        return None

    def remove_condition_by_id(self, condition_id):
        self.conditions = [cond for cond in self.conditions if cond.id != condition_id]

    def to_dict(self):
        return {
            "name": self.name,
            "process_name": self.process_name,
            "conditions": [condition.to_dict() for condition in self.conditions]
        }

    @staticmethod
    def from_dict(data):
        job = Job(data['name'], data['process_name'])
        job.conditions = [Condition.from_dict(cond_data) for cond_data in data.get('conditions', [])]
        return job