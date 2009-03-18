# This dictionary maps Field objects to their associated Server Server column
# types, as strings. Column-type strings can contain format strings; they'll
# be interpolated against the values of Field.__dict__.
from django.db.backends.creation import BaseDatabaseCreation

class DatabaseCreation(BaseDatabaseCreation):
    data_types = {
        'AutoField':            'int IDENTITY (1, 1)',
        'BigIntegerField':      'bigint',
        'BooleanField':         'bit',
        'CharField':            'nvarchar(%(max_length)s)',
        'CommaSeparatedIntegerField': 'nvarchar(%(max_length)s)',
        'DateField':            'datetime',
        'DateTimeField':        'datetime',
        'DecimalField':         'decimal(%(max_digits)s, %(decimal_places)s)',
        'FileField':            'nvarchar(%(max_length)s)',
        'FilePathField':        'nvarchar(%(max_length)s)',
        'FloatField':           'double precision',
        'IntegerField':         'int',
        'IPAddressField':       'nvarchar(15)',
        'NullBooleanField':     'bit',
        'OneToOneField':        'int',
        'PositiveIntegerField': 'int CHECK ([%(column)s] >= 0)',
        'PositiveSmallIntegerField': 'smallint CHECK ([%(column)s] >= 0)',
        'SlugField':            'nvarchar(%(max_length)s)',
        'SmallIntegerField':    'smallint',
        'TextField':            'nvarchar(max)',
        'TimeField':            'datetime',
    }
