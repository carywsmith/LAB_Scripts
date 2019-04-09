#
# For writing images to CSV File
# By Cary Smith
# Feb 3, 2019
#

from astropy.io import fits
import numpy
import csv

start = 1
n_images =1441
step = 1

for x in range(start, n_images, step):
    print("Writing File to CSV %d of %d ..." % (x+1, n_images))
    fits_filename = 'mfg1m0XX-kb80-20190201-%04d-x00.fits' % (x + 1)
    hdul = fits.open(fits_filename)
    data = hdul[0].data
    stdev = numpy.std(data)
    string_stdev = str('%.3f' % stdev)

# write Data to CSV file
    with open('Standard_Deveation.csv', 'a') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(string_stdev)

    csv_file.close()
