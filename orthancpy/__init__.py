import requests
from datetime import datetime
from simplejson import JSONDecoder

json = JSONDecoder()

def dicom_date(string,format="%Y%m%d"):
    return datetime.strptime(string, format).date()


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

    def _get_tag(self, tag):
        self._get_data()
        # get tag dict
        main = self._get_field('MainDicomTags')
        # check if dict exists
        if main is None: return None
        return main.get(tag, None)

    def _get_field(self, field):
        self._get_data()
        return self._data.get(field, None)


class Patient(OrthancObject):
    """ Orthanc patient """
    def __init__(self, orthanc, id):
        super(self.__class__,self).__init__(orthanc, 'patients', id)

    @property
    def name(self):
        return self._get_tag('PatientName')

    @property
    def dob(self):
        return dicom_date(self._get_tag('PatientBirthDate'))

    @property
    def sex(self):
        return self._get_tag('PatientSex')

    @property
    def patient_id(self):
        return self._get_tag('PatientID')

    @property
    def studies(self):
        return [Study(orthanc,x,patient=self)
                for x in self._get_field('Studies')]


class Study(OrthancObject):
    """ Orthanc study """
    def __init__(self, orthanc, id, patient=None, series=None):
        super(self.__class__,self).__init__(orthanc, 'studies', id)
        self._patient = patient

    @property
    def date(self):
        return dicom_date(self._get_tag('StudyDate'))

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
        return [Series(orthanc,x,study=self)
                for x in self._get_field('Series')]

    @property
    def patient(self):
        if self._patient is None:
            self._patient = Patient(self.orthanc,self._get_field('ParentPatient'))
        return self._patient


class Series():
    """ Orthanc series """
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
        return Study(orthanc, self._get_field('ParentStudy'))


class NewOrthancData():
    """ Access recently chnaged data as seen 
        through /changes interface
    """
    def __init__(self,orthanc):
        self.orthanc = orthanc

    def _get(self, changetype):
        last = 0
        done = False
        while not done:
            c = self.orthanc.changes(since=last)
            for x in c['Changes']: 
                if  x['ChangeType'] == changetype:
                    yield x['ID']
            done = c['Done']
            last = c['Last']

    def patients(self):
        """ returns list of "new" patients """
        return [Patient(self.orthanc,x) for x in self._get("StablePatient")]

    def studies(self):
        return [Study(self.orthanc,x) for x in self._get("StableStudy")]

    def series(self):
        return self._get("StableSeries")


class Orthanc():
    """ Direct interface to Orthanc REST API"""
    def __init__(self, host, user=None, password=None):
        self.host     = host
        self.user     = user
        self.password = password
        self.get_new  = NewOrthancData(self)

    def changes(self,limit=10,since=0):
        params = {'limit':limit, 'since':since}
        resp = self.get('/changes', params=params)
        return resp

    def get(self, path, auth=None, params=None):
        if self.user:
            auth = (self.user,self.password)
        return json.decode(requests.get('{}{}'.format(self.host,path),
                           auth=auth, params=params).content)

    def patient(self, id):
        return Patient(self, id)

    def study(self, id):
        return Study(self, id)

    def series(self, id):
        return Series(self, id)

    def put(self, path, data):
        pass


