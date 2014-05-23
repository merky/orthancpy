# Orthancpy

This is an incomplete interface to Orthanc REST, organized in
a way that is convenient for me, and possibly not anyone else.

    import orthancpy
    orthanc = orthancpy.Orthanc('http://localhost:8042')

    studies = orthanc.get_new.studies()

    for study in studies:
        print study.patient.name
        print study.patient.patient_id

