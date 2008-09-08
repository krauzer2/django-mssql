import unittest

# Django settings for testbackend project.
def hack_path():
    import os, sys
    common_path = os.path.join(os.path.abspath(os.path.dirname(".")), "..")
    sys.path.append(common_path)

hack_path()
from dbsettings import *

from sqlserver_ado import dbapi
import dbapi20

class test_dbapi(dbapi20.DatabaseAPI20Test):
    driver = dbapi
    connect_args = [ make_connection_string() ]
    
    def _try_run(self, *args):
        con = self._connect()
        cur = None
        try:
            cur = con.cursor()
            for arg in args:
                cur.execute(arg)
        finally:
            try:
                if cur is not None:
                    cur.close()
            except: pass
            con.close()
        
    
    # This should create the "lower" sproc.
    def _callproc_setup(self):
        self._try_run(
            """IF OBJECT_ID(N'[dbo].[to_lower]', N'P') IS NOT NULL DROP PROCEDURE [dbo].[to_lower]""",
            """
CREATE PROCEDURE to_lower
    @input nvarchar(max)
AS
BEGIN
    select LOWER(@input)
END
""",
            )
    
    # This should create a sproc with a return value.
    def _retval_setup(self):
        self._try_run(
            """IF OBJECT_ID(N'[dbo].[add_one]', N'P') IS NOT NULL DROP PROCEDURE [dbo].[add_one]""",
            """
CREATE PROCEDURE add_one
    @input int
AS
BEGIN
    return @input+1
END
""",
            )

    def test_retval(self):
        self._retval_setup()
        con = self._connect()
        try:
            cur = con.cursor()
            if hasattr(cur,'callproc'):
                cur.callproc('add_one',(1,))
                r = cur.returnValue
                self.assertEqual(r, 2, 'retval produced invalid reults: %s' % (r,))
        finally:
            con.close()
    
    # Don't need exceptions mirrored on connections.
    def test_ExceptionsAsConnectionAttributes(self): 
        pass
        
    # Don't need setoutputsize tests.
    def test_setoutputsize(self): 
        pass
        
    def test_nextset(self):
        print "Multiple recordset test skipped."
   
suite = unittest.makeSuite(test_dbapi, 'test')
testRunner = unittest.TextTestRunner(verbosity=9)
print testRunner.run(suite)
