import os
import pytest
pytest.importorskip('cryptography')
from cryptography.exceptions import InvalidTag
from duecare_eval.vault import seal, open_in_memory, compare_locally


def test_exact_bytes_and_random_nonce():
    original='A fictional case.\n  Preserve exact whitespace and Unicode: é.\n'.encode()
    key=os.urandom(32);a=seal(original,key);b=seal(original,key)
    assert a!=b and original not in a
    assert open_in_memory(a,key)==original
    receipt=compare_locally(a,key,lambda raw:{'items':1,'matches':raw==original})
    assert receipt['metrics']['matches'] is True
    assert original.decode() not in repr(receipt)


def test_wrong_key_and_tamper_fail_authentication():
    key=os.urandom(32);value=seal(b'fictional record',key)
    with pytest.raises(InvalidTag):open_in_memory(value,os.urandom(32))
    with pytest.raises(InvalidTag):open_in_memory(value[:-1]+bytes([value[-1]^1]),key)


def test_text_and_unexpected_receipt_fields_are_rejected():
    key=os.urandom(32);value=seal(b'fictional record',key)
    with pytest.raises(ValueError):compare_locally(value,key,lambda raw:{'reason':raw.decode()})
    with pytest.raises(ValueError):compare_locally(value,key,lambda raw:{'accuracy':float('nan')})
