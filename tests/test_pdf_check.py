import importlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

module=importlib.import_module('projects.ble-elva.tools.pdf_check')


class PdfCheckTests(unittest.TestCase):
    def test_non_pdf_or_oversized_artifact_not_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'not-pdf.pdf';path.write_bytes(b'not a PDF'*30)
            with patch.object(module,'check_private_directory'):
                with self.assertRaises(ValueError):module.inspect_pdf(path,['synthetic'])

    def test_encrypted_pdf_and_missing_required_identity_are_not_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'mock.pdf';path.write_bytes(b'%PDF-1.7\n'+b' '*200)
            with patch.object(module,'check_private_directory'),patch('pypdf.PdfReader') as reader:
                reader.return_value.is_encrypted=True
                with self.assertRaises(ValueError):module.inspect_pdf(path,['synthetic'])
