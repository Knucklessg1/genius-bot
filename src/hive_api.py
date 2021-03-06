#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import warnings
import pypyodbc as pyodbc
import pandas as pd
import sqlalchemy as sqla
import sqlalchemy.exc
import time
import os
from sqlalchemy.dialects import registry
from log import Log


# The Hive API is meant to connect and interact with Hive Environments with less coding involvement.
# Simply conifgure your ODBC Hive connection, and point your DSN connection to the one you defined.
class HiveAPI:
    conn = None
    cursor = None
    conn_str = None
    engine = None
    report_name = "report_export"
    report_name_csv = str(report_name) + ".csv"
    report_name_xlsx = str(report_name) + ".xlsx"
    save_directory = os.getcwd()
    csv_export = save_directory + '\\' + report_name_csv
    excel_export = save_directory + '\\' + report_name_xlsx
    df_final = None
    logger = None
    logging_file = ""
    logging_dir = ""
    error = 0

    # Initialize the Class
    def __init__(self, logger=None):
        # This uses SQLAlchemy's Registrar to Register the PyHive custom dialect
        registry.register("hive", "pyhive.sqlalchemy_hive", "HiveDialect")
        # This will initializing a logging instance to capture all errors in a file.
        if logger:
            self.log = logger
        else:
            self.log = Log()
            self.log.init_logging()
            self.log.log_stdout()
            self.log.log_stderr()

        # This attempts to establish the database connection
        print("Testing Conn")
        try:
            self.conn = pyodbc.connect("DSN=Hive_connection", autocommit=True)
            self.conn.timeout = 0
            # Cloudera ODBC Driver for Apache Hive
            self.log.info("Connected Part 1 to Hadoop Cluster")
            print("Connected to Hadoop Cluster Using: ", self.conn.getinfo(pyodbc.SQL_DRIVER_NAME))
            self.cursor = self.conn.cursor()
            self.log.info("Created Cursor")
            self.cursor.execute('set tez.queue.name=tda_adhoc;')
            self.cursor.execute('set hive.execution.engine = tez;')
            self.cursor.execute('set hive.vectorized.execution.reduce.enabled = true;')
            self.log.info("Created Cursor and executed commands, Now creating SQL Alchemy Engine")
            # logging.basicConfig(level=logging.DEBUG)
            self.create_sqlalchemy_engine("host")
            self.log.info("Connected Part 2 to Hadoop Cluster Completed")
            self.error = 0
        except Exception as e:
            self.log.info("Unable to Connect to Database")
            self.error = 1
            print("Unable to connect to the Database: ", e)

    def get_error(self):
        return self.error

    # Method to get a query
    def get_query(self, query):
        queried_list = []
        print("Executing Query")
        self.cursor.execute(query)
        print("Query Executed")
        for row in self.cursor:
            queried_list.append(str(row))
            print(row)
        return queried_list

    # Method to insert
    def insert_query(self, query):
        print("Executing Query")
        self.cursor.execute(query)
        print("Query Executed")

    # Method to create a table
    def create_table(self, query):
        print("Executing Query")
        self.cursor.execute(query)
        print("Query Executed")

    # Method to drop a table
    def drop_table(self, query):
        print("Executing Query")
        self.cursor.execute(query)
        print("Query Executed")

    # Return connection details
    def get_conn(self):
        return self.conn

    # Write DataFrame to Database
    def write_df(self, df, table_name, dtype):
        try:
            print("Writing Data Frame to Hadoop Database")
            start = time.time()
            df.to_sql(table_name, con=self.engine, if_exists='append', dtype=dtype, index=True, schema='tda_sb_bqoe',
                      chunksize=10000)  # , confOverlay=None, runAsync=False, queryTimeout=0)
            end = time.time()
            print("Time to Complete Task: " + str(end - start) + " seconds")
        except sqla.exc.IntegrityError as Exception_e:
            print(
                "Could Not write DataFrame to Database.\nIntegrity Error May be a result of trying to insert a primary key column that is auto-generated by the DB\nAdditional Error Information: ",
                Exception_e)

    # Read Table into DataFrame
    def read_df(self, sql):
        self.log.info("Reading Table into Dataframe")
        print("Reading Table into Pandas Data Frame")
        try:
            start = time.time()
            df = pd.read_sql(sql, self.conn)
            print("Dataframe: ", df)
            end = time.time()
            print("Time to Complete Task: " + str(end - start) + " seconds")
            self.df_final = df
            self.log.info("Reading Table Completed")
            self.error = 0
            return df
        except Exception as e:  # print(e)(pd.io.sql.DatabaseError, AttributeError) as Exception_e:
            print("Error Reading Dataframe from Database: ", e)
            self.error = 1
            return pd.DataFrame()

    # Obtain Data Types of Current Data Frame
    @staticmethod
    def df_dtype(df):
        print("Determining Data Types for Columns")
        return df.dtypes

    # Create a SQLAlchemy Connection Engine for Pandas.to_sql function
    def create_sqlalchemy_engine(self, host):
        self.log.info("Creating SQL Alchemy Engine in FUNCTIONS")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=sqla.exc.SAWarning)
            self.engine = sqla.create_engine(host,
                                             connect_args={'auth': 'KERBEROS', 'kerberos_service_name': 'hive'})
        self.log.info("SQLAlchemy Engine Created")

    # Close cursor and connection(self):
    def close_conn(self):
        self.cursor.close()
        self.conn.close()
        print("Connection closed successfully")
        # self.engine.close()

    def set_report_name(self, report_name):
        if report_name != "":
            print("Report Name: ", report_name)
            self.report_name = report_name
            self.csv_export = self.save_directory + '\\' + str(self.report_name) + ".csv"
            self.excel_export = self.save_directory + '\\' + str(self.report_name) + ".xlsx"
        else:
            print("Report Name was Blank")

    def get_report_name(self):
        return self.report_name

    def set_save_directory(self, directory):
        self.save_directory = directory
        print("New Directory: ", self.save_directory)
        self.csv_export = self.save_directory + '\\' + self.report_name_csv
        self.excel_export = self.save_directory + '\\' + self.report_name_xlsx

    def export_data(self, csv_flag):
        print("Exporting Data")
        if csv_flag == 1:
            self.df_final.to_csv(self.csv_export, index=False)
            print("Exported to CSV Complete!")
        else:
            self.df_final.to_excel(self.excel_export, index=False, engine='xlsxwriter')
            print("Exported to Excel Complete!")
