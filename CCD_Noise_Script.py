# Cary Smith (2017)
import matplotlib
matplotlib.use('Agg')

import time
from time import sleep
import astropy.time as astt
from astropy.io import fits
from pysinistro import sinistro

from matplotlib.backends.backend_pdf import PdfPages

from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

import io
import os
import sys, traceback
import vxi11
import datetime

import plot_stuff
import numpy as np
import pylab as plt

# Attempt to import superfin control:
try:
	import tfetch
except ImportError:
	sys.stderr.write("Unable to import tfetch module!  TT controller polling is disabled.")
	tfetch = None

# Define the fuctions here

def plot_noise_spectrum_x(d, pixel_time=7.5e-6):

	subplot_order = (223, 224, 222, 221)
	for i in range(1):
		plt.subplot(subplot_order[i])
		plt.ylim(0,40)
		q = d[i]
		q_rfft = np.fft.rfft(q[1:-2,1:-2], axis=1)
		q_rms = np.sqrt((abs(q_rfft)**2).mean(axis=0))
		q_rms_scaled = q_rms[1:] / np.sqrt(2*q_rms[1:].shape[0])  # scale so horiz. line is gaussian frame in adu
		f = np.arange(len(q_rms)) / (len(q_rms) * pixel_time) / 1000  # frequency in kHz derived from pixel time
		plt.plot(f[1:], q_rms_scaled)
		plt.title('FFT Noise Spectrum X '"Q{0}".format(i+1))
		plt.annotate(("Q{0}".format(i+1), q_rms_scaled.mean()), xy=(2,17), xytext=(3,1.15))

def plot_noise_spectrum_y(d, pixel_time=7.5e-6):
 
	subplot_order = (223, 224, 222, 221)
	for i in range(1):
		plt.subplot(subplot_order[i])
		plt.ylim(0,20)
		q = d[i]
		q_rfft = np.fft.rfft(q[1:-2,1:-2], axis=0)
		q_rms = np.sqrt((abs(q_rfft)**2).mean(axis=1))
		q_rms_scaled = q_rms[1:] / np.sqrt(2*q_rms[1:].shape[0])  # scale so horiz. line is gaussian frame in adu
		f = np.arange(len(q_rms)) / (len(q_rms) * pixel_time) / 1000  # frequency in kHz derived from pixel time
		plt.plot(f[1:], q_rms_scaled)
		plt.title('FFT Noise Spectrum Y '"Q{0}".format(i+1))
		plt.ylabel('Count (ADU)')
		plt.xlabel('Freq (kHz)')
		plt.annotate(("Q{0}".format(i+1), q_rms_scaled.mean()), xy=(2,17), xytext=(3,1.15))

def plot_linearity_ramp(d):
	subplot_order = (223, 224, 222, 221)
	for i in range(4):
		plt.subplot(subplot_order[i])
		plt.plot(d[i, :, 950:1050].mean(axis=1))
		plt.xlim([0,2048])
		plt.ylim([0,65535])

def plot_trailing_column(d):
	subplot_order = (223, 224, 222, 221)
	for i in range(4):
		plt.subplot(subplot_order[i])
		plt.plot(d[i, :, 2066])
		plt.xlim([0, 2048])

def plot_trailing_correlation(d):
	subplot_order = (223, 224, 222, 221)
	for i in range(4):
		plt.subplot(subplot_order[i])
		# plt.plot(d[i, :, 950:1050].mean(axis=1), d[i, :, 2050:2070].mean(axis=1))
		plt.plot(d[i, :, 950:1050].mean(axis=1), d[i, :, 2068:].mean(axis=1))
		plt.xlim([0, 65535])

def plot_photon_transfer_map(d):
	subplot_order = (223, 224, 222, 221)
	for i in range(4):
		plt.subplot(subplot_order[i])
		plt.plot(d[i, :, 950:1050].mean(axis=1) - d[i, :, 2068:].mean(axis=1), d[i, :, 950:1050].std(axis=1)**2)
		plt.xlim([0, 65535])
		plt.ylim([0, 65535])

def findgain(f1, f2, z1, z2, section=(900, 1100, 900, 1100)):

	r = {"gain": [], "readnoise": []}

	for i in range(4):
		# TODO: For some reason this is not robust against the dead column in i=1
		# Need to compute as float64 or you get subtle integer underflow errors.
		f1s = f1[i, section[0]:section[1], section[2]:section[3]].astype(np.float64)
		f2s = f2[i, section[0]:section[1], section[2]:section[3]].astype(np.float64)
		z1s = z1[i, section[0]:section[1], section[2]:section[3]].astype(np.float64)
		z2s = z2[i, section[0]:section[1], section[2]:section[3]].astype(np.float64)
		df = f1s - f2s
		dz = z1s - z2s
		gain = ((f1s.mean() + f2s.mean()) - (z1s.mean() + z2s.mean())) / (df.std()**2 - dz.std()**2)
		readnoise = gain * dz.std() / np.sqrt(2)
		# gain = ((mean(flat1) + mean(flat2)) - (mean(zero1) + mean(zero2))) / ((sigma(flatdif))**2 - (sigma(zerodif))**2 )
		# readnoise = gain * sigma(zerodif) / sqrt(2)
		r["gain"].append(gain)
		r["readnoise"].append(readnoise)

	return r

def make_fits_header(ttobj):
	# Check current time:
	tstart = astt.Time(time.time(), scale='utc', format='unix')   # time object

	# Start list of cards for FITS header:
	divider_string = "-----------------------------------------------------------------------"
	hcards = [fits.Card('COMMENT', divider_string)]

	# Add timestamp to card list:
	hcards.append(fits.Card('DATE-OBS', tstart.isot, 'UTC date at start of exposure'))
	hcards.append(fits.Card('COMMENT', divider_string))

	# Add TT controller data to card list (if available):
	if ttobj != None:
		hcards.append(fits.Card('TT_ADDR', ttobj.ip_address, "TT controller address"))
		hcards.extend(ttobj.get_values().items())
		hcards.append(fits.Card('COMMENT', divider_string))

	# Add more stuff ...

	# Build and return FITS header:
	return fits.Header(hcards)

# Gather our code in a main() function
def main():
	try:
		#Date time instance
		now = datetime.datetime.now()
		buf = io.BytesIO()
		ins = vxi11.Instrument('172.16.4.6')
	    	##set Camera to the proper state
		pictureTime = input('Would you like to start the Camera? ').lower()
		if pictureTime.startswith('y'):
			cam = sinistro.Sinistro(sinistro.mode_1, sinistro.operating_point_default)
			r = cam.set_ccd_analog_on()
			print (r)
			cam.setup_frame()

		# Prompt for TT controller IP address:
		ttsf = None
		if tfetch is not None:
			tt_address = input("\n\nEnter the TT controller address (leave blank to skip): ")
			if len(tt_address) == 0:
				print("TT polling disabled.")
				tt_address = None
			print("Connecting to TT controller ... ")
			ttsf = tfetch.TFetch(tt_address)
			tt_vals = ttsf.get_values()
			print("TT connected!")
			print("------------------------------------------")
			print("Current values:")
			for kv in tt_vals.items():
				print("%8s --> %10.3f" % kv)
			print("------------------------------------------")
		#n_biases = input('How many bias woulkd you like to take? ')
		#sys.exit(0)
		
		os.chdir('/home/eng/data')
		cameraNumber = input('What is the Camera Number and Controller Number ie. FL02/flcn? ')
		fullFileName = cameraNumber + '_' + now.strftime('%Y%m%d') + '_' + now.strftime('%H%M%S')
		if not os.path.exists(fullFileName):
			os.makedirs(fullFileName)
		os.chdir(fullFileName)
		n_flushes = 4
		for x in range(n_flushes):
			ba = cam.get_frame()
		
## Noise (images and plots)
		n_biases = 2
		pix_time = 7.5e-6
		fullName = 'Bias_FFT_Plots_' + now.strftime('%Y%m%d') + '_' + now.strftime('%H%M%S') + '.pdf'
		pp = PdfPages(fullName)

		for x in range(n_biases):
			print("Taking bias %d of %d ..." % (x+1, n_biases))
			fits_filename = 'Bias%02d.fits' % (x + 1)
			fits_header = make_fits_header(ttsf)	# create header
			bias_data = cam.get_frame()				# take image
			cam.imstat()
			fits.writeto(fits_filename, bias_data, header=fits_header, checksum=True)
			plt.clf()
			plot_stuff.plot_noise_spectrum_x(bias_data, pixel_time=pix_time)
			plt.savefig(pp, format='pdf')

 ##Flats
		n_flats = 2
		pix_time = 7.5e-6

		for x in range(n_flats):
			print("Taking flat %d of %d ..." % (x+1, n_flats))
			fits_filename = 'Flat%02d.fits' % (x + 1)
			fits_header = make_fits_header(ttsf)	# create header
			ins.write("puls:widt 5")
			ins.trigger()
			sleep(5)
			flat_data = cam.get_frame()				# take image
			fits.writeto(fits_filename, flat_data, header=fits_header, checksum=True)

		pp.close()

 #PDF of find gain
		fullName = 'Find_Gain_' + now.strftime('%Y%m%d') + '_' + now.strftime('%H%M%S') + ".pdf"
		bias1 = fits.getdata('Bias01.fits'); bias2 = fits.getdata('Bias02.fits'); flat1 = fits.getdata('Flat01.fits'); flat2 = fits.getdata('Flat02.fits')
		value = plot_stuff.findgain(flat1, flat2, bias1, bias2, section=(900, 1100, 900, 1100))
		word = '%s' % str (value)

 # Setup the document with paper size and margins
		doc = SimpleDocTemplate(buf, rightMargin=inch/2, leftMargin=inch/2, topMargin=inch/2, bottomMargin=inch/2, pagesize=letter)

 # Styling paragraphs
		styles = getSampleStyleSheet()
 # Write things on the document
		paragraphs = []
		paragraphs.append(Paragraph(word, styles['Normal']))
		doc.build(paragraphs)

# Write the PDF to a file
		with open(fullName, 'wb') as fd:
			fd.write(buf.getvalue())
			sleep(10)
			os.chdir('..')

		cam.set_ccd_analog_off()
		print (r)
		#usb_close.reset_sinistro_usb()
		os.chdir('/home/eng/venv_pysinistro/pysinistro')

	except KeyboardInterrupt:
		print ("Shutdown requested...exiting")
		cam.set_ccd_analog_off()
		#usb_close.reset_sinistro_usb()
		print('Have a nice Day!')
		os.chdir('/home/eng/venv_pysinistro/pysinistro')
	except Exception:
		cam.set_ccd_analog_off()
		#usb_close.reset_sinistro_usb()
		traceback.print_exc(file=sys.stdout)
		sys.exit(0)

# Standard boilerplate to call the main() function to begin
# the program.
if __name__ == '__main__':
	main()
