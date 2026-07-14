class AgentError(Exception):
    code = 'AGENT_ERROR'


class AgentLimitError(AgentError):
    code = 'AGENT_LIMIT_EXCEEDED'


class AgentCancelledError(AgentError):
    code = 'GENERATION_CANCELLED'

