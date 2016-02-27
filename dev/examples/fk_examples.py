from __future__ import absolute_import

import numpy
import numpy as np
from numpy import genfromtxt
import math
import matplotlib.pyplot as plt
import matplotlib as mpl
import scipy as sp
import scipy.signal as signal

import os
import datetime

import obspy
from obspy.geodetics.base import gps2dist_azimuth, kilometer2degrees, locations2degrees
from obspy import read as read_st
from obspy import read_inventory as read_inv
from obspy import read_events as read_cat
from obspy.taup import TauPyModel

import sipy.misc.Muenster_Array_Seismology_Vespagram as MAS
import sipy.filter.fk as fk
import sipy.utilities.fkutil as fku
from sipy.filter.fk import fk_filter
from sipy.utilities.fkutil import get_polygon, nextpow2
from sipy.utilities.array_util import get_coords, attach_network_to_traces, attach_coordinates_to_traces,\
stream2array, array2stream, attach_network_to_traces, attach_coordinates_to_traces, epidist_inv, epidist2nparray, epidist2list, \
alignon, partial_stack






stream="../data/WORK_D.MSEED"
inventory="../data/2011-03-11T05:46:23.MSEED_inv.xml"
catalog="../data/2011-03-11T05:46:23.MSEED_cat.xml"
st, inv, cat = fku.read_file(stream, inventory, catalog)
ad = fku.stream2array(st)
adt = fku.transpose(ad)
epid = fku.epidist2nparray(fku.epidist_stream(st, inv, cat))
fkspectra, periods = fk_filter(st, ftype='LS', inv=inv, cat=cat, fktype="eliminate")
fkfft = abs(np.fft.fftn(ad))
samplingrate = 0.025

#Example data flow 20.01.2016
trace = ad[0]
xrange = np.linspace(0, trace.size*0.025, trace.size)




tracefft = np.fft.rfft(trace)
freq = np.fft.rfftfreq(trace.size, samplingrate)
freq = freq * 2. * np.pi
fftnorm=tracefft/max(tracefft)

frange_new = np.linspace(freq[1], max(freq), trace.size/2 + 1)
epidist = np.linspace(0, trace.size, trace.size) * 0.025
tracels_new = signal.lombscargle(epidist, trace.astype('float'), frange_new)


tracels = fku.ls2ifft_prep(tracels_new, trace)
fls = fku.convert_lsindex(frange_new, 0.025)



plt.plot(freq, abs((tracefft/max(tracefft)).real))
plt.plot(frange_new,tracels_new/max(tracels_new))
plt.plot(fls, tracels_new/max(tracels_new))
plt.plot(abs((tracefft/max(tracefft)).real))
plt.show()



plt.plot(tracels/max(tracels))
plt.plot(abs((tracefft/max(tracefft)).real))
plt.show()

plt.plot(np.fft.irfft(tracels))
plt.show()



Test Sinus
A = 2.
w = 1.
phi = 0.5 * np.pi

nin = 1000
nout = 100000
x = np.linspace(0.01, 10*np.pi, nin)
y = A * np.sin(w*x+phi)

yfft = np.fft.rfft(y)
yfft = yfft/max(yfft)

steps= max(x)/y.size

f_fft = np.fft.rfftfreq(y.size, steps) * 2. * np.pi

#frange = np.linspace(0.01, 10, nin/2)
frange = np.linspace(f_fft[1], max(f_fft), nin/2)
yls = signal.lombscargle(x, y, frange)
yls = yls/max(yls)
yls2ifft = fku.ls2ifft_prep(yls)



"""

#Example data flow
"""

#fk_filter(stream, inventory, catalog, phase)
#data=create_signal(no_of_traces=1,len_of_traces=12,multiple=False)
#datatest=fku.create_sine(no_of_traces=1, no_of_periods=2)

"""
##################INSTASEIS###############################

"""
#get data with instaseis
import obspy
from obspy.geodetics.base import gps2dist_azimuth, kilometer2degrees, locations2degrees
from obspy import read as read_st
from obspy import read_inventory as read_inv
from obspy import read_events as read_cat
from obspy.taup import TauPyModel

import numpy
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import scipy as sp
import scipy.signal as signal
from numpy import genfromtxt

from sipy.utilities.array_util import get_coords

import os
import datetime

import sipy.filter.fk as fk
from sipy.filter.fk import fk_filter
import sipy.utilities.fkutil as fku
import instaseis as ins

uniform=True
db = ins.open_db("/Users/Simon/dev/instaseis/10s_PREM_ANI_FORCES")

tofe = obspy.UTCDateTime(2016,2,9,18,41,1)
lat = 0.0
lon = 0.0
depth = 100000
aperture=20
no_of_stations=20
# in degrees
distance_to_source=100
# magnitude of randomness 
magn=2.

#output

streamfile = "SYNTH_OUT.QHD"

qstfile = "SYNTH_OUT.QST"
invfile = "SYNTH_OUT_inv.xml"
catfile = "SYNTH_OUT_cat.xml"

source = ins.Source(
latitude=lat, longitude=lon, depth_in_m=depth,
m_rr = 3.71e23 / 1E7,
m_tt = 7.81e21 / 1E7,m_pp =8.26e23 / 1E7,
m_rt = 1.399e23 / 1E7,
m_rp =6.95e22 / 1E7,
m_tp =3.177e24 / 1E7,
origin_time=tofe
)

x = []

with open( qstfile, "w") as fh:
	station_range = np.linspace(0,aperture-1,no_of_stations) + 100.
	if uniform:
		k=0
		for i in station_range:
			slon = i
			name="X"+str(int(k))
			print(name)
			x.append(ins.Receiver(latitude="0", longitude=str(slon), network="LA", station=name ))
			latdiff = gps2dist_azimuth(0.1,0,0.1,slon)[0]/1000.
			fh.write("%s    lat:     0.0 lon:     %f elevation:   0.0000 array:LA  xrel:      %f yrel:      0.00 name:ADDED BY SIMON \n" % (name, lon, latdiff))
			k+=1	
	else:
		i=0
		r = np.random.randn(no_of_stations)
		randrange = station_range + magn * r  
		randrange[0] = station_range[0]
		randrange[no_of_stations-1] = station_range[no_of_stations-1]
		while randrange.max() > randrange[19]:
			i = randrange.argmax()
			randrange[i] = randrange[i]-0.1
		randrange.sort()
		for slon in randrange:
			name="X"+str(int(i))
			x.append(ins.Receiver(latitude="0", longitude=slon, network="LA", station=name ))
			latdiff = gps2dist_azimuth(0.1,0,0.1,slon)[0]/1000.
			fh.write("%s    lat:     0.0 lon:     %f elevation:   0.0000 array:LA  xrel:      %f yrel:      0.00 name:ADDED BY SIMON \n" % (name, slon, latdiff))		
			i+=1
st_synth = []    
for i in range(len(x)):
    st_synth.append(db.get_seismograms(source=source, receiver=x[i]))


stream=st_synth[0]
for i in range(len(st_synth))[1:]:
    stream.append(st_synth[i][0])


#stream.write("../data/synth.sac", format="SAC")
#stream.write("../data/SYNTH.QHD", format="Q")


"""
Write quakeml file
"""


with open( catfile, "w") as fh:
	fh.write("<?xml version=\'1.0\' encoding=\'utf-8\'?> \n")
	fh.write("<q:quakeml xmlns:q=\"http://quakeml.org/xmlns/quakeml/1.2\" xmlns:ns0=\"http://service.iris.edu/fdsnws/event/1/\" xmlns=\"http://quakeml.org/xmlns/bed/1.2\"> \n")
	fh.write("  <eventParameters publicID=\"smi:local/6b269cbf-6b00-4643-8c2c-cbe6274083ae\"> \n")
	fh.write("    <event publicID=\"smi:service.iris.edu/fdsnws/event/1/query?eventid=3279407\"> \n")
	fh.write("      <preferredOriginID>smi:service.iris.edu/fdsnws/event/1/query?originid=9933375</preferredOriginID> \n")
	fh.write("      <preferredMagnitudeID>smi:service.iris.edu/fdsnws/event/1/query?magnitudeid=16642444</preferredMagnitudeID> \n")
	fh.write("      <type>earthquake</type> \n")
	fh.write("      <description ns0:FEcode=\"228\"> \n")
	fh.write("        <text>NEAR EAST COAST OF HONSHU, JAPAN</text> \n ")
	fh.write("        <type>Flinn-Engdahl region</type> \n")
	fh.write("      </description> \n")
	fh.write("      <origin publicID=\"smi:service.iris.edu/fdsnws/event/1/query?originid=9933375\" ns0:contributor=\"ISC\" ns0:contributorOriginId=\"02227159\" ns0:catalog=\"ISC\" ns0:contributorEventId=\"16461282\"> \n")
	fh.write("        <time> \n")
	fh.write("          <value>%s</value> \n" % tofe)
	fh.write("        </time> \n")
	fh.write("        <latitude> \n")
	fh.write("          <value>%f</value> \n" %lat)
	fh.write("        </latitude>\n")
	fh.write("        <longitude> \n")
	fh.write("          <value>%f</value> \n" %lon)
	fh.write("        </longitude>\n")
	fh.write("        <depth> \n")
	fh.write("          <value>%f</value> \n" %depth)
	fh.write("        </depth>\n")
	fh.write("        <creationInfo> \n")
	fh.write("          <author>Simon</author> \n")
	fh.write("        </creationInfo> \n")
	fh.write("      </origin> \n")
	fh.write("      <magnitude publicID=\"smi:service.iris.edu/fdsnws/event/1/query?magnitudeid=16642444\"> \n")
	fh.write("        <mag> \n")
	fh.write("          <value>9.1</value> \n")
	fh.write("        </mag> \n")
	fh.write("        <type>MW</type> \n")
	fh.write("        <originID>smi:service.iris.edu/fdsnws/event/1/query?originid=9933383</originID> \n")
	fh.write("        <creationInfo> \n")
	fh.write("          <author>Simon</author> \n")
	fh.write("        </creationInfo> \n")
	fh.write("      </magnitude> \n")
	fh.write("    </event> \n")
	fh.write("  </eventParameters> \n")
	fh.write("</q:quakeml>")



"""
Write station-files for synthetics
"""

with open( invfile, "w") as fh:
	fh.write("<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n")
	fh.write("<FDSNStationXML schemaVersion=\"1.0\" xmlns=\"http://www.fdsn.org/xml/station/1\">\n")
	fh.write("  <Source>IRIS-DMC</Source>\n")
	fh.write("  <Sender>IRIS-DMC</Sender>\n")
	fh.write("  <Created>2015-11-05T18:22:28+00:00</Created>\n")
	fh.write("  <Network code=\"LA\" endDate=\"2500-12-31T23:59:59+00:00\" restrictedStatus=\"open\" startDate=\"2003-01-01T00:00:00+00:00\">\n")
	fh.write("    <Description>Synthetic Array - Linear Array</Description>\n")
	fh.write("    <TotalNumberStations>20</TotalNumberStations>\n")
	fh.write("    <SelectedNumberStations>20</SelectedNumberStations>\n")

	if not uniform:
		station_range = randrange
	j=0
	for i in station_range:
		slon=i
		lat=0.0
		name="X"+str(int(j))
		fh.write("    <Station code=\"%s\" endDate=\"2011-11-17T23:59:59+00:00\" restrictedStatus=\"open\" startDate=\"2010-01-08T00:00:00+00:00\">\n" % name)
		fh.write("      <Latitude unit=\"DEGREES\">%f</Latitude>\n" % lat)
		fh.write("      <Longitude unit=\"DEGREES\">%f</Longitude>\n" % slon)
		fh.write("      <Elevation>0.0</Elevation>\n")
		fh.write("      <Site>\n")
		fh.write("        <Name> %s </Name>\n" % name)
		fh.write("      </Site>\n")
		fh.write("    <CreationDate>2010-01-08T00:00:00+00:00</CreationDate>\n")
		fh.write("    </Station>\n")
		j += 1
	fh.write("  </Network>\n")
	fh.write("</FDSNStationXML>")

inv=read_inv(invfile)
cat=read_cat(catfile)

st = stream.select(component="Z")
st.write( streamfile, format="Q")

##########################################################################################
#create Q station-file
with open("SYNTH.QST", "w") as fh:
	for i in station_range:
		slon=i
		latdiff = gps2dist_azimuth(0.1,0,0.1,lon)[0]/1000.
		#print "X%s    lat:     0.0 slon:     %f elevation:   0.0000 array:LA  xrel:      %f yrel:      0.00 name:ADDED BY SIMON" % (i, lon, latdiff)
		fh.write("X%s    lat:     0.0 lon:     %f elevation:   0.0000 array:LA  xrel:      %f yrel:      0.00 name:ADDED BY SIMON \n" % (i, slon, latdiff))



#Calculate Arrivals

#inv=read_inv("../data/synth_inv.xml")

latitude = 0.0
longitude = 0.0
m = TauPyModel(model="ak135")
Plist = ["P", "Pdiff", "PP"]
epidist = []
arrivaltime = []

for i in range(len(stream)):
	elat = latitude
	elon = longitude
	slat =  inv[0][i].latitude
	slon =  inv[0][i].longitude
	epidist.append(locations2degrees(slat,slon,elat,elon))
	arrivaltime.append(m.get_travel_times(source_depth_in_km=100.0, distance_in_degree=epidist[i]))

tofe

"""
Plotting
"""
pexuni = fku.stream2array(read_st("../data/synthetics_uniform/SYNTH_UNIFORM_PP_FK_EX.QHD").normalize())
pexuni = np.roll(pexuni, -35)
pexran = fku.stream2array(read_st("../data/synthetics_random/SYNTH_RAND_PP_FK_EX.QHD").normalize())
pexran = np.roll(pexran, -35)

pdiffuni = fku.stream2array(read_st("../data/synthetics_uniform/SYNTH_UNIFORM_PP_FK.QHD").normalize())
pdiffuni = np.roll(pdiffuni, -47)
pdiffran = fku.stream2array(read_st("../data/synthetics_random/SYNTH_RAND_PP_FK.QHD").normalize())

uni = fku.stream2array(read_st("../data/synthetics_uniform/SYNTH_UNIFORM_PP.QHD").normalize())
uni = np.roll(uni, -35)
ran = fku.stream2array(read_st("../data/synthetics_random/SYNTH_RAND_PP.QHD").normalize())
ran = np.roll(ran, -35)




plt.ylim([-1,1])
plt.xlim([200,550])
#plt.plot(uni[0],label=("uniform, no filter"))
plt.plot(ran[0],label=("random, no filter"))
#plt.plot(pdiffuni[0],label=("uniform, Pdiff eliminated"))
plt.plot(pdiffran[0],label=("random, Pdiff eliminated"))
#plt.plot(pexuni[0],label=("uniform, PP extractet"))
plt.plot(pexran[0],label=("random, PP extractet"))
plt.legend()
plt.show()

