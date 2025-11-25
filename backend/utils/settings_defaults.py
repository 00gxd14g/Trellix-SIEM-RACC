"""Default settings values for system and customer configuration."""

from copy import deepcopy

DEFAULT_GENERAL_SETTINGS = {
    'appName': 'RACC',
    'maxFileSize': 16,
    'defaultPageSize': 50,
    'enableNotifications': True,
    'notificationEmail': '',
    'backupEnabled': True,
    'backupFrequency': 'daily',
    'enableAuditLog': True,
    'sessionTimeout': 60,
    'theme': 'system',
}

DEFAULT_API_SETTINGS = {
    'apiBaseUrl': 'http://localhost:5000/api',
    'healthEndpoint': '/health',
    'apiKey': '',
    'authHeader': 'Authorization',
    'timeout': 15,
    'verifySsl': False,
    'pollInterval': 60,
}

DEFAULT_CUSTOMER_SETTINGS = {
    'maxAlarmNameLength': 128,
    'defaultSeverity': 50,
    'defaultConditionType': 14,
    'matchField': 'DSIDSigID',
    'summaryTemplate': (
        "Destination IP: [$Destination IP]\n"
        "Source IP: [$Source IP]\n"
        "Source Port: [$Source Port]\n"
        "Destination Port: [$Destination Port]\n"
        "Alarm Name: [$Alarm Name]\n"
        "Condition Type: [$Condition Type]\n"
        "Alarm Note: [$Alarm Note]\n"
        "Trigger Date: [$Trigger Date]\n"
        "Alarm Severity: [$Alarm Severity]\n"
        "Traffic Type: L2L / R2L"
    ),
    'defaultAssignee': 8199,
    'defaultEscAssignee': 57355,
    'defaultMinVersion': '11.6.14',
}


def get_all_defaults():
    return {
        'general': deepcopy(DEFAULT_GENERAL_SETTINGS),
        'api': deepcopy(DEFAULT_API_SETTINGS),
        'customer_defaults': deepcopy(DEFAULT_CUSTOMER_SETTINGS),
    }
