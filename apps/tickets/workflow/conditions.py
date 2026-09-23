"""Bounded, structured conditions evaluated only against an instance snapshot."""
import math
import re

from .errors import WorkflowConfigurationError

OPERATORS = {'eq', 'ne', 'gt', 'gte', 'lt', 'lte', 'in', 'not_in', 'contains', 'exists'}
ROOTS = {'applicant', 'asset', 'assets', 'account', 'accounts', 'request', 'duration', 'risk_level', 'risk', 'actions', 'nodes'}
MISSING = object()
RISK_LEVELS = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}


def validate_condition(condition, depth=0):
    if depth > 8 or not isinstance(condition, dict):
        raise WorkflowConfigurationError('Conditions must be objects nested at most eight levels.')
    groups = {'and', 'or', 'not'} & condition.keys()
    if groups:
        if len(condition) != 1:
            raise WorkflowConfigurationError('A compound condition must have exactly one operator.')
        key = next(iter(groups))
        children = [condition[key]] if key == 'not' else condition[key]
        if not isinstance(children, list) or not 1 <= len(children) <= 32:
            raise WorkflowConfigurationError('Condition groups must contain between 1 and 32 conditions.')
        for child in children:
            validate_condition(child, depth + 1)
        return
    if not {'field', 'operator', 'value'} <= condition.keys() or condition.keys() - {'field', 'operator', 'value', 'quantifier'}:
        raise WorkflowConfigurationError('Conditions require field, operator and value.')
    field, operator, value = condition['field'], condition['operator'], condition['value']
    if not isinstance(field, str) or len(field) > 256 or not re.fullmatch(r'[a-zA-Z][\w]*(?:\.[\w]+)*', field):
        raise WorkflowConfigurationError('Invalid condition field path.')
    if field.split('.')[0] not in ROOTS:
        raise WorkflowConfigurationError('Unknown workflow context field.')
    if not isinstance(operator, str) or operator not in OPERATORS:
        raise WorkflowConfigurationError('Unknown condition operator.')
    if condition.get('quantifier', 'any') not in ('any', 'all'):
        raise WorkflowConfigurationError('The condition quantifier must be any or all.')
    if operator == 'exists' and not isinstance(value, bool):
        raise WorkflowConfigurationError('exists requires a boolean value.')
    if operator in ('in', 'not_in') and not isinstance(value, list):
        raise WorkflowConfigurationError('in and not_in require a list value.')
    if operator in ('gt', 'gte', 'lt', 'lte'):
        if field in ('risk_level', 'risk.level'):
            if isinstance(value, str) and value in RISK_LEVELS:
                return
            raise WorkflowConfigurationError('Risk comparisons require low, medium, high or critical.')
        if not is_number(value):
            raise WorkflowConfigurationError('Ordered comparisons require a number or a known risk level.')


def is_number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def values_at_path(context, field):
    parts = field.split('.')
    # The singular spelling in the domain DSL means each requested asset/account.
    if parts[0] in ('asset', 'account') and parts[0] not in context:
        parts[0] += 's'

    def walk(value, remaining):
        if not remaining:
            return [value]
        if isinstance(value, list):
            return [item for child in value for item in walk(child, remaining)] or [MISSING]
        if not isinstance(value, dict) or remaining[0] not in value:
            return [MISSING]
        return walk(value[remaining[0]], remaining[1:])

    return walk(context, parts)


def equal(left, right):
    if is_number(left) and is_number(right):
        return left == right
    return type(left) is type(right) and left == right


def compare(actual, operator, expected, field):
    if operator == 'exists':
        return (actual is not MISSING and actual is not None) == expected
    if actual is MISSING or actual is None:
        raise WorkflowConfigurationError(f'Missing condition context: {field}.')
    if operator in ('eq', 'ne'):
        if type(actual) is not type(expected) and not (is_number(actual) and is_number(expected)):
            raise WorkflowConfigurationError(f'Incompatible condition value types: {field}.')
        result = equal(actual, expected)
        return result if operator == 'eq' else not result
    if operator in ('in', 'not_in'):
        result = any(equal(actual, item) for item in expected)
        return result if operator == 'in' else not result
    if operator == 'contains':
        if isinstance(actual, list):
            return any(equal(item, expected) for item in actual)
        if isinstance(actual, (str, dict)) and isinstance(expected, str):
            return expected in actual
        raise WorkflowConfigurationError(f'Invalid contains operand: {field}.')
    if field in ('risk_level', 'risk.level'):
        if not isinstance(actual, str) or actual not in RISK_LEVELS:
            raise WorkflowConfigurationError('Unknown risk level in the snapshot.')
        actual, expected = RISK_LEVELS[actual], RISK_LEVELS[expected]
    if not is_number(actual) or not is_number(expected):
        raise WorkflowConfigurationError(f'Invalid ordered comparison: {field}.')
    return {'gt': actual > expected, 'gte': actual >= expected,
            'lt': actual < expected, 'lte': actual <= expected}[operator]


def evaluate_condition(condition, context):
    validate_condition(condition)

    def evaluate(item):
        # Evaluate all children so incomplete snapshots never silently select a path.
        if 'and' in item:
            return all([evaluate(child) for child in item['and']])
        if 'or' in item:
            return any([evaluate(child) for child in item['or']])
        if 'not' in item:
            return not evaluate(item['not'])
        values = values_at_path(context, item['field'])
        results = [compare(value, item['operator'], item['value'], item['field']) for value in values]
        default = 'all' if item['operator'] in ('ne', 'not_in') else 'any'
        return (all if item.get('quantifier', default) == 'all' else any)(results)

    return evaluate(condition)
