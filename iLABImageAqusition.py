###
# iLabImageAcquisition script
#
# A sequencer script to automatically take images in the lab with a shutter.
#
# Author: Cary Smith
#
# Feb 2019
#
###
#   I put these here only because they where in all of the scripts please if not needed remove
from org.lcogt.sequencer.script import Script
from java.lang import Double
#   For functionGenerator
import vxi11


class iLabImageAcquisition(Script):
    #   Acquisition Script

    def __init__(self):

        exposure_time = 10.0
        exposure_units = "s"
        n_images = 100
        image_type = "experimental"

    def run(self):
        #   Script run method

        self.message("Starting iLab Image Acquisition Script")
        functionGenerator = vxi11.Instrument('172.16.4.6')

        #   Take an exposure
        functionGenerator.write("puls:widt " str(exposure_time))
        #   Loop thru exposure
        for x in range(n_images):
            self.message("Taking Image %d of %d ..." % (x+1, n_images) ")
            functionGenerator.trigger()
            self.instrument.expose(exposure_time, units=exposure_units, count=1, type=image_type)
            
