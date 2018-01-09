__author__ = 'Dimitris'
import pandas as pd
import numpy as np
from utils import dbObj


sqlStr = " select g.Close_of_Business_Date, g.ISIN_Code, g.Redemption_Date, g.Dirty_Price, g.Yield, y.[Estimated Yield], "
sqlStr += " g.Yield-y.[Estimated Yield] as yield_diff "
sqlStr += " from Research.dbo.gilts g "
sqlStr += " left outer join [Research].[dbo].[est_yield] y "
sqlStr += " on g.Close_of_Business_Date = y.Close_of_Business_Date "
sqlStr += " and "
sqlStr += " g.ISIN_Code = y.ISIN_Code "
sqlStr += " and "
sqlStr += " g.Redemption_Date = y.Redemption_Date "
sqlStr += " where g.Close_of_Business_Date > '01-Nov-2012' "
sqlStr += " and datediff(year, g.Close_of_Business_Date, g.Redemption_Date) >= 2 "

engine = dbObj()
connection = engine.connect()

rs = pd.read_sql(sqlStr, connection, index_col=['Close_of_Business_Date', 'ISIN_Code'])

# get the residuals (ie how much the actual yield is above or below the fitted one)
resid = rs.drop(['Redemption_Date', 'Estimated Yield', 'Yield', 'Dirty_Price'], axis=1)
resid = resid.unstack()
del resid.index.name
resid.columns = resid.columns.droplevel()
resid.index = pd.to_datetime(resid.index)

# score: 1 if actual yield is above the fitted, -1 is observed yield is below
score = resid.apply(np.sign)

# get the bond prices
p = rs.drop(['Redemption_Date', 'Estimated Yield', 'Yield', 'yield_diff'], axis=1)
p = p.unstack()
del p.index.name
p.columns = p.columns.droplevel()
p.index = pd.to_datetime(p.index)

# bond returns
ret = p.pct_change()

# partition the residuals into buckets
q = resid.apply(lambda x: pd.qcut(x, 5, labels=list(range(5))), axis=1)

# Keep only scores for the top and bottom buckets (ie those whose actual yield is too high (q=4) or too low (q==0) compared to the fitted yield)
score = score[(q == 0) | (q == 4)]

# portfolio return for each day
port_ret = score.shift().multiply(ret).sum(axis=1)

# sharpe ratio
sr = np.mean(port_ret) / np.std(port_ret) * np.sqrt(250)
print "Annualised sharpe ratio is %2.2f" % sr