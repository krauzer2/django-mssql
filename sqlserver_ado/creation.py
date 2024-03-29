# This dictionary maps Field objects to their associated Server Server column
# types, as strings. Column-type strings can contain format strings; they'll
# be interpolated against the values of Field.__dict__.
from django.conf import settings
from django.db.backends.creation import BaseDatabaseCreation, TEST_DATABASE_PREFIX
import sys

class DatabaseCreation(BaseDatabaseCreation):
    data_types = {
        'AutoField':            'int IDENTITY (1, 1)',
        'BigAutoField':         'bigint IDENTITY (1, 1)',
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

    def _disable_transactions(self, verbosity=1):
        """Temporarily turn off transactions for non-transactionable SQL"""
        if self.connection.connection.supportsTransactions:
            if verbosity >= 1:
                print "Disabling Transactions"
            self._supports_transactions = self.connection.connection.supportsTransactions
            self.connection._commit()
            self.connection.connection.supportsTransactions = False

    def _reenable_transactions(self, verbosity=1):
        """Reset transaction support to state prior to _disable_transactions() call"""
        if hasattr(self, '_supports_transactions'):
            if verbosity >= 1:
                print "Re-enabling Transactions"
            self.connection.connection.supportsTransactions = self._supports_transactions

    def create_test_db(self, verbosity=1, autoclobber=False):
        """
        Duplicate of BaseDatabaseCreation.create_test_db to disable broken Site id coersion.
        Fixes django #17467 that was introduced by django #15573.
        """
        # Don't import django.core.management if it isn't needed.
        from django.core.management import call_command

        test_database_name = self._get_test_db_name()

        if verbosity >= 1:
            test_db_repr = ''
            if verbosity >= 2:
                test_db_repr = " ('%s')" % test_database_name
            print "Creating test database for alias '%s'%s..." % (self.connection.alias, test_db_repr)

        self._create_test_db(verbosity, autoclobber)

        self.connection.close()
        self.connection.settings_dict["NAME"] = test_database_name

        # Confirm the feature set of the test database
        self.connection.features.confirm()

        # Report syncdb messages at one level lower than that requested.
        # This ensures we don't get flooded with messages during testing
        # (unless you really ask to be flooded)
        call_command('syncdb',
            verbosity=max(verbosity - 1, 0),
            interactive=False,
            database=self.connection.alias,
            load_initial_data=False)

        # We need to then do a flush to ensure that any data installed by
        # custom SQL has been removed. The only test data should come from
        # test fixtures, or autogenerated from post_syncdb triggers.
        # This has the side effect of loading initial data (which was
        # intentionally skipped in the syncdb).
        call_command('flush',
            verbosity=max(verbosity - 1, 0),
            interactive=False,
            database=self.connection.alias)
        
        # One effect of calling syncdb followed by flush is that the id of the
        # default site may or may not be 1, depending on how the sequence was
        # reset.  If the sites app is loaded, then we report a mismatch.
        from django.db.models import get_model
        if 'django.contrib.sites' in settings.INSTALLED_APPS:
            Site = get_model('sites', 'Site')
            if Site is not None and Site.objects.using(self.connection.alias).count() == 1:
                site_id = Site.objects.using(self.connection.alias).all().values_list('id', flat=True)[0]
                
                if site_id != settings.SITE_ID:
                     print "settings.SITE_ID does not match Site object. This may cause some tests to fail."

        from django.core.cache import get_cache
        from django.core.cache.backends.db import BaseDatabaseCache
        for cache_alias in settings.CACHES:
            cache = get_cache(cache_alias)
            if isinstance(cache, BaseDatabaseCache):
                from django.db import router
                if router.allow_syncdb(self.connection.alias, cache.cache_model_class):
                    call_command('createcachetable', cache._table, database=self.connection.alias)

        # Get a cursor (even though we don't need one yet). This has
        # the side effect of initializing the test database.
        cursor = self.connection.cursor()

        return test_database_name


    def _create_test_db(self, verbosity=1, autoclobber=False):
        test_database_name = self._test_database_name(settings)
        
        if not self._test_database_create(settings):
            if verbosity >= 1:
                print "Skipping Test DB creation"
            return test_database_name

        # Create the test database and connect to it. We need to autocommit
        # if the database supports it because PostgreSQL doesn't allow
        # CREATE/DROP DATABASE statements within transactions.
        cursor = self.connection.cursor()
        suffix = self.sql_table_creation_suffix()
        qn = self.connection.ops.quote_name

        try:
            self._disable_transactions()
            cursor.execute("CREATE DATABASE %s %s" % (qn(test_database_name), suffix))
            self._reenable_transactions()
        except Exception, e:
            sys.stderr.write("Got an error creating the test database: %s\n" % e)
            if not autoclobber:
                confirm = raw_input("Type 'yes' if you would like to try deleting the test database '%s', or 'no' to cancel: " % test_database_name)
            if autoclobber or confirm == 'yes':
                try:
                    self._disable_transactions()
                    if verbosity >= 1:
                        print "Destroying old test database..."
                    cursor.execute("DROP DATABASE %s" % qn(test_database_name))
                    if verbosity >= 1:
                        print "Creating test database..."
                    cursor.execute("CREATE DATABASE %s %s" % (qn(test_database_name), suffix))
                    self._reenable_transactions()
                except Exception, e:
                    sys.stderr.write("Got an error recreating the test database: %s\n" % e)
                    sys.exit(2)
            else:
                print "Tests cancelled."
                sys.exit(1)

        return test_database_name
        

    def _destroy_test_db(self, test_database_name, verbosity=1):
        "Internal implementation - remove the test db tables."

        if self._test_database_create(settings):
            qn = self.connection.ops.quote_name

            # Remove the test database to clean up after
            # ourselves. Connect to the previous database (not the test database)
            # to do so, because it's not allowed to delete a database while being
            # connected to it.
            cursor = self.connection.cursor()
            self.set_autocommit()
            import time
            time.sleep(1) # To avoid "database is being accessed by other users" errors.
            self._disable_transactions()
            cursor.execute("DROP DATABASE %s" % self.connection.ops.quote_name(test_database_name))
            self._reenable_transactions()
            self.connection.close()
        else:
            print "Skipping Test DB destruction"    
        
    def _test_database_create(self, settings):
        if self.connection.settings_dict.has_key('TEST_CREATE'):
            return self.connection.settings_dict.get('TEST_CREATE', True)
        if hasattr(settings, 'TEST_DATABASE_CREATE'):
            return settings.TEST_DATABASE_CREATE
        else:
            return True

    def _test_database_name(self, settings):
        try:
            name = TEST_DATABASE_PREFIX + self.connection.settings_dict['NAME']
            if self.connection.settings_dict['TEST_NAME']:
                name = self.connection.settings_dict['TEST_NAME']
        except AttributeError:
            if hasattr(settings, 'TEST_DATABASE_NAME') and settings.TEST_DATABASE_NAME:
                name = settings.TEST_DATABASE_NAME
            else:
                name = TEST_DATABASE_PREFIX + settings.DATABASE_NAME
        return name
