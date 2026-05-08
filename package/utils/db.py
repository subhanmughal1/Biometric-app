import sqlite3
import os
import shutil
from package.utils.logger import Logger
from main import DATA_DIR

class DbHelper:   
    tableName = ''
    def __init__(self, db_name='', debug=False):    
        if(db_name == ''): db_name = 'app.db'    
        # Initialize the database connection and set up the environment.
        self.db_name = os.path.join(DATA_DIR, db_name)
        self.debug = debug
        
        try:
            self.connection = sqlite3.connect(self.db_name)
            self.connection.row_factory = sqlite3.Row  # Enable fetching rows as dictionaries
            self.cursor = self.connection.cursor()
        except sqlite3.Error as e:
            Logger.error(f"Error connecting to database: {e}")
            pass 

    def create_table(self, table_name, schema):
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({schema})"
        self.execute_query(query)

    def insert(self, table_name, data):
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        self.execute_query(query, tuple(data.values()))

    def update(self, table_name, data, where_clause, where_params):
        set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
        query = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"
        self.execute_query(query, tuple(data.values()) + where_params)

    def select(self, table_name, columns='*', where_clause=None, params=None, count=False):
        query = f"SELECT {columns} FROM {table_name}"
        if count:
            query = f"SELECT COUNT(*) FROM {table_name}"

        if where_clause:
            query += f" WHERE {where_clause}"
        self.execute_query(query, params or ())
        if count:
            result = self.cursor.fetchone()
            return result[0] if result else 0
        else:
            return [dict(row) for row in self.cursor.fetchall()]  # Convert rows to dictionaries

    def select_one(self, table_name, columns='*', where_clause=None, params=None):
        query = f"SELECT {columns} FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"
        self.execute_query(query, params or ())
        row = self.cursor.fetchone()
        return dict(row) if row else None  # Convert single row to dictionary

    def delete(self, table_name, where_clause, params=None):
        query = f"DELETE FROM {table_name} WHERE {where_clause}"
        self.execute_query(query, params or ())

    def drop_table(self, table_name):
        query = f"DROP TABLE IF EXISTS {table_name}"
        self.execute_query(query)

    def execute_query(self, query, params=None):
        if self.debug:
            print(f"Executing query: {query} | Params: {params}")     
        try:
            self.cursor.execute(query, params or ())
            self.connection.commit()            
        except sqlite3.Error as e:
            if self.debug:
                print("SQLite Error:", e)
            Logger.error(f"Error executing query: {e}")
            self.connection.rollback()

    def is_table_exist(self, table_name):
        query = """SELECT name FROM sqlite_master WHERE type='table' AND name=?"""
        self.execute_query(query, (table_name,))
        return self.cursor.fetchone() is not None

    def get_tables(self):
        query = """SELECT name FROM sqlite_master WHERE type='table'"""
        self.execute_query(query)
        return [row['name'] for row in self.cursor.fetchall()]
  
    def backup(self, backup_path):
        if not os.path.exists(backup_path):
            os.makedirs(backup_path)
        backup_file = os.path.join(backup_path, f"{self.db_name}.backup")
        shutil.copy2(self.db_name, backup_file)
  
    def __del__(self):        
        # Close the cursor and connection.
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()

    # ///////////////////////////////////////////////////////////////////
    def add(self, data):
        # add a new row
        self.insert(self.tableName, data)
        # Return the user ID of the last inserted row
        return self.cursor.lastrowid
    
    def save(self, rid, data):
        where_clause = "id = ?"
        params = (rid,)
        # add a new row
        self.update(self.tableName, data, where_clause, params)
        
    def remove(self, rid):
        # delete a row
        self.delete(self.tableName, 'id = ?', (rid,))
        
    def remove_where(self, where_clause, params=None):
        # delete a row
        self.delete(self.tableName, where_clause, params)
        
    def record(self, rid):
        row = self.select_one(self.tableName, '*', 'id = ?', (rid,) )
        if row:
            return row
        return None
    
    def records(self, columns='*', where_clause=None, params=None, count=False):
        rows = self.select(self.tableName, columns, where_clause, params,count)
        return rows
    # ///////////////////////////////////////////////////////////////////
    # initialize the db schema
    def initSchema(self):
        
        tableDevices  = "devices"

        devicesTableSchema = """
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            serial_number TEXT,
            vendor TEXT,
            status TEXT,
            ipaddress TEXT,
            port INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """
        
        # create the tables
        self.create_table(tableDevices,devicesTableSchema)