"""
Script that estimates the parameters of the Nelson-Siegel-Svensson model and then constructs the term
structure for [1yr, 2yr, 3yr, 4yr, 5yr, 8yr, 10yr, 15yr, 20yr, 25yr, 30yr] maturities.
Both the parameters and the term structure are then save to the database
"""

__author__ = 'Dimitris'

from utils import dbObj
import pandas as pd
import numpy as np
from nss import NSS
import logging

logger = logging.getLogger()
logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
rootLogger = logging.getLogger()
rootLogger.setLevel(logging.DEBUG)

fileHandler = logging.FileHandler("{0}.log".format('main'), mode='w')
fileHandler.setFormatter(logFormatter)
rootLogger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
rootLogger.addHandler(consoleHandler)


logger.info('***** Starting *****')
sqlStr = " select distinct t.Close_of_Business_Date,  t.days_to_expiry, t.Yield from "
sqlStr += " ( "
sqlStr += " select *, datediff(day, Close_of_Business_Date, Redemption_Date)  as days_to_expiry "
sqlStr += " from research.dbo.gilts g "
sqlStr += " ) t "
sqlStr += " where t.days_to_expiry > 0 "
sqlStr += " and t.Close_of_Business_Date > '01-Nov-2012' "
sqlStr += " order by t.Close_of_Business_Date, t.days_to_expiry "

engine = dbObj()
connection = engine.connect()
rs = pd.read_sql(sqlStr, connection, index_col=['Close_of_Business_Date', 'days_to_expiry'])
connection.dispose()

rs = rs.unstack()
rs.columns = rs.columns.droplevel()
rs.index = pd.to_datetime(rs.index)
rs = rs.sort_index(ascending=False)
del rs.index.name
# rs = rs.tail()
# rs = rs.head()


maturities = [1, 2, 3, 4, 5, 8, 10, 15, 20, 25, 30]
dates = rs.index
nrows = len(dates)
ncols = len(maturities)
term_structure = pd.DataFrame(np.ones([nrows, ncols])*np.nan, index=dates, columns=['%syr' % x for x in maturities])
term_structure.index.name = 'Date'
coeff = pd.DataFrame(np.ones([nrows, 6])*np.nan, index=dates, columns=['beta1', 'beta2', 'beta3', 'beta4', 'lambda1', 'lambda2'])
coeff.index.name = 'Date'
for dt in dates:
    logger.info('Estimating yield curve for %s ', dt.strftime("%d-%b-%Y"))
    s = rs.loc[dt].dropna()
    years_to_expiry = s.index.values/365.0
    yield_rates = s.values/100.0
    # instantiate an object
    nss = NSS(years_to_expiry, yield_rates)
    # fit a Nelson-Siegel-Svensson spline and estimate it parameters
    nss_coeff = nss.fit()
    # Calc the yield for the pre-defined maturities
    yc = nss.yield_curve(maturities, nss_coeff)
    # Populate the dataframes with the relevant results. Yields are stored in %
    term_structure.loc[dt] = yc.values[0] * 100
    coeff.loc[dt] = nss_coeff

# save to the database
logger.info('Saving term structure to the db...')
engine = dbObj()
connection = engine.connect()
term_structure.to_sql('term_structure', connection, if_exists='replace', chunksize=100000 )
coeff.to_sql('nss_coeff', connection, if_exists='replace', chunksize=100000 )
connection.dispose()
logger.info('***** Done *****')


