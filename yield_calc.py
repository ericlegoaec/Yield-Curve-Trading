""" Script which for each gilt and for each date calculates its yield. It goes through the following steps:
    1) Selects all ISINs that appear in the last 4years
    2) Loops over the ISINs and for each date it retrieves the Nelson-Spiegel-Svensson parameters
    3) Calculated the yield for that ISIN on each date
    4) Save the estimated yields to the database
"""
__author__ = 'Dimitris'

import pandas as pd
from nss import NSS
import numpy as np
from utils import dbObj
import logging

logger = logging.getLogger()
logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
rootLogger = logging.getLogger()
rootLogger.setLevel(logging.DEBUG)

fileHandler = logging.FileHandler("{0}.log".format('yield_calc'), mode='w')
fileHandler.setFormatter(logFormatter)
rootLogger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
rootLogger.addHandler(consoleHandler)


# select the universe
engine = dbObj()
sqlStr = ' SELECT distinct ISIN_Code  FROM [Research].[dbo].[Gilts] '
sqlStr += " where Close_of_Business_Date > '01-Nov-2012' "
sqlStr += ' order by ISIN_Code '
connection = engine.connect()
codes = pd.read_sql(sqlStr, connection)


i = 1
for x in codes['ISIN_Code']:
    sqlStr = " select g.Close_of_Business_Date, g.ISIN_Code, g.Redemption_Date, g.Clean_Price, g.Dirty_Price, g.Yield, "
    sqlStr += " nss.beta1, nss.beta2, nss.beta3, nss.beta4, nss.lambda1, nss.lambda2 "
    sqlStr += " from Research.dbo.Gilts g "
    sqlStr += " left outer join[Research].[dbo].[nss_coeff] nss "
    sqlStr += " on "
    sqlStr += " g.Close_of_Business_Date = nss.[Date] "
    sqlStr += " where ISIN_Code = '%s' " % x
    sqlStr += " and g.Close_of_Business_Date > '01-Nov-2012' "
    sqlStr += " order by g.Close_of_Business_Date "
    rs = pd.read_sql(sqlStr, connection, index_col=['Close_of_Business_Date'])
    rs.index = pd.to_datetime(rs.index)
    rs.Redemption_Date = pd.to_datetime(rs.Redemption_Date)

    # Loop over the dates and estimate the yield
    cols = ['ISIN_Code', 'Redemption_Date', 'Estimated Yield']
    df = pd.DataFrame(np.ones([len(rs.index), len(cols)])*np.nan, index=rs.index, columns=cols)
    for dt in rs.index:
        s = rs.loc[dt]
        m = (s.loc['Redemption_Date'] - dt).days/365.0  # maturity in years
        nss = NSS(None, None)
        nss_coeff = [s.loc['beta1'], s.loc['beta2'], s.loc['beta3'], s.loc['beta4'], s.loc['lambda1'], s.loc['lambda2']]
        y = nss.yield_curve([m], nss_coeff)
        df.loc[dt] = [x, s.loc['Redemption_Date'], y.iloc[0, 0] * 100]

    logger.info("Loop %d of %d: Saving estimated yields for '%s' to the db..." % (i, len(codes['ISIN_Code']), x) )
    df.to_sql('est_yield', connection, if_exists='append', chunksize=100000 )
    i = i + 1

logging.info("Finished with yields estimation")
connection.dispose()
