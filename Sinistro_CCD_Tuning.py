# Cary Smith (2017)
import matplotlib
# Force matplotlib to not use any Xwindows backend.
matplotlib.use('Agg')

import time
from time import sleep
import astropy.time as astt
from astropy.io import fits
from pysinistro import timing_sinistro

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

import numpy as np
import pylab as plt

## Attempt to import superfin control:
#try:
#	import tfetch
#except ImportError:
#	sys.stderr.write("Unable to import tfetch module!  TT controller polling is disabled.")
#	tfetch = None


# Define the fuctions here

def plot_noise_spectrum_x(d, pixel_time=7.5e-6):

	subplot_order = (223, 224, 222, 221)
	for i in range(4):
		plt.subplot(subplot_order[i])
		plt.ylim(0,20)
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
	for i in range(4):
		plt.subplot(subplot_order[i])
		plt.ylim(0,20)
		q = d[i]
		q_rfft = np.fft.rfft(q[1:-2,1:-2], axis=0)
		q_rms = np.sqrt((abs(q_rfft)**2).mean(axis=1))
		q_rms_scaled = q_rms[1:] / np.sqrt(2*q_rms[1:].shape[0])  # scale so horiz. line is gaussian frame in adu
		f = np.arange(len(q_rms)) / (len(q_rms) * pixel_time) / 1000  # frequency in kHz derived from pixel time
		plt.plot(f[1:], q_rms_scaled)
		plt.title('FFT Noise Spectrum Y '"Q{0}".format(i+1))
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

	r = {"Gain - electrons per ADU ": [], "Read noise - electrons ": []}

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
		r["Gain - electrons per ADU "].append(gain)
		r["Read noise - electrons "].append(readnoise)

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
		sleep(0.5)
		cam = timing_sinistro.Sinistro(timing_sinistro.mode_1, timing_sinistro.operating_point_default)
		sleep(0.5)

		haveDoneSetup = input('Do you want to setup the Camera? ').lower()
		if haveDoneSetup.startswith('y'):
				
			# Prompt for TT controller IP address:
			ttsf = None
	#		if tfetch is not None:
	#			tt_address = input("\n\nEnter the TT controller address (leave blank to skip): ")
	#			if len(tt_address) == 0:
	#				print("TT polling disabled.")
	#				tt_address = None
	#			print("Connecting to TT controller ... ")
	#			ttsf = tfetch.TFetch(tt_address)
	#			tt_vals = ttsf.get_values()
	#			print("TT connected!")
	#			print("------------------------------------------")
	#			print("Current values:")
	#			for kv in tt_vals.items():
	#				print("%8s --> %10.3f" % kv)
	#			print("------------------------------------------")

			plotMode = input('Would you like to Enter Plot Mode I will take images and then plot the info for you? ').lower()
			if plotMode.startswith('y'):
				os.chdir('/home/eng/data')
				cameraNumber = input('What is the Camera Number and Controller Number ie. FL02/flcn? ')
				fullFileName = cameraNumber + '_' + now.strftime('%Y%m%d') + '_' + now.strftime('%H%M%S')
				if not os.path.exists(fullFileName):
					os.makedirs(fullFileName)
				os.chdir(fullFileName)
				
				operating_point_number = 43
				for x in range(operating_point_number):
					print("Taking operating point series %d of %d ..." % (x+1, operating_point_number))
					operating_point_FileName = 'operating_ point_%02d' % (x + 1)
					if not os.path.exists(operating_point_FileName):
						os.makedirs(operating_point_FileName)
					os.chdir(operating_point_FileName)
					sleep(0.5)
					
					if x == 0:
						z = cam.set_operating_point(timing_sinistro.operating_point_1)
						print (z)
					elif x == 1:
						z = cam.set_operating_point(timing_sinistro.operating_point_2)
						print (z)
					elif x == 2:
						z = cam.set_operating_point(timing_sinistro.operating_point_3)
						print (z)
					elif x == 3:
						z = cam.set_operating_point(timing_sinistro.operating_point_4)
						print (z)
					elif x == 4:
						z = cam.set_operating_point(timing_sinistro.operating_point_5)
						print (z)
					elif x == 5:
						z = cam.set_operating_point(timing_sinistro.operating_point_6)
						print (z)
					elif x == 6:
						z = cam.set_operating_point(timing_sinistro.operating_point_7)
						print (z)
					elif x == 7:
						z = cam.set_operating_point(timing_sinistro.operating_point_8)
						print (z)
					elif x == 8:
						z = cam.set_operating_point(timing_sinistro.operating_point_9)
						print (z)
					elif x == 9:
						z = cam.set_operating_point(timing_sinistro.operating_point_10)
						print (z)
					elif x == 10:
						z = cam.set_operating_point(timing_sinistro.operating_point_11)
						print (z)
					elif x == 11:
						z = cam.set_operating_point(timing_sinistro.operating_point_12)
						print (z)
					elif x == 12:
						z = cam.set_operating_point(timing_sinistro.operating_point_13)
						print (z)
					elif x == 13:
						z = cam.set_operating_point(timing_sinistro.operating_point_14)
						print (z)
					elif x == 14:
						z = cam.set_operating_point(timing_sinistro.operating_point_15)
						print (z)
					elif x == 15:
						z = cam.set_operating_point(timing_sinistro.operating_point_16)
						print (z)
					elif x == 16:
						z = cam.set_operating_point(timing_sinistro.operating_point_17)
						print (z)
					elif x == 17:
						z = cam.set_operating_point(timing_sinistro.operating_point_18)
						print (z)
					elif x == 18:
						z = cam.set_operating_point(timing_sinistro.operating_point_19)
						print (z)
					elif x == 19:
						z = cam.set_operating_point(timing_sinistro.operating_point_20)
						print (z)
					elif x == 20:
						z = cam.set_operating_point(timing_sinistro.operating_point_21)
						print (z)
					elif x == 21:
						z = cam.set_operating_point(timing_sinistro.operating_point_22)
						print (z)
					elif x == 22:
						z = cam.set_operating_point(timing_sinistro.operating_point_23)
						print (z)
					elif x == 23:
						z = cam.set_operating_point(timing_sinistro.operating_point_24)
						print (z)
					elif x == 24:
						z = cam.set_operating_point(timing_sinistro.operating_point_25)
						print (z)
					elif x == 25:
						z = cam.set_operating_point(timing_sinistro.operating_point_26)
						print (z)
					elif x == 26:
						z = cam.set_operating_point(timing_sinistro.operating_point_27)
						print (z)
					elif x == 27:
						z = cam.set_operating_point(timing_sinistro.operating_point_28)
						print (z)
					elif x == 28:
						z = cam.set_operating_point(timing_sinistro.operating_point_29)
						print (z)
					elif x == 29:
						z = cam.set_operating_point(timing_sinistro.operating_point_30)
						print (z)
					elif x == 30:
						z = cam.set_operating_point(timing_sinistro.operating_point_31)
						print (z)
					elif x == 31:
						z = cam.set_operating_point(timing_sinistro.operating_point_32)
						print (z)
					elif x == 32:
						z = cam.set_operating_point(timing_sinistro.operating_point_33)
						print (z)
					elif x == 33:
						z = cam.set_operating_point(timing_sinistro.operating_point_34)
						print (z)
					elif x == 34:
						z = cam.set_operating_point(timing_sinistro.operating_point_35)
						print (z)
					elif x == 35:
						z = cam.set_operating_point(timing_sinistro.operating_point_36)
						print (z)
					elif x == 36:
						z = cam.set_operating_point(timing_sinistro.operating_point_37)
						print (z)
					elif x == 37:
						z = cam.set_operating_point(timing_sinistro.operating_point_38)
						print (z)
					elif x == 38:
						z = cam.set_operating_point(timing_sinistro.operating_point_39)
						print (z)
					elif x == 39:
						z = cam.set_operating_point(timing_sinistro.operating_point_40)
						print (z)
					elif x == 40:
						z = cam.set_operating_point(timing_sinistro.operating_point_41)
						print (z)
					elif x == 41:
						z = cam.set_operating_point(timing_sinistro.operating_point_42)
						print (z)
					elif x == 42:
						z = cam.set_operating_point(timing_sinistro.operating_point_43)
						print (z)
						
					else:
						print ('Something is Wrong.')

					
					sleep(0.5)
					print()
					r = cam.set_ccd_analog_on()
					print (r)
					cam.setup_frame()
					print()
				
					n_flushes = 4
					for x in range(n_flushes):
						print("flushing %d of %d ..." % (x+1, n_flushes))
						ba = cam.get_frame()
						cam.imstat()
					
					##Noise		
					n_biases = 2	#n_biases = 1
					pix_time = 7.5e-6
					fullName = 'Bias_FFT_Plots_' + now.strftime('%Y%m%d') + '_' + now.strftime('%H%M%S') + '.pdf'
					pp = PdfPages(fullName)

					for x in range(n_biases):
						print("Taking bias %d of %d ..." % (x+1, n_biases))
						fits_filename = 'Bias%02d.fits' % (x + 1)
						fits_header = make_fits_header(ttsf)	# create header
						#cam.get_frame(fits_filename)
						bias_data = cam.get_frame()				# take image
						cam.imstat()
						fits.writeto(fits_filename, bias_data, header=fits_header, checksum=True)
						
						plt.clf()
						plot_noise_spectrum_x(bias_data, pixel_time=pix_time)
						plt.savefig(pp, format='pdf')
						
						plt.clf()
						plot_noise_spectrum_y(bias_data, pixel_time=pix_time)
						plt.savefig(pp, format='pdf')
						
					pp.close()
						
					##Flats	
					n_flats = 2	#n_flats = 1
					pix_time = 7.5e-6

					for x in range(n_flats):
						print("Taking flat %d of %d ..." % (x+1, n_flats))
						fits_filename = 'Flat%02d.fits' % (x + 1)
						fits_header = make_fits_header(ttsf)	# create header
						ins.write("puls:widt 5")
						ins.trigger()
						sleep(5)
						#cam.get_frame(fits_filename)
						flat_data = cam.get_frame()				# take image
						fits.writeto(fits_filename, flat_data, header=fits_header, checksum=True)
												
					##Flats
					ins.write("puls:widt 10")
					ins.trigger()
					sleep(10)
					cam.get_frame('flat_10sec.fits')
					ins.write("puls:widt 15")
					ins.trigger()
					sleep(15)
					cam.get_frame('flat_15sec.fits')
					ins.write("puls:widt 17")
					ins.trigger()
					sleep(17)
					cam.get_frame('flat_17sec.fits')
					ins.write("puls:widt 20")
					ins.trigger()
					sleep(20)
					cam.get_frame('flat_20secc.fits')
					ins.write("puls:widt 22")
					ins.trigger()
					sleep(22)
					cam.get_frame('flat_22sec.fits')
					ins.write("puls:widt 25")
					ins.trigger()
					sleep(25)
					cam.get_frame('flat_25sec.fits')
					
					## Ramp Flat and Plotting
					##
					##
					ba = cam.get_frame()
					ins.write("puls:widt 25")
					ins.trigger()
					cam.get_frame('Ramp_25sec.fits')
					ramp1 = fits.getdata('Ramp_25sec.fits')
						
					#Clear the Plot Memory and save the Ramp Plots to PDF
					fullName = 'Ramp_Plots_' + now.strftime('%Y%m%d') + '_' + now.strftime('%H%M%S') + ".pdf"
					pp2 = PdfPages(fullName)
					plt.clf()
					plot_linearity_ramp(ramp1)
					plt.savefig(pp2, format='pdf')
					plt.clf()
					
					plot_photon_transfer_map(ramp1)
					plt.savefig(pp2, format='pdf')
					plt.clf()
						
					plot_trailing_column(ramp1)
					plt.savefig(pp2, format='pdf')
					plt.clf()
						
					plot_trailing_correlation(ramp1)
					plt.savefig(pp2, format='pdf')
					plt.clf()

					pp2.close()
					
					
					
					#PDF of find gain	
					fullName = 'Find_Gain_' + now.strftime('%Y%m%d') + '_' + now.strftime('%H%M%S') + ".pdf"
					bias1 = fits.getdata('Bias01.fits'); bias2 = fits.getdata('Bias02.fits'); flat1 = fits.getdata('Flat01.fits'); flat2 = fits.getdata('Flat02.fits')
					value = findgain(flat1, flat2, bias1, bias2, section=(900, 1100, 900, 1100))
					word = '%s' % str (value)

					# Setup the document with paper size and margins
					doc = SimpleDocTemplate(buf, rightMargin=inch/2, leftMargin=inch/2, topMargin=inch/2, bottomMargin=inch/2, pagesize=letter)
					 
					# Styling paragraphs
					styles = getSampleStyleSheet()
					
					# Write things on the document
					paragraphs = []
					paragraphs.append(Paragraph(word, styles['Normal']))
					#paragraphs.append(Paragraph('This is another paragraph', styles['Normal']))
					doc.build(paragraphs)
					 
					# Write the PDF to a file
					with open(fullName, 'wb') as fd:
						fd.write(buf.getvalue())
					cam.set_ccd_analog_off()
					ins.close()
					sleep(60)
					os.chdir('..')	
			else:
				picMode = input('Would you like to Enter Picture Mode you tell me the frames and I will take them? ').lower()
				if picMode.startswith('y'):
					cameraNumber = input('What is the Camera Number and Controller Number ie. FL02/flcn ? ')
					fullFileName = cameraNumber + '_' + now.strftime('%Y%m%d') + '_' + now.strftime('%H%M%S')
					if not os.path.exists(fullFileName):
						os.makedirs(fullFileName)
					os.chdir(fullFileName)
					whatToDo = input('what would you like to to do? (Bias, Flat, Ramp or None) : ').lower()
					if whatToDo.startswith('b'):
						howManyBias = input('How many bias images would you like to take? ')
						ba = cam.get_frame()
						for i in range(int(howManyBias)):
							num = i + 1
							string = str(num)
							ba = cam.get_frame()
							# ba = cam.get_frame('Bias_' + string + '_' + now.strftime('%Y%m%d') + '_' + now.strftime('%H%M%S') + '.fits')

					elif whatToDo.startswith('f'):
						howManyFlats = input('How many flat images would you like to take? ')
						howManySecs = input('How long of an Exposure in Seconds? ')
						ins.write("puls:widt " + howManySecs)
						ba = cam.get_frame()
						for i in range(int(howManyFlats)):
							num = i + 1
							string = str(num)
							ins.trigger()
							sleep(int(howManySecs))
							ba = cam.get_frame('Flat_' + string + '_' + now.strftime('%Y%m%d') + '_' + now.strftime('%H%M%S') + '.fits')

					elif whatToDo.startswith('r'):
						ins.write("puls:widt 25")
						num = i + 1
						string = str(num)
						ba = cam.get_frame()
						ins.trigger()
						ba = cam.get_frame('Ramp_' + string + '_' + now.strftime('%Y%m%d') + '_' + now.strftime('%H%M%S') + '.fits')

					else:
						print('You did not say what to do or said None ... ')
						cam.set_ccd_analog_off()
		
							
			os.chdir('/home/eng/venv_pysinistro/pysinistro')
		else:
			cam.set_ccd_analog_off()
	except KeyboardInterrupt:
		print ("Shutdown requested...exiting")
		cam.set_ccd_analog_off()
		ins.close()
		print('Have a nice Day!')
		os.chdir('/home/eng/venv_pysinistro/pysinistro')
	except Exception:
		traceback.print_exc(file=sys.stdout)
	sys.exit(0)
# Standard boilerplate to call the main() function to begin
# the program.
if __name__ == '__main__':
	main()
