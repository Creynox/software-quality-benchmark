"""Read/render a local benchmark download; does not generate or modify a PDF."""
import base64
import hashlib
from pathlib import Path
from sqbf.artifact_privacy import check_private_directory


def inspect_pdf(path,required_text):
    from pypdf import PdfReader
    import pymupdf
    path=Path(path)
    if path.is_symlink():raise ValueError('PDF link not accepted')
    path=path.resolve(strict=True);check_private_directory(path.parent)
    if not 100<=path.stat().st_size<=25_000_000:raise ValueError('PDF size/type not accepted')
    data=path.read_bytes()
    if not data.startswith(b'%PDF-'):raise ValueError('Not a PDF')
    reader=PdfReader(path,strict=True)
    if reader.is_encrypted or not 1<=len(reader.pages)<=40:raise ValueError('Unsupported PDF')
    text=' '.join(' '.join((page.extract_text() or '').split()) for page in reader.pages)
    matches=all(' '.join(token.split()) in text for token in required_text)
    images=[]
    with pymupdf.open(path) as doc:
        if doc.is_encrypted or doc.page_count!=len(reader.pages):raise ValueError('Contradictory PDF structure')
        for index in range(doc.page_count):
            page=doc[index]
            scale=min(1.5,1600/max(page.rect.width,page.rect.height))
            png=page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),alpha=False).tobytes('png')
            images.append(base64.b64encode(png).decode('ascii'))
    return {'pdf_integrity':'PASS' if matches else 'FAIL','pages':len(reader.pages),'required_identity_text_present':matches,
            'sha256':hashlib.sha256(data).hexdigest(),'images':images,'extracted_text_not_returned':True}
