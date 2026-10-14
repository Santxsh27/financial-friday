"""Optional independent Google OCR. Configuration never implies it ran."""
import base64
import os
import re
from decimal import Decimal, InvalidOperation


class GoogleDocumentGrounder:
    def __init__(self, processor, session=None):
        if not re.fullmatch(r"projects/[A-Za-z0-9_-]+/locations/(us|eu|asia-south1)/processors/[A-Za-z0-9_-]+",processor):
            raise ValueError("Use an exact Document AI processor resource in an approved US/EU/Mumbai location")
        self.processor=processor
        self.location=processor.split('/')[3]
        if session is None:
            import google.auth
            from google.auth.transport.requests import AuthorizedSession
            credentials,_=google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
            session=AuthorizedSession(credentials)
        self.session=session

    @staticmethod
    def page_count(data, mime, max_pages=3):
        if mime == 'application/pdf':
            from io import BytesIO
            from pypdf import PdfReader
            try:
                reader = PdfReader(BytesIO(data), strict=True)
                if reader.is_encrypted:
                    raise ValueError('Encrypted PDFs are not admitted; never upload a document password')
                count = len(reader.pages)
            except Exception as error:
                raise ValueError('The PDF could not be safely read before OCR') from error
            if not 1 <= count <= max_pages:
                raise ValueError(f'For this demo, choose a PDF of one to {max_pages} pages before OCR')
            return count
        if mime not in {'image/png','image/jpeg','image/webp'}:
            raise ValueError('Unsupported OCR document type')
        return 1

    def read(self, data, mime, *, max_pages=3):
        page_count = self.page_count(data, mime, max_pages)
        response=self.session.post(f'https://{self.location}-documentai.googleapis.com/v1/{self.processor}:process',
            json={"rawDocument":{"content":base64.b64encode(data).decode(),"mimeType":mime}},timeout=60)
        response.raise_for_status()
        doc=response.json()['document']
        text=doc.get('text','')
        if not text or len(text)>60000 or len(doc.get('pages',[]))>page_count:
            raise ValueError("OCR is empty or exceeds the admitted page/text bounds")
        lines=[]
        for number,page in enumerate(doc.get('pages',[]),1):
            for line in page.get('lines',[]):
                layout=line.get('layout',{})
                segments=layout.get('textAnchor',{}).get('textSegments',[])
                for span in segments:
                    start,end=int(span.get('startIndex',0)),int(span['endIndex'])
                    if not 0<=start<end<=len(text):raise ValueError('Invalid OCR text anchors')
                    lines.append({'page':number,'start':start,'end':end,
                        'box':layout.get('boundingPoly',{}).get('normalizedVertices',[]),
                        'confidence':layout.get('confidence')})
        return {'text':text,'lines':lines,'mode':'DOCUMENT_AI_OCR','processor':self.processor}


def configured_grounder():
    processor=os.getenv('FRIDAY_DOCUMENT_AI_PROCESSOR')
    return GoogleDocumentGrounder(processor) if processor else None


def value_supported(field, value, quote):
    if field=='total':
        try:
            return any(Decimal(raw.replace(',',''))==Decimal(value) for raw in re.findall(r'\d[\d,]*(?:\.\d+)?',quote))
        except InvalidOperation:return False
    if field=='currency':
        return value=='UNKNOWN' or value.lower() in quote.lower() or value=='INR' and '₹' in quote
    return re.sub(r'\W','',str(value).lower()) in re.sub(r'\W','',quote.lower())


def ground_facts(facts, ocr):
    anchors=[];unsupported=[]
    for q in facts.quotes:
        start=ocr['text'].find(q.quote)
        value=getattr(facts,q.field,None)
        if start<0 or value is None or not value_supported(q.field,value,q.quote):
            unsupported.append(q.field);continue
        relevant=[line for line in ocr['lines'] if line['start']<start+len(q.quote) and line['end']>start]
        if not relevant or any(type(line.get('confidence')) not in {int,float} or line['confidence']<0.8 for line in relevant):
            unsupported.append(q.field)
        anchors.append({'field':q.field,'quote':q.quote,'start':start,'end':start+len(q.quote),'locations':relevant})
    # Model omissions must not turn an unquoted field into independent evidence.
    supported = {anchor['field'] for anchor in anchors if anchor['field'] not in unsupported}
    if facts.currency != 'UNKNOWN' and 'currency' not in supported:
        # An explicit currency on the independently anchored total's SAME line
        # can supply the missing currency quote. Never search the whole invoice
        # for a convenient code, infer from a recipient, or interpret a bare "$".
        totals = [anchor for anchor in anchors if anchor['field']=='total' and 'total' not in unsupported]
        for anchor in totals:
            for line in anchor['locations']:
                text = ocr['text'][line['start']:line['end']]
                labels = set(re.findall(r'\b(?:INR|USD|EUR|GBP|AUD|SGD|JPY)\b|₹',text))
                codes = {'INR' if label=='₹' else label for label in labels}
                if codes != {facts.currency}: continue
                quote = next(label for label in labels if label==facts.currency or label=='₹' and facts.currency=='INR')
                start = line['start'] + text.index(quote)
                anchors.append({'field':'currency','quote':quote,'start':start,'end':start+len(quote),'locations':[line]})
                supported.add('currency'); break
            if 'currency' in supported: break
    for field in ('supplier','reference','total','currency','payee'):
        value = getattr(facts,field,None)
        if value is not None and value != 'UNKNOWN' and field not in supported:
            unsupported.append(field)
    return {'mode':ocr['mode'],'field_anchors':anchors,'unsupported_fields':sorted(set(unsupported)),
        'authenticity_verified':False,'processor':ocr.get('processor'),'raw_ocr_stored':False}
