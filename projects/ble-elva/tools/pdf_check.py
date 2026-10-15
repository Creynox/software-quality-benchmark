"""Read/render a local benchmark download; does not generate or modify a PDF.

An unreadable application download is an artifact finding (INVALID_ARTIFACT),
not a harness failure. Only controller-side problems (missing libraries,
unsafe paths, artifact ACL) raise and therefore remain harness errors.
"""
import base64
import hashlib
from pathlib import Path
from sqbf.artifact_privacy import check_private_directory


def _invalid(data, code):
    return {'pdf_integrity':'INVALID_ARTIFACT','artifact_error':code,'pages':0,
            'required_identity_text_present':False,'sha256':hashlib.sha256(data).hexdigest(),
            'images':[],'extracted_text_not_returned':True}


def _squash(text):
    """Identity tokens are compared without whitespace: BLE's report layout wraps the sample code after a hyphen
    ("ENZBERG-20260508- NSN-014-02"), so text extraction inserts a space inside the code (dry run 15.10.2026)."""
    return ''.join(text.split())


def inspect_pdf(path,required_text):
    from pypdf import PdfReader
    from pypdf.errors import PyPdfError
    import pymupdf
    path=Path(path)
    if path.is_symlink():raise ValueError('PDF link not accepted')
    path=path.resolve(strict=True);check_private_directory(path.parent)
    data=path.read_bytes()
    if not 100<=len(data)<=25_000_000:return _invalid(data,'PDF_SIZE_OUT_OF_RANGE')
    if not data.startswith(b'%PDF-'):return _invalid(data,'NOT_A_PDF')
    try:
        reader=PdfReader(path,strict=True)
        if reader.is_encrypted:return _invalid(data,'PDF_ENCRYPTED')
        if not 1<=len(reader.pages)<=40:return _invalid(data,'PDF_PAGE_COUNT_UNSUPPORTED')
        text=' '.join(' '.join((page.extract_text() or '').split()) for page in reader.pages)
    except (PyPdfError,ValueError,KeyError,TypeError,OSError):
        return _invalid(data,'PDF_UNREADABLE')
    squashed=_squash(text)
    matches=all(_squash(token) in squashed for token in required_text)
    images=[]
    try:
        with pymupdf.open(path) as doc:
            if doc.is_encrypted or doc.page_count!=len(reader.pages):return _invalid(data,'PDF_STRUCTURE_CONTRADICTORY')
            for index in range(doc.page_count):
                page=doc[index]
                scale=min(1.5,1600/max(page.rect.width,page.rect.height))
                png=page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),alpha=False).tobytes('png')
                images.append(base64.b64encode(png).decode('ascii'))
    except (RuntimeError,ValueError):
        return _invalid(data,'PDF_NOT_RENDERABLE')
    return {'pdf_integrity':'PASS' if matches else 'FAIL','artifact_error':None if matches else 'IDENTITY_TEXT_MISSING',
            'pages':len(reader.pages),'required_identity_text_present':matches,
            'sha256':hashlib.sha256(data).hexdigest(),'images':images,'extracted_text_not_returned':True}
