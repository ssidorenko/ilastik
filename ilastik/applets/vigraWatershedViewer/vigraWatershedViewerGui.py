from PyQt4 import uic
from PyQt4.QtCore import pyqtSlot

import os
import time
import copy
import threading
from functools import partial

from ilastik.applets.layerViewer import LayerViewerGui

from volumina.slicingtools import index2slice

import logging
logger = logging.getLogger(__name__)
traceLogger = logging.getLogger('TRACE.' + __name__)
from lazyflow.tracer import traceLogged

class VigraWatershedViewerGui(LayerViewerGui):
    """
    """
    
    ###########################################
    ### AppletGuiInterface Concrete Methods ###
    ###########################################
    
    def appletDrawers(self):
        return [ ("Watershed Viewer", self.getAppletDrawerUi() ) ]

    # (Other methods already provided by our base class)

    ###########################################
    ###########################################
    
    @traceLogged(traceLogger)
    def __init__(self, mainOperator):
        """
        """
        super(VigraWatershedViewerGui, self).__init__([mainOperator.InputChannels, mainOperator.ColoredPixels])
        self.mainOperator = mainOperator
        self.mainOperator.FreezeCache.setValue(True)
        self.mainOperator.OverrideLabels.setValue( { 0: (0,0,0,0) } )
        
        self.mainOperator.WatershedPadding.notifyDirty( self.updatePaddingGui )
        self.mainOperator.WatershedPadding.setValue(10)
        self.updatePaddingGui(self.mainOperator.WatershedPadding)
    
    @traceLogged(traceLogger)
    def initAppletDrawerUi(self):
        # Load the ui file (find it in our own directory)
        localDir = os.path.split(__file__)[0]
        self._drawer = uic.loadUi(localDir+"/drawer.ui")
        self._drawer.updateWatershedsButton.clicked.connect( self.onUpdateWatershedsButton )
        self._drawer.paddingSlider.valueChanged.connect( self.onPaddingChanged )
        self._drawer.paddingSpinBox.valueChanged.connect( self.onPaddingChanged )
                
    def getAppletDrawerUi(self):
        return self._drawer
    
    @traceLogged(traceLogger)
    def setupLayers(self, currentImageIndex):
        layers = []

        # Show the watershed data
        outputImageSlot = self.mainOperator.ColoredPixels[ currentImageIndex ]
        if outputImageSlot.ready():
            outputLayer = self.createStandardLayerFromSlot( outputImageSlot, lastChannelIsAlpha=True )
            outputLayer.name = "Watershed (channel 0)"
            outputLayer.visible = True
            outputLayer.opacity = 0.5
            layers.append(outputLayer)
        
        # Show the raw input data
        inputImageSlot = self.mainOperator.InputChannels[ currentImageIndex ]
        if inputImageSlot.ready():
            for channel, slot in enumerate(inputImageSlot):
                inputLayer = self.createStandardLayerFromSlot( slot )
                inputLayer.name = "Raw Input (Ch.{})".format(channel)
                inputLayer.visible = True
                inputLayer.opacity = 1.0
                layers.append(inputLayer)

        return layers

    @pyqtSlot()
    @traceLogged(traceLogger)
    def onUpdateWatershedsButton(self):        
        @traceLogged(traceLogger)
        def updateThread():
            """
            Temporarily unfreeze the cache and freeze it again after the views are finished rendering.
            """
            self.mainOperator.FreezeCache.setValue(False)

            # Force the cache to update.
            self.mainOperator.InputImage[self.imageIndex].setDirty( slice(None) )
            
            # Wait for the image to be rendered into all three image views
            time.sleep(2)
            for imgView in self.editor.imageViews:
                imgView.scene().joinRendering()
            self.mainOperator.FreezeCache.setValue(True)

        if self.imageIndex >= 0:
            th = threading.Thread(target=updateThread)
            th.start()

    def getLabelAt(self, currentImageIndex, position5d):
        labelSlot = self.mainOperator.WatershedLabels[currentImageIndex]
        if labelSlot.ready():
            labelData = labelSlot[ index2slice(position5d) ].wait()
            return labelData.squeeze()[()]
        else:
            return None

    def handleEditorLeftClick(self, currentImageIndex, position5d):
        """
        This is an override from the base class.  Called when the user clicks in the volume.
        
        For left clicks, we highlight the clicked label.
        """
        label = self.getLabelAt(currentImageIndex, position5d)
        if label != 0 and label is not None:
            overrideSlot = self.mainOperator.OverrideLabels[currentImageIndex]
            overrides = copy.copy(overrideSlot.value)
            overrides[label] = (255, 255, 255, 255)
            overrideSlot.setValue(overrides)
            
    def handleEditorRightClick(self, currentImageIndex, position5d):
        """
        This is an override from the base class.  Called when the user clicks in the volume.
        
        For right clicks, we un-highlight the clicked label.
        """
        label = self.getLabelAt(currentImageIndex, position5d)
        overrideSlot = self.mainOperator.OverrideLabels[currentImageIndex]
        overrides = copy.copy(overrideSlot.value)
        if label != 0 and label in overrides:
            del overrides[label]
            overrideSlot.setValue(overrides)
    
    def onPaddingChanged(self, value):
        self.mainOperator.WatershedPadding.setValue(value)
    
    def updatePaddingGui(self, slot, *args):
        value = slot.value
        self._drawer.paddingSlider.setValue( value )
        self._drawer.paddingSpinBox.setValue( value )


