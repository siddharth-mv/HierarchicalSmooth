#   Copyright (c) 2016-2018, Siddharth Maddali 
#   All rights reserved. 
#   
#   Redistribution and use in source and binary forms, with or without 
#   modification, are permitted provided that the following conditions are met: 
#   
#    * Redistributions of source code must retain the above copyright notice, 
#      this list of conditions and the following disclaimer. 
#    * Redistributions in binary form must reproduce the above copyright 
#      notice, this list of conditions and the following disclaimer in the 
#      documentation and/or other materials provided with the distribution. 
#    * Neither the name of Carnegie Mellon University nor the names of its 
#      contributors may be used to endorse or promote products derived from 
#      this software without specific prior written permission. 
#   
#   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
#   AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE 
#   IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE 
#   ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE 
#   LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR 
#   CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
#   SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS 
#   INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
#   CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
#   ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
#   POSSIBILITY OF SUCH DAMAGE. 
#   
import numpy as np
from scipy.sparse import diags, csc_matrix  # to create sparse diagonal matrices
from scipy.sparse.linalg import spsolve     # to solve sparse systems of equations

import Base as base                         # custom module containing ismember, etc.
import HierarchicalSmooth_PRIVATE as hspv   # private functions to make this code mode readable
import Triangulation as triang              # bare-bones version of Matlab's triangulation object

import copy                                 # to use deepcopy
import sys                                  # to write to output streams
import time

###################################################################################################


def Laplacian2D( N, type='serial' ):    # ...or type='cyclic'
    M = diags( [ np.ones( N-1 ) ], [ 1 ] ) - diags( [ np.ones( N ) ], [ 0 ] ).tolil()
    M = M.T * M
    if type=='serial':
        M[ -1, -1 ] = 1.
    elif type=='cyclic':
        M[ 0, 0 ] = 2.
        M[ 0, -1 ] = M[ -1, 0 ] = -1.
    else:
        sys.stderr.write( 'HierarchicalSmooth.Laplacian2D: Unrecognized type \'%s\'.\n' % type )
    return M.tocsc()

###################################################################################################

def GraphLaplacian( tri ):
    nUniq = np.unique( tri )
    nIdx = range( nUniq.size )
    nSubTri = np.array( base.ismember( tri, nUniq )[1] ).reshape( -1, tri.shape[1] )
    MLap = diags( [ np.zeros( nUniq.size ) ], [ 0 ] ).tolil()    # linked list sparse matrix
    for i in range( nSubTri.shape[0] ):
        for j in range( 3 ):
            l = ( j + 3 ) % 3
            m = ( j + 4 ) % 3 
            n = ( j + 5 ) % 3
            MLap[ nSubTri[i,l], nSubTri[i,m] ] = -1
        MLap[ nSubTri[i,l], nSubTri[i,n] ] = -1
    for i in range( MLap.shape[0] ):
        MLap[ i, i ] = -MLap[i,:].sum()
    return MLap.tocsc(), nUniq

###################################################################################################

def Smooth( yInArray, fThreshold, nMaxIterations, L=None, nFixed=None ):

    N = yInArray.shape[0]
    if L==None:
        if nFixed==None or len( nFixed )==0:
            L = Laplacian2D( N )                                # serial with fixed endpoints
            nFixed = [ 0, N-1 ]
        else:
            L = Laplacian2D( N, 'cyclic' )

    nMobile = [ i for i in range( N ) if i not in nFixed ]  # cyclic with specified fixed points
    yIn = csc_matrix( yInArray )

    if len( nMobile ) < 1:
        return yIn.todense(), [], []

    IterData = []
    LRed = L[ :, nMobile ][ nMobile, : ]
    fConst = copy.deepcopy( L )
    fConst[ :, nMobile ] = 0
    fConst = ( fConst * yIn )[ nMobile, : ]
    D = L.multiply( L > 0. ) # diagonal matrix
    A = L.multiply( L < 0. ) # adjacency matrix
    AyIn = A * yIn
    fSmallEye = diags( [ np.ones( len( nMobile ) ) ], [ 0 ] )
    yMobile = yIn[ nMobile, : ]

    fEps = 0.5
    fStep = fEps/2.
    nIterations = 1
    LRedTLRed = LRed.T * LRed
    LRedConst = LRed.T * fConst

    fObj1, yOut = hspv._GetObjFn( fEps, fSmallEye, LRedTLRed, yIn, nMobile, LRedConst, D, AyIn )
    fObj2 = hspv._GetObjFn( fEps+fThreshold, fSmallEye, LRedTLRed, yIn, nMobile, LRedConst, D, AyIn )[0]
    IterData.append( [ fEps, fObj1 ] )

    fSlope = ( fObj2 - fObj1 ) / fThreshold
    while abs( fSlope ) > fThreshold and nIterations < nMaxIterations:
        if fSlope > 0.:
            fEps -= fStep
        else:
            fEps += fStep

        fStep /= 2.
        fObj1, yOut = hspv._GetObjFn( fEps, fSmallEye, LRedTLRed, yIn, nMobile, LRedConst, D, AyIn )
        fObj2 = hspv._GetObjFn( fEps+fThreshold, fSmallEye, LRedTLRed, yIn, nMobile, LRedConst, D, AyIn )[0]

        fSlope = ( fObj2 - fObj1 ) / fThreshold
        IterData.append( [ fEps, fObj1 ] )
        nIterations += 1

    if nIterations == nMaxIterations:
        sys.stderr.write( 'HierarchicalSmooth.Smooth warning: Max. number of iterations reached.\n' )
    return yOut.todense(), IterData, nIterations

###################################################################################################

def DifferentiateFaces( TriangIn ):
    FB = TriangIn.freeBoundary() 
        # No need for chain-link sorting; this was already 
        # done on the creation of the Triangulation object.
    fblist = []
    start = FB[0,0]
    thissec = [ 0 ]
    n = 1
    while n < len( FB ):
        if FB[n,1]==start:  # end of current section
            thissec.append( n )
            fblist.append( thissec )
            thissec = []
        elif thissec==[]:   # start of new section
            start = FB[n,0]
            thissec.append( n )
        n += 1
    return FB, fblist

###################################################################################################

def HierarchicalSmooth( 
    xPoints, tri, nFaceLabels, nNodeType, 
    fThreshold=1.e-4, nIterations=2000, bPointSmoothed=None, sLogFile=None 
    ):

    xSmoothed = copy.deepcopy( xPoints )

    if bPointSmoothed==None:
        bPointSmoothed = np.array( nNodeType%10==4 )    # following Dream3d convention.
            # quad points are considered already 'smoothed'
    sOut = sys.stdout
    if sLogFile != None:            # dump status to text file instead of stdout
        sys.stdout = open( sLogFile, 'w' )
   
    print 'Hashing interface elements (this may take some time)...',
    t0 = time.time()
    BoundaryDict = {}
    for i in range( len( nFaceLabels ) ):
        if nFaceLabels[i,0] > nFaceLabels[i,1]:
            nFaceLabels[i,0], nFaceLabels[i,1] = nFaceLabels[i,1], nFaceLabels[i,0]
            tri[i,0], tri[i,1] = tri[i,1], tri[i,0]
        try:
            BoundaryDict[ str( nFaceLabels[i] ) ].append( i )
        except KeyError:
            BoundaryDict[ str( nFaceLabels[i] ) ] = [ i ] # start new dictionary entry
    print '%s seconds. ' % str( time.time() - t0 )
    nUniqFaces = np.vstack( { tuple( row ) for row in nFaceLabels } )
    nCount = 1
    for GB in BoundaryDict.keys():
        print 'Interface %s: %d of %d...' % ( GB, nCount, len( nUniqFaces )  ), 
        t0 = time.time()
        triGB = tri[ BoundaryDict[ GB ], : ]
        pointGB = np.unique( triGB )
        triGB = np.array( base.ismember( triGB, pointGB )[1] ).reshape( -1, 3 )
        thisX = xSmoothed[ :, pointGB ]
        thisType = nNodeType[ pointGB ]
        thisSmoothed = bPointSmoothed[ pointGB ]
        
        T = triang.Triangulation( triGB, thisX )
        FB, fbList = DifferentiateFaces( T )
        
        if len( FB ) > 0:
            for thisFB in fbList:   # smoothing entire closed loop
                if len( thisFB ) != 2:
                    continue
                thisLoop = FB[ thisFB[0]:thisFB[1]+1, 0 ]
                nLoop = len( thisLoop )
                anchorPoints = np.where( ( thisType[ thisLoop ] % 10 )==4 )[0]
                    # should account for the case where len( anchorPoints ) == 0 for a closed internal free boundary
                nAP = len( anchorPoints )
                for i in range( nAP ):
                    nstart = anchorPoints[i]
                    nstop = anchorPoints[ (i+1)%nAP ]
                    if nstop < nstart: # loop around...
                        tjSegment = thisLoop[ [ j%nLoop for j in range( nstart, nstop+nLoop+1 ) ] ]
                    else:
                        tjSegment = thisLoop[ range( nstart, nstop+1 ) ]
                    if np.any( thisSmoothed[ tjSegment ]==False ): # if not already smoothed...
                        thisTJ = thisX[ :, tjSegment ]
                        thisTJSmoothed = Smooth( thisTJ.T, fThreshold, nIterations )[0].T
    #                    thisTJSmoothed = Smooth( thisTJSmoothed.T, fThreshold, nIterations )[0].T
                        thisX[ :, tjSegment ] = thisTJSmoothed
                        thisSmoothed[ tjSegment ] = True

        L = GraphLaplacian( triGB )[0]
        fixed = list( np.where( thisSmoothed==True )[0] )
        thisXS = Smooth( thisX.T, fThreshold, nIterations, L, nFixed=fixed )[0].T
        thisXS = Smooth( thisXS.T, fThreshold, nIterations, L, nFixed=fixed )[0].T
        xSmoothed[ :, pointGB ] = thisXS
        thisSmoothed[ [ n for n in range( pointGB.size ) if n not in fixed ] ] = True
        bPointSmoothed[ pointGB ] = thisSmoothed
        print '%s seconds. ' % str( time.time() - t0 )
        nCount += 1

    sys.stdout = sOut     # reset stdout
    return xSmoothed, bPointSmoothed

###################################################################################################
        
