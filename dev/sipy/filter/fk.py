from __future__ import absolute_import, print_function
import obspy
from obspy.core.event.event import Event
from obspy.core.inventory.inventory import Inventory

import sys

import numpy
import numpy as np
import math
import matplotlib.pyplot as plt
from sipy.util.array_util import get_coords
import datetime
import scipy as sp
import scipy.signal as signal
from scipy import sparse
from scipy.optimize import fmin_cg

from sipy.util.array_util import array2stream, stream2array, epidist2nparray, attach_epidist2coords
from sipy.util.fkutil import ls2ifft_prep, line_cut, line_set_zero, shift_array,\
							find_peaks, slope_distribution, makeMask, create_iFFT2mtx, cg_solver, lstsqs
from sipy.util.base import nextpow2
from sipy.util.picker import get_polygon

def fk_filter(st, inv=None, event=None, trafo='FK', ftype='eliminate-polygon', phase=None, polygon=12, normalize=True, SSA=False):
	"""
	Import stream, the function applies an 2D FFT, removes a certain window around the
	desired phase to surpress a slownessvalue corresponding to a wavenumber and applies an 2d iFFT.
	To fill the gap between uneven distributed stations use array_util.gaps_fill_zeros(). A method to interpolate the signals in the
	fk-domain is beeing build, also a method using a norm minimization method.
	Alternative is an nonequidistant 2D Lombard-Scargle transformation.

	param st: Stream
	type st: obspy.core.stream.Stream

	param inv: inventory
	type inv: obspy.station.inventory.Inventory

	param event: Event
	type event: obspy.core.event.Event

	param trafo: Type of transformation, default is 'FK', possible inputs are:
				 FK: for f-k transformation via numpy.fft.fft2
				 FX: for f-x transformation via numpy.fft.fft
				 LS: for a combination of 1D FFT in time-domain and and Lomb-Scargle
				     in the space-domain, via numpy.fft.fft and scipy.signal.lombscargle
	type trafo: string

	param ftype: type of method, default is 'eliminate-polygon', possible inputs are:
				 eliminate
				 extract
				
				 if trafo is set to FK, also:
				 eliminate-polygon
				 extract-polygon

	type ftype: string

	param phase: name of the phase to be investigated
	type phase: string

	param polygon: number of vertices of polygon for fk filter, only needed 
				   if ftype is set to eliminate-polygon or extract-polygon.
				   Default is 12.
	type polygon: int
	
	param normalize: normalize data to 1
	type normalize: bool

	param SSA: Force SSA algorithm or let it check, default:False
	type SSA: bool

	returns:	stream_filtered, the filtered stream.
			


	References: Yilmaz, Thomas

	Author: S. Schneider 2016

	 This program is free software: you can redistribute it and/or modify
	 it under the terms of the GNU General Public License as published
	 by the Free Software Foundation, either version 3 of the License, or
	 any later version.

	 This program is distributed in the hope that it will be useful,
	 but WITHOUT ANY WARRANTY; without even the implied warranty of
	 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	 GNU General Public License for more details: http://www.gnu.org/licenses/
	"""

	# Convert format and prepare Variables.
	st_tmp = st.copy()
	ArrayData = stream2array(st_tmp, normalize)
	
	ix = ArrayData.shape[0]
	iK = int(math.pow(2,nextpow2(ix)+1))
	
	try:
		yinfo = epidist2nparray(epidist(inv, event, st_tmp))
		dx = (yinfo.max() - yinfo.min() + 1) / yinfo.size
		k_axis = np.fft.fftfreq(iK, dx)	
	except:
		print("\nNo inventory or event-information found. \nContinue without specific distance and wavenumber information.")
		yinfo=None
		dx=None
		k_axis=None

	it = ArrayData.shape[1]
	iF = int(math.pow(2,nextpow2(it)+1))
	dt = st_tmp[0].stats.delta
	f_axis = np.fft.fftfreq(iF,dt)


	# Calc mean diff of each epidist entry if it is reasonable
	# do a partial stack and apply filter.


	"""
	2D Frequency-Space / Wavenumber-Frequency Filter #########################################################
	"""

	# 2D f-k Transformation 
	# Decide when to use SSA to fill the gaps, calc mean distance of each epidist entry
	# if it differs too much --> SSA
	if trafo == "FK":
		
		# Note array_fk has f on the x-axis and k on the y-axis!!!
		# For interaction the conj.-transposed Array is shown!!! 
		array_fk = np.fft.fft2(ArrayData, s=(iK,iF))

		if ftype in ("eliminate"):
			array_filtered_fk = line_set_zero(array_fk)

		elif ftype in ("extract"):
			array_filtered_fk = line_cut(array_fk)				
		
		elif ftype in ("eliminate-polygon"):
			if isinstance(event, Event) and isinstance(inv, Inventory):
				array_filtered_fk = _fk_eliminate_polygon(array_fk, polygon, ylabel=r'frequency-domain f in $\frac{1}{Hz}$', \
														  yticks=f_axis, xlabel=r'wavenumber-domain k in $\frac{1}{^{\circ}}$', xticks=k_axis)
			else:
				msg='For wavenumber calculation inventory and event information is needed, not found.'
				raise IOError(msg)

		elif ftype in ("extract-polygon"):
			if isinstance(event, Event) and isinstance(inv, Inventory):
				array_filtered_fk = _fk_extract_polygon(array_fk, polygon, ylabel=r'frequency-domain f in $\frac{1}{Hz}$', \
														yticks=f_axis, xlabel=r'wavenumber-domain k in $\frac{1}{^{\circ}}$', xticks=k_axis)
			else:
				msg='For wavenumber calculation inventory and event information is needed, not found.'
				raise IOError(msg)

		else:
			print("No type of filter specified")
			raise TypeError

		array_filtered = np.fft.ifft2(array_filtered_fk, s=(iK,iF)).real

	# 2D f-x Transformation 
	elif trafo in ("FX"):
		array_fx = np.fft.fft(ArrayData, iF)
		if ftype in ("eliminate"):
			array_filtered = line_set_zero(array_fx)

		elif ftype in ("extract"):
			array_filtered = line_cut(array_fx)
			array_filtered = np.fft.ifft(ArrayData, iF).real

		else:
			msg = "No type of filter specified"
			raise TypeError(msg)

	# 2D FFT-LS 
	# elif trafo in ("LS"):

	# 	try:
	# 		yinfo = epidist2nparray(epidist(inv, event, st_tmp))
	# 	else:
	# 		msg='For wavenumber calculation inventory and event information is needed, not found.'
	# 		raise IOError(msg)	

	# 	# Apply filter.
	# 	if ftype in ("eliminate"):
	# 		array_filtered, periods = _fk_ls_filter_eliminate_phase_sp(ArrayData, y_dist=yinfo)

	# 	elif ftype in ("extract"):
	# 		array_filtered, periods = _fk_ls_filter_extract_phase_sp(ArrayData, y_dist=yinfo)

	# 	else:
	# 		print("No type of fk-filter specified")
	# 		raise TypeError		


	else:
		print("No valid input for type of Transformationtype")
		raise TypeError

	# Convert to Stream object.
	array_filtered = array_filtered[0:ix, 0:it]
	stream_filtered = array2stream(array_filtered, st_original=st.copy())

	return stream_filtered



"""
FFT FUNCTIONS 
"""
def fktrafo(stream, inv, event, normalize=True):
	"""
	Calculates the f,k - transformation of the data in stream. Returns the trafo as an array.

	:param st: Stream
	:type st: obspy.core.stream.Stream

	:param inv: inventory
	:type inv: obspy.station.inventory.Inventory

	:param event: Event
	:type event: obspy.core.event.Event

	returns
	:param fkdata: f,k - transformation of data in stream
	:type fkdata: numpyndarray
	"""
	st_tmp = stream.copy()
	ArrayData = stream2array(st_tmp, normalize)
	
	ix = ArrayData.shape[0]
	iK = int(math.pow(2,nextpow2(ix)+1))
	it = ArrayData.shape[1]
	iF = int(math.pow(2,nextpow2(it)+1))

	fkdata = np.fft.fft2(ArrayData, s=(iK,iF))
	
	return fkdata

def fk_reconstruct(st, mu=5e-2, solver="iterative", maxiter=8):
	"""
	This functions reconstructs missing signals in the f-k domain, using the original data,
	including gaps, filled with zeros, and its Mask-array (see makeMask, and slope_distribution.
	Uses the following cost function to minimize:

			J = ||dv - T FHmtx2D Yw Dv ||^{2}_{2} + mu^2 ||Dv||^{2}_{2}
			
			J := Cost function
			dv:= Column-wise-ordered long vector of the 2D signal d
			DV:= Column-wise-ordered long vector of the	f-k-spectrum
			Yw := Diagonal matrix built from the column-wise-ordered long vector of Mask
			T := Sampling matrix which maps the fully sampled desired seismic data to the available samples.
				 For de-noising problems T = I (identity matrix)
			mu := Trade-off parameter between misfit and model norm


	Minimizing is done via a method of conjugate gradients, de-noising (1-2 iterations), reconstruction(8-10) iterations.
	T FHmtx2D Yw Dv will be formed to one matrix A, so at the end the equation has the form:
			
							|   A    |		  | dv |
							|    	 | * Dv = |    |
							| mu * I |		  | 0  |

							  Afinal		  dfinal

	:param:

	returns:

	:param: 

	Example:
				from obspy import read as read_st
				import sipy
				
				stream = read_st("../data/synthetics_uniform/SUNEW.QHD")

				#Example around PP.
				stream_org = st.copy()
				d = sipy.util.array_util.stream2array(stream_org)
				ArrayData = np.zeros((d.shape[0], 300))
				for i, trace in enumerate(d):
					ArrayData[i,:]=trace[400:700]
				stream = sipy.util.array_util.array2stream(ArrayData, stream_org)
	
				dssa = sipy.filter.fk.fk_reconstruct(stream, mu=5e-2, maxiter=8)
				
				stream_ssa = sipy.util.array_util.array2stream(dssa, stream)

				sipy.util.fkutil.plot(stream_ssa)

	Author: S. Schneider, 2016
	Reference:	Mostafa Naghizadeh, Seismic data interpolation and de-noising in the frequency-wavenumber
				domain, 2012, GEOPHYSICS
	"""
	peakpick = None
	deltaslope = 0.05
	slopes = [-10,15]

	# Prepare data.
	st_tmp = st.copy()
	ArrayData= stream2array(st_tmp, normalize=True)
	ADT = ArrayData.copy().transpose()

	fkData = np.fft.fft2(ArrayData)
	fkDT = np.fft.fft2(ADT)

	# Implement automatic method, to cut into N 300 npts samples.
	# Iterate over those.
	if ADT.shape[0] > 300:
		msg="Data sample to big, no sufficient memory!"
		raise MemoryError(msg)

	# Calculate mask-function W.
	print("Calculating slope distribution...\n")
	M, prange, peaks = slope_distribution(fkData, slopes, deltaslope, peakpick)
	print("Creating mask function...\n")
	W = makeMask(fkData, peaks[0])
	
	# To keep the order it would be better to transpose W to WT
	# but for creation of Y, WT has to be transposed again,
	# so this step can be skipped.
	Y = W.reshape(1,W.size)[0]

	# Initialize arrays for cost-function.
	dv = ADT.transpose().reshape(1, ADT.size)[0]
	Dv = fkDT.transpose().reshape(1, fkDT.size)[0]
	
	T = np.ones((ArrayData.shape[0], ArrayData.shape[1]))
	for i,trace in enumerate(ArrayData):
		if sum(trace) == 0.:
			T[i] = 0.
	T = T.reshape(1, T.size)[0]

	Ts = sparse.diags(T)
	Yw = sparse.diags(Y)

	# Create sparse-matrix with iFFT operations.	
	print("Creating iFFT2 operator as a %ix%i matrix ...\n" %(fkDT.shape[0]*fkDT.shape[1], fkDT.shape[0]*fkDT.shape[1]))	

	FH = create_iFFT2mtx(fkDT.shape[0], fkDT.shape[1]) 
	print("... finished\n")

	# Create model matrix A.
	print("Creating sparse %ix%i matrix A ...\n" %(FH.shape[0], FH.shape[1]))	
	A =  Ts.dot(FH.dot(Yw))
	print("Starting reconstruction...\n")

	if solver in ("lsqr", "leastsquares"):
		print(" ...using least-squares solver...\n")
		x = sparse.linalg.lsqr(A, dv, mu)
	elif solver in ("ilsmr", "iterative"):
		print(" ...using iterative LSMR solver...\n")
		x = sparse.linalg.lsmr(A,dv,mu, maxiter=maxiter)
		print("istop = %i \n" % x[1])
		print("Used iterations = %i \n" % x[2])
		print("Misfit = %f \n " % x[3])
		print("Modelnorm = %f \n" % x[4])
		print("Condition number = %f \n" % x[5])
		print("Norm of Dv = %f \n" % x[6]) 
		Dv_rec = x[0]/x[0].max()
	
	st_rec = np.fft.ifft2(Dv_rec.reshape(fkData.shape))
	st_rec = (st_rec/st_rec.max()).real
	
	return dv, Dv, Dv_rec, st_rec


def _fk_extract_polygon(data, polygon, xlabel=None, xticks=None, ylabel=None, yticks=None):
	"""
	Only use with the function fk_filter!
	Function to test the fk workflow with synthetic data
	param data:	data of the array
	type data:	numpy.ndarray
	"""
	# Shift 0|0 f-k to center, for easier handling
	dsfk = np.fft.fftshift(data.conj().transpose())

	# Define polygon by user-input.
	indicies = get_polygon(np.log(abs(dsfk)), polygon, xlabel, xticks, ylabel, yticks)

	# Create new array, only contains extractet energy, pointed to with indicies
	dsfk_extract = np.zeros(dsfk.shape)
	dsfk_extract.conj().transpose().flat[ indicies ]=1.
	data_fk = dsfk * dsfk_extract
	
	data_fk = np.fft.ifftshift(data_fk.conj().transpose())

	return data_fk


def _fk_eliminate_polygon(data, polygon, xlabel=None, xticks=None, ylabel=None, yticks=None):
	"""
	Only use with the function fk_filter!
	Function to test the fk workflow with synthetic data
	param data:	data of the array
	type data:	numpy.ndarray
	"""
	# Shift 0|0 f-k to center, for easier handling
	dsfk = np.fft.fftshift(data.conj().transpose())
	
	# Define polygon by user-input.
	indicies = get_polygon(np.log(abs(dsfk)), polygon, xlabel, xticks, ylabel, yticks)

	# Create new array, contains all the energy, except the eliminated, pointed to with indicies
	dsfk_elim = dsfk.conj().transpose()
	dsfk_elim.flat[ indicies ]=0.
	data_fk = dsfk_elim.conj().transpose()

	data_fk = np.fft.ifftshift(data_fk.conj().transpose())

	return data_fk

"""
LS FUNCTIONS
"""
def _fk_ls_filter_extract_phase_sp(ArrayData, y_dist=False, radius=None, maxk=False):
	"""
	Only use with the function fk_filter!
	FK-filter using the Lomb-Scargle Periodogram with the scipy library
	param data:	data of the array
	type data:	numpy.ndarray

	param snes:	slownessvalue of the desired extracted phase
	type snes:	int
	"""
	return 

def _fk_ls_filter_eliminate_phase_sp(ArrayData, y_dist=False, radius=None, maxk=False):
	"""
	Only use with the function fk_filter!
	Function to test the fk workflow with synthetic data
	param data:	data of the array
	type data:	numpy.ndarray

	param snes:	slownessvalue of the desired extracted phase
	type snes:	int
	"""
	# Define freq Array 
	freq = np.zeros((len(ArrayData), len(ArrayData[0]) / 2  + 1)) + 1j

	for i in range(len(ArrayData)):
		freq_new = np.fft.rfftn(ArrayData[i])
		freq[i] = freq_new

	# Define k Array
	freqT = freq.conj().transpose()
	knum = np.zeros( ( len(freqT), len(freqT[0])  /2 +1 ))
		     
	#calc best range
	N = len(freqT[0])
	dN = ( max(freqT[0]) - min(freqT[0]) / N )
	
	f_temp = np.fft.rfftfreq(len(freqT[0]), dN) * 2.* np.pi

	#1. try: 
	#period_range = np.linspace(min_wavelength, max_bound, len(freqT[0]))
	#2. try: 
	#period_range = np.linspace(f_temp[1], max(f_temp), N)
	#3. try:
	period_range = f_temp
	#period_range = period_range.astype('float')
	period_range[0] = 1.
	#after this change the first outputparameter of the periodogram to a 
	#correlation between the signal and a e^0 function ;)
	period_range = period_range.astype('float')
	
	for j in range(len(freqT)):
		k_new = signal.lombscargle(y_dist, abs(freqT[j]), period_range)
		k_new = ls2ifft_prep(k_new, abs(freqT[j]))
		knum[j] = k_new

			
	#change dtype to integer, for further processing
	period_range = period_range.astype('int')
	fkspectra = knum
	dsfft = line_set_zero(fkspectra, 0, radius)
	
	return fkspectra.conj().transpose(), period_range
