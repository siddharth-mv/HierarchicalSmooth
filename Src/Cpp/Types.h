/*
 * Types.h -- contains all user-defined types.
 */

#ifndef _HSMOOTH_TYPES
#define _HSMOOTH_TYPES

#include <iostream>
#include <unordered_map>
#include <vector>
#include <tuple>
#include <boost/functional/hash.hpp>	// for std::hash< std::pair, ... >

#include "Eigen/Eigen"
#include "Eigen/Sparse"

// NOTE: 'size_t' is typedefed in iostream as unsigned long long, or something.

/*
 * trimesh:
 * Eigen array of integer triplets; the prototype of Delaunay 
 * triangulations in this library.
 */
typedef Eigen::Array< size_t, Eigen::Dynamic, 3 > trimesh;

/* 
 * meshnode:
 * Eigen arra yof float triplets, each column representing 
 * a 3D cartesian mesh node.
 */
typedef Eigen::Array< double, 3, Eigen::Dynamic > meshnodes;

/* 
 * facelabel:
 * This data type is analogous to Dream.3D's FaceLabels property
 * and represents a grain boundary patch by specifying the 
 * grain IDs on either side of the patch. 
 */
typedef Eigen::Array< size_t, Eigen::Dynamic, 2 > facelabels;

/*
 * nodetype:
 * Dream.3D-specific dataset which indicates the type of node 
 * in a surface mesh: interior, triple junction or quad junction
 * ( denoted by 2, 3, 4 respectively if on the interior and 
 * 12, 13, 14 if on the volume surface.
 */
typedef Eigen::Array< size_t, Eigen:Dynamic > nodetype;

/*
 * is_smoothed:
 * Boolean array specifying whether each node has been smoothed 
 * or not. At the beginning, only the nodetypes 4 and 14 should 
 * be initialized to true, the others should be false. 
 */
typedef Eigen:Array< bool, Eigen::Dynamic > is_smoothed;


/*
 * EdgePair, EdgeList:
 * Bookkeeping devices for edges in a Delaunay mesh, each 
 * edge being represented by an ordered pair of integers.
 */
typedef std::pair< size_t, size_t > EdgePair;
typedef std::vector< EdgePair > EdgeList;

/*
 * Since EdgePair objects are going to be searched for a lot in the 
 * hierarchical smooth library, the following definition is for a 
 * dictionary that maps EdgePair objects to objects of the user's 
 * choice. This object uses Boost's in-built hash function for 
 * std::pair objects. The target object type is specified through 
 * a template parameter T.
 */
template< typename T >
struct DictBase {
	typedef std::unordered_map< EdgePair, T, boost::hash< EdgePair > > EdgeDict;
};
/*
 * The dictionary initialization happens like this:
 *
 * DictBase< your-type >::EdgeDict my_dict;
 *
 */


/* SpMat:
 * Shorthand for Eigen's sparse matrix type.
 *
 * T:
 * Triplet containing a position indices for 
 * a single sparse matrix element (i, j ) and 
 * the floating point value at that position.
 * Defined in Eigen/Sparse
 */
typedef Eigen::SparseMatrix<double>	SpMat;
typedef Eigen::Triplet<double>		T;

#endif