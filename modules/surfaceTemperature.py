import numpy as np
from constants import *
from cpkernel.io import *
from scipy.optimize import minimize
import sys

def energy_balance(x, GRID, SWnet, rho, Cs, T2, u2, q2, p, Li, lam, SLOPE):

    if x >= zero_temperature:
        Lv = lat_heat_vaporize
    else:
        Lv = lat_heat_sublimation

    # Saturation vapour pressure at the surface
    if saturation_water_vapour_method == 'Sonntag90':

        Ew0 = method_EW_Sonntag(x)

    else:
        print('Method for saturation water vapour ', saturation_water_vapour_method,
              ' not availalbe using default method, using default')

        Ew0 = method_EW_Sonntag(x)
    
    # Bulk Richardson number
    if (u2!=0):
        Ri = (9.81 * (T2 - x) * 2.0) / (T2 * np.power(u2, 2))
    else:
        Ri = 0
    
    # Stability correction
    if (Ri > 0.01) & (Ri <= 0.2):
        phi = np.power(1-5*Ri,2)
    elif Ri > 0.2:
        phi = 0
    else:
        phi = 1
    
    # Sensible heat flux
    H = rho * spec_heat_air * Cs * u2 * (T2-x) * phi * np.cos(np.radians(SLOPE))

    # Mixing ratio at surface
    q0 = (100.0 * 0.622 * (Ew0 / (p - Ew0))) / 100.0

    # Latent heat flux
    L = rho * Lv * Cs * u2 * (q2-q0) * phi * np.cos(np.radians(SLOPE))

    # Outgoing longwave radiation
    Lo = -surface_emission_coeff * sigma * np.power(x, 4.0)

    # Ground heat flux
    #B = lam * ((2.0 * GRID.get_node_temperature(1) - (0.5 * ((3.0 * x) + GRID.get_node_temperature(2)))) /\
    #           (GRID.get_node_height(0))) * np.cos(np.radians(SLOPE))
   
    B = lam * (GRID.get_node_temperature(1)-x)/(GRID.get_node_depth(1)-GRID.get_node_depth(0))

    # Return residual of energy balance
    return np.abs(SWnet+Li+Lo+H+L+B)

def update_surface_temperature(GRID, alpha, z0, T2, rH2, p, G, u2, SLOPE, LWin=None, N=None):
    """ This methods updates the surface temperature and returns the surface fluxes
       """
    # start module logging
    logger = logging.getLogger(__name__)
        
    # Saturation vapour pressure (hPa)
    if saturation_water_vapour_method == 'Sonntag90':
        Ew = method_EW_Sonntag(T2)
    else:
        print('Method for saturation water vapour ', saturation_water_vapour_method, ' not available, using default')
        Ew = method_EW_Sonntag(T2)

    # Water vapour at 2 m (hPa)
    Ea = (rH2 * Ew) / 100.0

    # Calc incoming longwave radiation, if not available Ea has to be in Pa (Konzelmann 1994)
    if LWin is None:
        eps_cs = 0.23 + 0.433 * np.power(100*Ea/T2,1.0/8.0)
        #eps_cs = 1.24 * np.power(100*Ea/T2,1.0/7.0)
        eps_tot = eps_cs * (1 - np.power(N,2)) + 0.984 * np.power(N,2)
        Li = eps_tot * sigma * np.power(T2,4.0)
    else:
    # otherwise use LW data from file
        Li = LWin

    # Mixing Ratio at 2 m or calculate with other formula? 0.622*e/p = q
    q2 = (rH2 * 0.622 * (Ew / (p - Ew))) / 100.0
    
    # Air density 
    rho = (p*100.0) / (287.058 * (T2 * (1 + 0.608 * q2)))

    # Total net shortwave radiation
    SWnet = G * (1-alpha)

    # Bulk transfer coefficient 
    Cs = np.power(0.41,2.0) / np.power(np.log(2.0/(z0)),2)
    
    #hm = GRID.get_node_height(0)+GRID.get_node_height(1)+GRID.get_node_height(2)
    lam = GRID.get_node_thermal_conductivity(0) 
    
    #(GRID.get_node_height(0)*GRID.get_node_thermal_conductivity(0) + GRID.get_node_height(1)*GRID.get_node_thermal_conductivity(1) \
    #        + GRID.get_node_height(2)*GRID.get_node_thermal_conductivity(2))/hm

    res = minimize(energy_balance, GRID.get_node_temperature(0), method='L-BFGS-B', bounds=((220.0, 273.16),),
                   tol=1e-8, args=(GRID, SWnet, rho, Cs, T2, u2, q2, p, Li, lam, SLOPE))
 
    # Set surface temperature
    GRID.set_node_temperature(0, float(res.x))

    # Bulk Richardson number
    if (u2!=0):
        Ri = (9.81 * (T2 - res.x) * 2.0) / (T2 * np.power(u2, 2))
    else:
        Ri = 0
    
    # Stability correction
    if (Ri > 0.01) & (Ri <= 0.2):
        phi = np.power(1-5*Ri,2)
    elif Ri > 0.2:
        phi = 0
    else:
        phi = 1
    
    if res.x >= zero_temperature:
        Lv = lat_heat_vaporize
    else:
        Lv = lat_heat_sublimation

    # Sensible heat flux
    H = rho * spec_heat_air * Cs * u2 * (T2-res.x) * phi * np.cos(np.radians(SLOPE))

    # Saturation vapour pressure at the surface
    Ew0 = 6.112 * np.exp((17.67*(res.x-273.16)) / ((res.x-29.66)))
    
    # Mixing ratio at surface
    q0 = (100.0 * 0.622 * (Ew0/(p-Ew0))) / 100.0

    # Latent heat flux
    L = rho * Lv * Cs * u2 * (q2-q0) * phi * np.cos(np.radians(SLOPE))

    # Outgoing longwave radiation
    Lo = -surface_emission_coeff * sigma * np.power(res.x, 4.0)

    # Ground heat flux
    #B = lam * ((2 * GRID.get_node_temperature(1) - (0.5 * ((3 * res.x) + GRID.get_node_temperature(2)))) /\
    #            (GRID.get_node_height(0))) * np.cos(np.radians(SLOPE))

    B = lam * (GRID.get_node_temperature(1)-res.x)/(GRID.get_node_depth(1)-GRID.get_node_depth(0))

    qdiff = q0-q2

    if float(res.x)>273.16:
        logger.error('Surface temperature exceeds 273.16 K')
        logger.error(GRID.get_node_temperature(0))

    return res.fun, float(res.x), float(Li), float(Lo), float(H), float(L), float(B), float(SWnet), rho, Lv, Cs, q0, q2, qdiff, phi



def method_EW_Sonntag(Temp):
    Ew = 6.112 * np.exp((17.67*(Temp-273.16)) / ((Temp-29.66)))
    return Ew
