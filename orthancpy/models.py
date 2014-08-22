from datetime import datetime
from simplejson import JSONEncoder

def dicom_date(string,format="%Y%m%d"):
    try:
        return datetime.strptime(string, format).date()
    except:
        return None


class OrthancObject(object):
    """ Parent class for all Orthanc objects.
        REST calls are made only when data is
        attempted to be accessed.
    """
    _data = None
    def __init__(self, orthanc, obj_type, obj_id):
        self.type    = obj_type
        self.id      = obj_id
        self.orthanc = orthanc
        self.path    = '/{}/{}'.format(self.type,self.id)

    def _get_data(self, force_update=False):
        if self._data is None or force_update:
            self._data = self.orthanc.get(self.path)

    def _get_tag(self, tag, func=None):
        self._get_data()
        # get tag dict
        main = self._get_field('MainDicomTags')
        # check if dict exists
        if main is None: return None
        value = main.get(tag, None)
        # transform data if necessary
        if func is not None: return func(value)
        return value

    def _get_field(self, field):
        self._get_data()
        return self._data.get(field, None)

    def delete(self):
        self.orthanc.delete(self.path)
 
    @property 
    def exists(self):
        self._get_data()
        return self._data is not None


class Patient(OrthancObject):
    """ Orthanc patient """
    _studies = None
    def __init__(self, orthanc, id):
        super(self.__class__,self).__init__(orthanc, 'patients', id)

    @property
    def name(self):
        return self._get_tag('PatientName')

    @property
    def dob(self):
        return self._get_tag('PatientBirthDate',dicom_date)

    @property
    def sex(self):
        return self._get_tag('PatientSex')

    @property
    def patient_id(self):
        return self._get_tag('PatientID')

    @property
    def studies(self):
        if self._studies is None:
            self._studies = [Study(self.orthanc,x,patient=self)
                    for x in self._get_field('Studies')]
        return self._studies


class Study(OrthancObject):
    """ Orthanc study """
    def __init__(self, orthanc, id):
        super(self.__class__,self).__init__(orthanc, 'studies', id)

    @property
    def date(self):
        return self._get_tag('StudyDate', dicom_date)

    @property
    def description(self):
        return self._get_tag('StudyDescription')

    @property
    def study_id(self):
        return self._get_tag('StudyID')

    @property
    def instance_uid(self):
        return self._get_tag('StudyInstanceUID')

    @property
    def time(self):
        return self._get_tag('StudyTime')

    @property
    def series(self):
        return [Series(self.orthanc,x)
                for x in self._get_field('Series')]

    @property
    def series_count(self):
        return len(self._get_field('Series'))

    @property
    def patient(self):
        return Patient(self.orthanc,self._get_field('ParentPatient'))

    @property
    def is_anonymized(self):
        return self._get_field('AnonymizedFrom')

    def anonymize(self, obscure_id):
        uri = '{}/anonymize'.format(self.path)
        data = {
                "Replace":
                    {
                     "PatientName":obscure_id,
                     "PatientID":  obscure_id
                    },
                "Keep":
                    ["StudyDescription",
                     "SeriesDescription"]
                }

        return self.orthanc.post(uri, data=data)

    def send_to(self, modality):
        uri = '/modalities/{}/store'.format(modality)
        return self.orthanc.post(uri, data=self.id)


class Series(OrthancObject):
    """ Orthanc series """
    _instances = None
    def __init__(self, orthanc, id):
        super(self.__class__,self).__init__(orthanc, 'series', id)

    @property
    def manufacturer(self):
        return self._get_tag('Manufacturer')
    @property
    def modality(self):
        return self._get_tag('Modality')
    @property
    def protocol(self):
        return self._get_tag('ProtocolName')
    @property
    def sequence(self):
        return self._get_tag('SequenceName')
    @property
    def description(self):
        return self._get_tag('SeriesDescription')
    @property
    def number(self):
        return self._get_tag('SeriesNumber')
    @property
    def instance_uid(self):
        return self._get_tag('SeriesInstanceUID')
    @property
    def date(self):
        return self._get_tag('SeriesDate')
    @property
    def time(self):
        return self._get_tag('SeriesTime')
    @property
    def study(self):
        return Study(self.orthanc, self._get_field('ParentStudy'))
    @property
    def status(self):
        return self._get_field('Status')
    @property
    def is_stable(self):
        return self._get_field('IsStable')
    @property
    def instances(self):
        if self._instances is None:
            self._instances = [DicomInstance(self.orthanc,x)
                               for x in self._get_field('Instances')]
        return self._instances

    @property
    def num_instances(self):
        return len(self.instances)

    @property
    def mid_instance(self):
        """ attempt to locate instance that is mid-series """
        midn = int(self.num_instances/2)
        return self.instances[midn]

    @property
    def preview(self):
        """ return preview for mid instance. in theory this will give
            us a slice mid-brain, but it depends on the slice-order of
            the acquisition.
        """
        return self.mid_instance.preview


class DicomInstance(OrthancObject):
    """ Orthanc dicom instance """
    def __init__(self, orthanc, id):
        super(self.__class__,self).__init__(orthanc, 'instances', id)

    @property
    def file_uid(self):
        return self._get_field('FileUuid')
    @property
    def filesize(self):
        return self._get_field('FileSize')
    @property
    def index(self):
        return self._get_field('IndexInSeries')
    @property
    def acquisition_number(self):
        return self._get_tag('AcquisitionNumber')
    @property
    def instance_number(self):
        return self._get_tag('InstanceNumber')
    @property
    def sop_instance_uid(self):
        return self._get_tag('SOPInstanceUID')
    @property
    def preview(self):
        return self.orthanc.get_url('{}/preview'.format(self.path))
