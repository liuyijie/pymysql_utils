'''
Created on Sep 24, 2013

@author: paepcke
'''

# TODO: Test calling query() multiple times with several queries and get results alternately from the iterators
# TODO: In: cmd = 'INSERT INTO %s (%s) VALUES (%s)' % (str(tblName), ','.join(colNames), ','.join(map(str, colValues)))
#                 the map removes quotes from strings: ','join(map(str,('My poem', 10)) --> (My Poem, 10) 

# To run these tests, you need a local MySQL server,
# an account called 'unittest' on that server, and a
# database called 'unittest', also on that server.
#
# User unittest must be able to log in without a password, 
# the user only needs permissions for the unittest database.
# Here are the necessary MySQL commands:

#   CREATE USER unittest@localhost;
#   GRANT SELECT, INSERT, CREATE, DROP, ALTER, DELETE, UPDATE ON unittest.* TO unittest@localhost;


from collections import OrderedDict
import unittest
import subprocess

from pymysql_utils import MySQLDB, DupKeyAction

#*******TEST_ALL = True
TEST_ALL = False

#from mysqldb import MySQLDB
class TestMySQL(unittest.TestCase):
    '''

    '''

    def setUp(self):
        #self.mysqldb = MySQLDB(host='127.0.0.1', port=3306, user='unittest', passwd='', db='unittest')
        try:
            self.mysqldb = MySQLDB(host='localhost', port=3306, user='unittest', db='unittest')
        except ValueError as e:
            self.fail(str(e) + " (For unit testing, localhost MySQL server must have user 'unittest' without password, and a database called 'unittest')")


    def tearDown(self):
        self.mysqldb.dropTable('unittest')
        self.mysqldb.close()

    #*******@unittest.skipIf(not TEST_ALL, "Temporarily disabled")    
    def testCreateAndDropTable(self):
        mySchema = {
          'col1' : 'INT',
          'col2' : 'varchar(255)',
          'col3' : 'FLOAT',
          'col4' : 'TEXT',
          'col5' : 'JSON'
          }
        self.mysqldb.createTable('myTbl', mySchema, temporary=False)
        tbl_desc = subprocess.check_output([self.mysqldb.mysql_loc, 
                                           '-u',
                                           'unittest',
                                           'unittest',
                                           '-e',
                                           'DESC myTbl;'])
        expected = 'Field\tType\tNull\tKey\tDefault\tExtra\n' +\
                   'col4\ttext\tYES\t\tNULL\t\n' +\
                   'col5\tjson\tYES\t\tNULL\t\n' +\
                   'col2\tvarchar(255)\tYES\t\tNULL\t\n' +\
                   'col3\tfloat\tYES\t\tNULL\t\n' +\
                   'col1\tint(11)\tYES\t\tNULL\t\n'
        self.assertEqual(tbl_desc, expected)
        
        # Query mysql information schema to check for table
        # present. Use raw cursor to test independently from
        # the pymysql_utils query() method:
        
        self.mysqldb.dropTable('myTbl')
        cursor = self.mysqldb.connection.cursor()
        tbl_exists_query = '''
                  SELECT table_name 
                    FROM information_schema.tables 
                   WHERE table_schema = 'unittest' 
                     AND table_name = 'myTbl';
                     '''
        cursor.execute(tbl_exists_query)
        self.assertEqual(cursor.rowcount, 0)
        cursor.close()

    @unittest.skipIf(not TEST_ALL, "Temporarily disabled")    
    def testInsert(self):
        schema = OrderedDict([('col1','INT'), ('col2','TEXT')])
        self.mysqldb.createTable('unittest', schema)
        colnameValueDict = OrderedDict([('col1',10)])
        self.mysqldb.insert('unittest', colnameValueDict)
        self.assertEqual((10,None), self.mysqldb.query("SELECT * FROM unittest").next())
        #for value in self.mysqldb.query("SELECT * FROM unittest"):
        #    print value
 
    @unittest.skipIf(not TEST_ALL, "Temporarily disabled")    
    def testInsertSeveralColums(self):
        schema = OrderedDict([('col1','INT'), ('col2','TEXT')])
        self.mysqldb.createTable('unittest', schema)
        colnameValueDict = OrderedDict([('col1',10), ('col2','My Poem')])
        self.mysqldb.insert('unittest', colnameValueDict)
        res = self.mysqldb.query("SELECT * FROM unittest").next()
        self.assertEqual((10,'My Poem'), res)
         
    @unittest.skipIf(not TEST_ALL, "Temporarily disabled")    
    def testQueryIterator(self):
        self.buildSmallDb()
        for rowNum, result in enumerate(self.mysqldb.query('SELECT col1,col2 FROM unittest')):
            if rowNum == 0:
                self.assertEqual((10,'col1'), result)
            elif rowNum == 1:
                self.assertEqual((20,'col2'), result)
            elif rowNum == 2:
                self.assertEqual((30,'col3'), result)
    
    @unittest.skipIf(not TEST_ALL, "Temporarily disabled")    
    def testTruncate(self):
        self.buildSmallDb()
        self.mysqldb.truncateTable('unittest')
        try:
            self.mysqldb.query("SELECT * FROM unittest").next()
            self.fail()
        except StopIteration:
            pass
    
    @unittest.skipIf(not TEST_ALL, "Temporarily disabled")    
    def testExecuteArbitraryQuery(self):
        self.buildSmallDb()
        self.mysqldb.execute("UPDATE unittest SET col1=120")
        for result in self.mysqldb.query('SELECT col1 FROM unittest'):
            self.assertEqual((120,), result)
        
    @unittest.skipIf(not TEST_ALL, "Temporarily disabled")    
    def testExecuteArbitraryQueryParameterized(self):
        self.buildSmallDb()
        myVal = 130
        self.mysqldb.executeParameterized("UPDATE unittest SET col1=%s", (myVal,))
        for result in self.mysqldb.query('SELECT col1 FROM unittest'):
            self.assertEqual((130,), result)
        
    @unittest.skipIf(not TEST_ALL, "Temporarily disabled")    
    def testBulkInsert(self):
      
        # Build test db (this already tests basic bulkinsert):
        #                  col1   col2
        #                   10,  'col1'
        #                   20,  'col2'
        #                   30,  'col3'
        self.buildSmallDb()
        self.mysqldb.execute('ALTER TABLE unittest ADD PRIMARY KEY(col1)')
        
        # Provoke a MySQL error: duplicate primary key (i.e. 10): 
        # Add another row:  10,  'newCol1':
        colNames = ['col1','col2']
        colValues = [(10, 'newCol1')]
        
        warnings = self.mysqldb.bulkInsert('unittest', colNames, colValues)
        # Expect something like: 
        #    ['Level\tCode\tMessage', 
        #     "Warning\t1062\tDuplicate entry '10' for key 'PRIMARY'"
        #    ]
        self.assertEqual(len(warnings), 2)
            
        # First tuple should still be (10, 'col1'):
        self.assertTupleEqual(('col1',), self.mysqldb.query('SELECT col2 FROM unittest WHERE col1 = 10').next())
        
        # Try update again, but with replacement:
        warnings = self.mysqldb.bulkInsert('unittest', colNames, colValues, onDupKey=DupKeyAction.REPLACE)
        self.assertIsNone(warnings)
        # Now row should have changed:
        self.assertTupleEqual(('newCol1',), self.mysqldb.query('SELECT col2 FROM unittest WHERE col1 = 10').next())
        
        # Insert a row with duplicate key, specifying IGNORE:
        colNames = ['col1','col2']
        colValues = [(10, 'newCol2')]
        warnings = self.mysqldb.bulkInsert('unittest', colNames, colValues, onDupKey=DupKeyAction.IGNORE)
        # Still get a warning from MySQL for the ignored
        # dup key; so expect warnings to be the column
        # name header plus that one warning:
        self.assertEqual(len(warnings), 2)
        self.assertTupleEqual(('newCol1',), self.mysqldb.query('SELECT col2 FROM unittest WHERE col1 = 10').next())

    def buildSmallDb(self):
        schema = OrderedDict([('col1','INT'),('col2','TEXT')])
        self.mysqldb.dropTable('unittest')
        self.mysqldb.createTable('unittest', schema)
        colNames = ['col1','col2']
        colValues = [(10, 'col1'),(20,'col2'),(30,'col3')]
        warnings = self.mysqldb.bulkInsert('unittest', colNames, colValues)
        self.assertIsNone(warnings)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testQuery']
    unittest.main()