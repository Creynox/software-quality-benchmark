import importlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

module=importlib.import_module('projects.ble-elva.tools.pdf_check')


def synthetic_pdf(path,text):
    import pymupdf
    with pymupdf.open() as doc:
        page=doc.new_page();page.insert_text((72,72),text);doc.save(path)


class PdfCheckTests(unittest.TestCase):
    def inspect(self,path,required=('synthetic',)):
        with patch.object(module,'check_private_directory'):
            return module.inspect_pdf(path,list(required))

    def test_non_pdf_or_out_of_range_download_is_an_invalid_artifact_not_a_harness_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'not-pdf.pdf';path.write_bytes(b'not a PDF'*30)
            result=self.inspect(path)
            self.assertEqual((result['pdf_integrity'],result['artifact_error']),('INVALID_ARTIFACT','NOT_A_PDF'))
            self.assertEqual(result['images'],[]);self.assertEqual(len(result['sha256']),64)
            path.write_bytes(b'%PDF-1.7');result=self.inspect(path)
            self.assertEqual(result['artifact_error'],'PDF_SIZE_OUT_OF_RANGE')

    def test_encrypted_or_structurally_broken_pdf_is_an_invalid_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'mock.pdf';path.write_bytes(b'%PDF-1.7\n'+b' '*200)
            with patch('pypdf.PdfReader') as reader:
                reader.return_value.is_encrypted=True
                self.assertEqual(self.inspect(path)['artifact_error'],'PDF_ENCRYPTED')
            path.write_bytes(b'%PDF-1.7\n'+b'garbage without objects or trailer '*10)
            result=self.inspect(path)
            self.assertEqual((result['pdf_integrity'],result['artifact_error']),('INVALID_ARTIFACT','PDF_UNREADABLE'))

    def test_readable_pdf_requires_every_identity_token_and_returns_no_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'report.pdf';synthetic_pdf(path,'SYNTHETIC-01 Synthetic stone Enzberg')
            result=self.inspect(path,('SYNTHETIC-01','Synthetic stone','Enzberg'))
            self.assertEqual((result['pdf_integrity'],result['artifact_error'],result['pages']),('PASS',None,1))
            self.assertEqual(len(result['images']),1);self.assertTrue(result['extracted_text_not_returned'])
            self.assertNotIn('SYNTHETIC-01',str({k:v for k,v in result.items() if k!='images'}))
            result=self.inspect(path,('SYNTHETIC-02','Enzberg'))
            self.assertEqual((result['pdf_integrity'],result['artifact_error']),('FAIL','IDENTITY_TEXT_MISSING'))

    def test_a_sample_code_wrapped_after_a_hyphen_still_matches_but_other_codes_do_not(self):
        # BLE's report layout breaks "ENZBERG-20260508-NSN-014-02" after a hyphen; extraction then reads "20260508- NSN".
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'wrapped.pdf'
            synthetic_pdf(path,'Probe SYNTH-20260508-\nNSN-014-02 Produkt Synthetic stone Werk Enzberg')
            result=self.inspect(path,('SYNTH-20260508-NSN-014-02','Synthetic stone Werk Enzberg','Enzberg'))
            self.assertEqual((result['pdf_integrity'],result['artifact_error']),('PASS',None))
            for wrong in ('SYNTH-20260508-NSN-014-03','SYNTH-20260509-NSN-014-02','Synthetic stone Werk Other'):
                result=self.inspect(path,(wrong,))
                self.assertEqual((result['pdf_integrity'],result['artifact_error']),('FAIL','IDENTITY_TEXT_MISSING'),wrong)

    def test_controller_side_path_problems_still_raise(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):self.inspect(Path(directory)/'missing.pdf')
