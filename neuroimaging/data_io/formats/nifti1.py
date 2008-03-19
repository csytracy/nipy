__docformat__ = 'restructuredtext'

import numpy as N

from neuroimaging.utils.odict import odict
from neuroimaging.data_io.datasource import DataSource
from neuroimaging.data_io.formats import utils, binary, analyze
from neuroimaging.data_io.formats.nifti1_ext import quatern2mat, \
     mat2quatern

from neuroimaging.core.reference.axis import space, spacetime
from neuroimaging.core.reference.mapping import Affine
from neuroimaging.core.reference.grid import SamplingGrid


class Nifti1FormatError(Exception):
    """
    Nifti format error exception
    """

# datatype is a one bit flag into the datatype identification byte of the
# Analyze header. 
UBYTE = 2
SHORT = 4
INTEGER = 8
FLOAT = 16
COMPLEX = 32
DOUBLE = 64
RGB = 128 # has no translation!
INT8 = 256
UINT16 = 512
UINT32 = 768
INT64 = 1024
UINT64 = 1280
FLOAT128 = 1536 # has no translation!
COMPLEX128 = 1792
COMPLEX256 = 2048 # has no translation!

datatype2sctype = {
    UBYTE: N.uint8,
    SHORT: N.int16,
    INTEGER: N.int32,
    FLOAT: N.float32,
    COMPLEX: N.complex64,
    DOUBLE: N.float64,
    INT8: N.int8,
    UINT16: N.uint16,
    UINT32: N.uint32,
    INT64: N.int64,
    UINT64: N.uint64,
    COMPLEX128: N.complex128,
}

sctype2datatype = dict([(v, k) for k, v in datatype2sctype.items()])

# some bit-mask codes
NIFTI_UNITS_UNKNOWN = 0
NIFTI_UNITS_METER = 1
NIFTI_UNITS_MM = 2
NIFTI_UNITS_MICRON = 3
NIFTI_UNITS_SEC = 8
NIFTI_UNITS_MSEC = 16
NIFTI_UNITS_USEC = 24
NIFTI_UNITS_HZ = 32
NIFTI_UNITS_PPM = 40
NIFTI_UNITS_RADS = 48

unitcode2units = {
    NIFTI_UNITS_UNKNOWN: '',
    NIFTI_UNITS_METER: 'm',
    NIFTI_UNITS_MM: 'mm',
    NIFTI_UNITS_MICRON: 'um',
    NIFTI_UNITS_SEC: 's',
    NIFTI_UNITS_MSEC: 'ms',
    NIFTI_UNITS_USEC: 'us',
    NIFTI_UNITS_HZ: 'hz',
    NIFTI_UNITS_PPM: 'ppm',
    NIFTI_UNITS_RADS: 'rad',
}
units2unitcode = dict([(v, k) for k, v in unitcode2units.items()])

#q/sform codes
NIFTI_XFORM_UNKNOWN = 0
NIFTI_XFORM_SCANNER_ANAT = 1
NIFTI_XFORM_ALIGNED_ANAT = 2
NIFTI_XFORM_TALAIRACH = 3
NIFTI_XFORM_MNI_152 = 4

#slice codes:
NIFTI_SLICE_UNKNOWN = 0
NIFTI_SLICE_SEQ_INC = 1
NIFTI_SLICE_SEQ_DEC = 2
NIFTI_SLICE_ALT_INC = 3
NIFTI_SLICE_ALT_DEC = 4

# intent codes
NIFTI_INTENT_NONE = 0
NIFTI_INTENT_CORREL = 2
NIFTI_INTENT_TTEST = 3
NIFTI_INTENT_FTEST = 4
NIFTI_INTENT_ZSCORE = 5
NIFTI_INTENT_CHISQ = 6
NIFTI_INTENT_BETA = 7
NIFTI_INTENT_BINOM = 8
NIFTI_INTENT_GAMMA = 9
NIFTI_INTENT_POISSON = 10
NIFTI_INTENT_NORMAL = 11
NIFTI_INTENT_FTEST_NONC = 12
NIFTI_INTENT_CHISQ_NONC = 13
NIFTI_INTENT_LOGISTIC = 14
NIFTI_INTENT_LAPLACE = 15
NIFTI_INTENT_UNIFORM = 16
NIFTI_INTENT_TTEST_NONC = 17
NIFTI_INTENT_WEIBULL = 18
NIFTI_INTENT_CHI = 19
NIFTI_INTENT_INVGAUSS = 20
NIFTI_INTENT_EXTVAL = 21
NIFTI_INTENT_PVAL = 22
NIFTI_INTENT_LOGPVAL = 23
NIFTI_INTENT_LOG10PVAL = 24
NIFTI_FIRST_STATCODE = 2
NIFTI_LAST_STATCODE = 24
NIFTI_INTENT_ESTIMATE = 1001
NIFTI_INTENT_LABEL = 1002
NIFTI_INTENT_NEURONAME = 1003
NIFTI_INTENT_GENMATRIX = 1004
NIFTI_INTENT_SYMMATRIX = 1005
NIFTI_INTENT_DISPVECT = 1006 # specifically for displacements
NIFTI_INTENT_VECTOR = 1007 # for any other type of vector
NIFTI_INTENT_POINTSET = 1008
NIFTI_INTENT_TRIANGLE = 1009
NIFTI_INTENT_QUATERNION = 1010
NIFTI_INTENT_DIMLESS = 1011

# The NIFTI header
HEADER_SIZE = 348
struct_formats = odict((
    ('sizeof_hdr','i'),
    ('data_type','10s'),
    ('db_name','18s'),
    ('extents','i'),
    ('session_error','h'),
    ('regular','c'),
    ('dim_info','B'),
    ('dim','8h'),
    ('intent_p1','f'),
    ('intent_p2','f'),
    ('intent_p3','f'),
    ('intent_code','h'),
    ('datatype', 'h'),
    ('bitpix','h'),
    ('slice_start', 'h'),
    ('pixdim','8f'),
    ('vox_offset','f'),
    ('scl_slope','f'),
    ('scl_inter','f'),
    ('slice_end','h'),
    ('slice_code','B'),
    ('xyzt_units','B'),
    ('cal_max','f'),
    ('cal_min','f'),
    ('slice_duration','f'),
    ('toffset','f'),
    ('glmax','i'),
    ('glmin','i'),
    ('descrip','80s'),
    ('aux_file','24s'),
    ('qform_code','h'),
    ('sform_code','h'),
    ('quatern_b','f'),
    ('quatern_c','f'),
    ('quatern_d','f'),
    ('qoffset_x','f'),
    ('qoffset_y','f'),
    ('qoffset_z','f'),
    ('srow_x','4f'),
    ('srow_y','4f'),
    ('srow_z','4f'),
    ('intent_name','16s'),
    ('magic','4s'),
    ('qfac','f'),
))
field_formats = struct_formats.values()

##### define an extension here

# an extension is n*16 bytes long, the first 8 bytes are:
# int esize --> the size of the extension in bytes
# int ecode --> the code of the extension


class Nifti1(binary.BinaryFormat):
    """
    A class to read and write NIFTI format images.
    """

    # Anything which should be default different than field-defaults
    _field_defaults = {'sizeof_hdr': HEADER_SIZE,
                       'scl_slope': 1.0,
                       'magic': 'n+1\x00',
                       'pixdim': [1,0,0,0,0,0,0,0],
                       'vox_offset': 352.0,
                       }

    extensions = ('.img', '.hdr', '.nii', '.mat')
    # get around to implementing nvector:
    nvector = -1

    extendable = False

    def __init__(self, filename, mode="r", datasource=DataSource(), use_memmap=True, **keywords):
        """
        Constructs a Nifti binary format object with at least a filename
        possible additional keyword arguments:
        mode = mode to open the memmap (default is "r")
        datasource = ???
        grid = Grid object
        dtype = numpy data type
        intent = meaning of data
        clobber = allowed to clobber?
        """

        binary.BinaryFormat.__init__(self, filename, mode, datasource, **keywords)
        self.intent = keywords.get('intent', '')

        # does this need to be redundantly assigned?
        self.header_formats = struct_formats

        # fill the header dictionary in order, with any default values
        self.header_defaults()
        if self.mode[0] is "w":
            # should try to populate the canonical fields and
            # corresponding header fields with info from grid?
            self.byteorder = utils.NATIVE
            self.dtype = N.dtype(keywords.get('dtype', N.float64))
            self.dtype = self.dtype.newbyteorder(self.byteorder)
            if self.grid is not None:
                self.header_from_given()
            else:
                raise NotImplementedError("Don't know how to create header" \
                                          "info without a grid object")
            self.write_header(clobber=self.clobber)
        else:
            # this should work
            self.byteorder = analyze.Analyze.guess_byteorder(self.header_file,
                                                    datasource=self.datasource)
            self.read_header()
            # we may THINK it's a Nifti, but ...
            if self.header['magic'] not in ('n+1\x00', 'ni1\x00'):
                raise Nifti1FormatError
            tmpsctype = datatype2sctype[self.header['datatype']]
            tmpstr = N.dtype(tmpsctype)
            self.dtype = tmpstr.newbyteorder(self.byteorder)
            self.ndim = self.header['dim'][0]

        # fill in the canonical list as best we can for Analyze
        self.inform_canonical()

        ########## This could stand a clean-up ################################
        if self.grid is None:
            origin = (self.header['qoffset_x'],
                      self.header['qoffset_y'],
                      self.header['qoffset_z'])
            step = tuple(self.header['pixdim'][1:4])
            shape = tuple(self.header['dim'][1:4])
            if self.ndim == 3:
                axisnames = space[::-1]
            elif self.ndim == 4 and self.nvector <= 1:
                axisnames = spacetime[::-1]
                origin = origin + (1,)
                step = step + (self.header['pixdim'][4],)
                shape = shape + (self.header['dim'][4],)
##                     if self.squeeze:
##                     if self.dim[4] == 1:
##                         origin = origin[0:3]
##                         step = step[0:3]
##                         axisnames = axisnames[0:3]
##                         shape = self.dim[1:4]
##                 elif self.ndim == 4 and self.nvector > 1:
##                     axisnames = ('vector_dimension', ) + space[::-1]
##                     origin = (1,) + origin
##                     step = (1,) + step
##                     shape = shape + (self.header['dim'][5],)
##                     if self.squeeze:
##                         if self.dim[1] == 1:
##                             origin = origin[1:4]
##                             step = step[1:4]
##                             axisnames = axisnames[1:4]
##                             shape = self.dim[2:5]

            # DEBUG:  some debugging notes... chris
            #print 'In nifti1.Nifti1... create SamplingGrid'
            #print 'names:', axisnames
            #print 'shape:', shape
            #print 'start:', -N.array(origin)
            #print 'step:', step
            #print 'origin:', origin

            self.grid = SamplingGrid.from_start_step(names=axisnames,
                                                shape=shape,
                                                start=-N.array(origin),
                                                step=step)
            t = self.transform()
            self.grid.mapping.transform[:3,:3] = t[:3,:3]
            self.grid.mapping.transform[:3,-1] = t[:3,-1]
            ### why is this here?
            self.grid = self.grid.matlab2python()
        #else: Grid was already assigned by Format constructor
        
        self.attach_data(offset=int(self.header['vox_offset']), use_memmap=use_memmap)


    def _get_filenames(self):
        # Nifti single file will be the preferred type for creation
        return self.datasource.exists(self.filebase+".hdr") and \
               (self.filebase+".hdr", self.filebase+".img") or\
               (self.filebase+".nii", self.filebase+".nii")
    

    @staticmethod
    def _default_field_value(fieldname, fieldformat):
        "[STATIC] Get the default value for the given field."
        return Nifti1._field_defaults.get(fieldname, None) or \
            (fieldformat[:-1] and fieldformat[-1] is not 's') and \
             [utils.format_defaults[fieldformat[-1]]]*int(fieldformat[:-1]) or \
             utils.format_defaults[fieldformat[-1]]
    

    def header_defaults(self):
        for field, format in self.header_formats.items():
            self.header[field] = self._default_field_value(field, format)


    def header_from_given(self):
        # try to set up these fields from what we know:
        # datatype
        # bitpix
        # quatern_b,c,d
        # qoffset_x,y,z
        # qfac
        # bitpix
        # dim

        self.grid = self.grid.python2matlab()
        self.header['datatype'] = sctype2datatype[self.dtype.type]
        self.header['bitpix'] = self.dtype.itemsize * 8
        self.ndim = self.grid.ndim
    
        if not isinstance(self.grid.mapping, Affine):
            raise Nifti1FormatError, 'error: non-Affine grid in writing' \
                  'out NIFTI-1 file'

        ddim = self.ndim - 3
        t = self.grid.mapping.transform[ddim:,ddim:]

        qb, qc, qd, qx, qy, qz, dx, dy, dz, qfac = mat2quatern(t)

        (self.header['quatern_b'],
         self.header['quatern_c'],
         self.header['quatern_d']) = qb, qc, qd
        
        (self.header['qoffset_x'],
         self.header['qoffset_y'],
         self.header['qoffset_z']) = qx, qy, qz

        self.header['qfac'] = qfac

        _pixdim = [0.]*8
        _pixdim[0:4] = [qfac, dx, dy, dz]
        self.header['pixdim'] = _pixdim

        # this should be set to something, 1 happens
        # to be NIFTI_XFORM_SCANNER_ANAT
        self.header['qform_code'] = 1
        
        self.header['dim'] = \
                        [self.ndim] + list(self.grid.shape) + [0]*(7-self.ndim)

        self.grid = self.grid.matlab2python()
        
    def transform(self):
        """
        Return 4x4 transform matrix based on the NIFTI attributes
        for the 3d (spatial) part of the mapping.
        If self.sform_code > 0, use the attributes srow_{x,y,z}, else
        if self.qform_code > 0, use the quaternion
        else use a diagonal matrix filled in by pixdim.

        See help(neuroimaging.data_io.formats.nifti1_ext) for explanation.

        """

        qfac = float(self.header['pixdim'][0])
        if qfac not in [-1.,1.]:
            raise Nifti1FormatError('invalid qfac: orientation unknown')
        
        value = N.zeros((4,4))
        value[3,3] = 1.0
        
        if self.header['qform_code'] > 0:
            
            value = quatern2mat(b=self.header['quatern_b'],
                                c=self.header['quatern_c'],
                                d=self.header['quatern_d'],
                                qx=self.header['qoffset_x'],
                                qy=self.header['qoffset_y'],
                                qz=self.header['qoffset_z'],
                                dx=self.header['pixdim'][1],
                                dy=self.header['pixdim'][2],
                                dz=self.header['pixdim'][3],
                                qfac=qfac)

        elif self.header['sform_code'] > 0:

            value[0] = N.array(self.header['srow_x'])
            value[1] = N.array(self.header['srow_y'])
            value[2] = N.array(self.header['srow_z'])

        return value

    def inform_canonical(self, fieldsDict=None):
        if fieldsDict is not None:
            self.canonical_fields = odict(fieldsDict)
        else:
            self.canonical_fields['datasize'] = self.header['bitpix']
            (self.canonical_fields['ndim'],
             self.canonical_fields['xdim'],
             self.canonical_fields['ydim'],
             self.canonical_fields['zdim'],
             self.canonical_fields['tdim']) = self.header['dim'][:5]
            self.canonical_fields['scaling'] = self.header['scl_slope']

    def postread(self, x):
        """
        NIFTI-1 normalization based on scl_slope and scl_inter.
        """
        if not self.use_memmap:
            return x

        if self.header['scl_slope']:
            return x * self.header['scl_slope'] + self.header['scl_inter']
        else:
            return x

    def prewrite(self, x):
        """
        NIFTI-1 normalization based on scl_slope and scl_inter.
        If we need to cast the data into Integers, then record the
        new scaling
        """
        # check if a cast is needed in these two cases:
        # 1 - we're replacing all the data
        # 2 - the maximum of the given slice of data exceeds the
        #     global maximum under the current scaling
        #
        # NIFTI1 also contains an intercept term, so see if that needs
        # to change

        if not self.use_memmap:
            return x

        scaled_x = (x - self.header['scl_inter'])/self.header['scl_slope']
        if N.asarray(x).shape == self.data.shape or scaled_x.max() > self.data.max():  
            if x.shape == self.data.shape:
                minval = x.min()
            else:
                minval = min(x.min(), self[:].min())
            # try to find a new intercept if:
            # it's an unsigned type (in order to shift up), or
            # if all values > 0 (in order to shift down)
            if self.dtype in N.sctypes['uint']:
                intercept = minval
            else:
                intercept = minval>0 and minval or 0
                            
            scale = utils.scale_data(x-intercept,
                                     self.dtype, self.header['scl_slope'])

            # if the scale or intercept changed, mark it down
            if scale != self.header['scl_slope'] or \
               intercept != self.header['scl_inter']:
                self.header['scl_inter'] = intercept
                self.header['scl_slope'] = scale
                # be careful with NIFTI, open it rb+ in case we're writing
                # into the same file as the data (.nii file)
                fp = self.datasource.open(self.header_file, 'rb+')

                self.write_header(hdrfile=fp)
                scaled_x = (x - self.header['scl_inter'])/self.header['scl_slope']
            
        return scaled_x
