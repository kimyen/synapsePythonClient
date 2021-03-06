import filecmp
import traceback
from io import open

from nose.tools import assert_equals, assert_true, assert_is_not_none

import synapseclient.core.config
from synapseclient.core.utils import *
from synapseclient.core.exceptions import *
from synapseclient import *
from synapseclient.core.upload import multipart_upload
from synapseclient.core.upload.multipart_upload import *
from tests import integration
from tests.integration import schedule_for_cleanup


def setup(module):
    module.syn = integration.syn
    module.project = integration.project


def test_round_trip():
    fhid = None
    filepath = utils.make_bogus_binary_file(MIN_PART_SIZE + 777771)
    try:
        fhid = multipart_upload_file(syn, filepath)

        # Download the file and compare it with the original
        junk = File(parent=project, dataFileHandleId=fhid)
        junk.properties.update(syn._createEntity(junk.properties))
        (tmp_f, tmp_path) = tempfile.mkstemp()
        schedule_for_cleanup(tmp_path)

        junk['path'] = syn._downloadFileHandle(fhid, junk['id'], 'FileEntity', tmp_path)
        assert_true(filecmp.cmp(filepath, junk.path))

    finally:
        try:
            if 'junk' in locals():
                syn.delete(junk)
        except Exception:
            print(traceback.format_exc())
        try:
            os.remove(filepath)
        except Exception:
            print(traceback.format_exc())


def test_single_thread_upload():
    synapseclient.core.config.single_threaded = True
    try:
        filepath = utils.make_bogus_binary_file(MIN_PART_SIZE * 2 + 1)
        assert_is_not_none(multipart_upload_file(syn, filepath))
    finally:
        synapseclient.core.config.single_threaded = False


def test_randomly_failing_parts():
    FAILURE_RATE = 1.0/3.0
    fhid = None
    MIN_PART_SIZE = 5 * MB
    MAX_RETRIES = 20

    filepath = utils.make_bogus_binary_file(MIN_PART_SIZE * 2 + 777771)

    normal_put_chunk = None

    def _put_chunk_or_fail_randomly(url, chunk, verbose=False):
        if random.random() < FAILURE_RATE:
            raise IOError("Ooops! Artificial upload failure for testing.")
        else:
            return normal_put_chunk(url, chunk, verbose)

    # Mock _put_chunk to fail randomly
    normal_put_chunk = multipart_upload._put_chunk
    multipart_upload._put_chunk = _put_chunk_or_fail_randomly

    try:
        fhid = multipart_upload_file(syn, filepath)

        # Download the file and compare it with the original
        junk = File(parent=project, dataFileHandleId=fhid)
        junk.properties.update(syn._createEntity(junk.properties))
        (tmp_f, tmp_path) = tempfile.mkstemp()
        schedule_for_cleanup(tmp_path)

        junk['path'] = syn._downloadFileHandle(fhid, junk['id'], 'FileEntity', tmp_path)
        assert_true(filecmp.cmp(filepath, junk.path))

    finally:
        # Un-mock _put_chunk
        if normal_put_chunk:
            multipart_upload._put_chunk = normal_put_chunk

        try:
            if 'junk' in locals():
                syn.delete(junk)
        except Exception:
            print(traceback.format_exc())
        try:
            os.remove(filepath)
        except Exception:
            print(traceback.format_exc())


def test_multipart_upload_big_string():
    cities = ["Seattle", "Portland", "Vancouver", "Victoria",
              "San Francisco", "Los Angeles", "New York",
              "Oaxaca", "Cancún", "Curaçao", "जोधपुर",
              "অসম", "ལྷ་ས།", "ཐིམ་ཕུ་", "دبي", "አዲስ አበባ",
              "São Paulo", "Buenos Aires", "Cartagena",
              "Amsterdam", "Venice", "Rome", "Dubrovnik",
              "Sarajevo", "Madrid", "Barcelona", "Paris",
              "Αθήνα", "Ρόδος", "København", "Zürich",
              "金沢市", "서울", "แม่ฮ่องสอน", "Москва"]

    text = "Places I wanna go:\n"
    while len(text.encode('utf-8')) < MIN_PART_SIZE:
        text += ", ".join(random.choice(cities) for i in range(5000)) + "\n"

    fhid = multipart_upload_string(syn, text)

    # Download the file and compare it with the original
    junk = File(parent=project, dataFileHandleId=fhid)
    junk.properties.update(syn._createEntity(junk.properties))
    (tmp_f, tmp_path) = tempfile.mkstemp()
    schedule_for_cleanup(tmp_path)

    junk['path'] = syn._downloadFileHandle(fhid, junk['id'], "FileEntity", tmp_path)

    with open(junk.path, encoding='utf-8') as f:
        retrieved_text = f.read()

    assert_equals(retrieved_text, text)

