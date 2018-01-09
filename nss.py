"""
Class to estimate the Nelson-Siegel-Svensson yield curve from an array of maturities and the corresponding yields
"""
__author__ = 'Dimitris'

import pandas as pd
import numpy as np
from scipy.optimize import least_squares
import logging

logger = logging.getLogger()
class NSS:
    # Class variable: Starting values for the least squares optimisation.
    # These will be updated with the optimal values once converge has be achieved to
    # help the optimiser when is called again at a later stage.
    p0 = [0.02351750, -0.0242402, 5.86996822, -5.90422588, 1.46142662, 1.46634330]

    def __init__(self, maturities, yields):
        df = pd.DataFrame([yields], columns = maturities)
        self.maturities = maturities
        self.yields = yields
        self.data = df

    def spline(self, x, params):
        beta1, beta2, beta3, beta4, lambda1, lambda2 = params
        term1 = beta1
        term2 = beta2 * ((1-np.exp(-x/lambda1)) / (x/lambda1))
        term3 = beta3 * ( ((1-np.exp(-x/lambda1)) / (x/lambda1)) - (np.exp(-x/lambda1)) )
        term4 = beta4 * ( ((1-np.exp(-x/lambda2)) / (x/lambda2)) - (np.exp(-x/lambda2)) )
        return term1 + term2 + term3 + term4

    def yield_curve(self, maturities, params):
        c = maturities
        nrows = self.data.shape[0]
        temp = pd.DataFrame([c]*nrows, columns=c)
        return temp.apply(self.spline, args=(params,))

    def residuals(self, params):
        fitted = self.yield_curve(self.maturities, params)
        err = self.data - fitted
        err = err.values[0]
        # sq_err = err**2
        # sse = sum(sq_err)
        return err

    def fit(self):
        p0 = NSS.p0
        plsq = least_squares(self.residuals, p0)
        if plsq['success'] is True:
            logging.info('NSS converged')
            NSS.p0 = plsq['x']  # update with the latest one
            return plsq['x']
        else:
            logger.warning('NSS fit did not converge!')
            return np.ones(np.size(p0))*np.nan




