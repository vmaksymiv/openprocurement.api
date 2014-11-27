# -*- coding: utf-8 -*-
from cornice.resource import resource, view
from openprocurement.api.models import Document
from openprocurement.api.utils import (
    filter_data,
    generate_id,
    get_file,
    save_tender,
    upload_file,
)
from openprocurement.api.validation import (
    validate_file_update,
    validate_file_upload,
    validate_patch_document_data,
    validate_tender_award_document_exists,
    validate_tender_award_exists_by_award_id,
)


@resource(name='Tender Award Documents',
          collection_path='/tenders/{tender_id}/awards/{award_id}/documents',
          path='/tenders/{tender_id}/awards/{award_id}/documents/{id}',
          description="Tender award documents")
class TenderAwardDocumentResource(object):

    def __init__(self, request):
        self.request = request
        self.db = request.registry.db

    @view(renderer='json', validators=(validate_tender_award_exists_by_award_id,))
    def collection_get(self):
        """Tender Award Documents List"""
        award = self.request.validated['award']
        if self.request.params.get('all', ''):
            collection_data = [i.serialize("view") for i in award['documents']]
        else:
            collection_data = sorted(dict([
                (i.id, i.serialize("view"))
                for i in award['documents']
            ]).values(), key=lambda i: i['dateModified'])
        return {'data': collection_data}

    @view(renderer='json', validators=(validate_file_upload, validate_tender_award_exists_by_award_id,))
    def collection_post(self):
        """Tender Award Document Upload
        """
        tender = self.request.validated['tender']
        if tender.status != 'qualification':
            self.request.errors.add('body', 'data', 'Can\'t add document in current tender status')
            self.request.errors.status = 403
            return
        src = tender.serialize("plain")
        data = self.request.validated['file']
        document = Document()
        document.id = generate_id()
        document.title = data.filename
        document.format = data.type
        key = generate_id()
        document.url = self.request.route_url('Tender Award Documents', tender_id=tender.id, award_id=self.request.validated['award_id'], id=document.id, _query={'download': key})
        self.request.validated['award'].documents.append(document)
        upload_file(tender, document, key, data.file, self.request)
        save_tender(tender, src, self.request)
        self.request.response.status = 201
        self.request.response.headers['Location'] = self.request.route_url('Tender Award Documents', tender_id=tender.id, award_id=self.request.validated['award_id'], id=document.id)
        return {'data': document.serialize("view")}

    @view(renderer='json', validators=(validate_tender_award_document_exists,))
    def get(self):
        """Tender Award Document Read"""
        document = self.request.validated['document']
        key = self.request.params.get('download')
        if key:
            return get_file(self.request.validated['tender'], document, key, self.db, self.request)
        document_data = document.serialize("view")
        document_data['previousVersions'] = [
            i.serialize("view")
            for i in self.request.validated['documents']
            if i.url != document.url
        ]
        return {'data': document_data}

    @view(renderer='json', validators=(validate_file_update, validate_tender_award_document_exists,))
    def put(self):
        """Tender Award Document Update"""
        tender = self.request.validated['tender']
        if tender.status != 'qualification':
            self.request.errors.add('body', 'data', 'Can\'t update document in current tender status')
            self.request.errors.status = 403
            return
        first_document = self.request.validated['documents'][0]
        src = tender.serialize("plain")
        if self.request.content_type == 'multipart/form-data':
            data = self.request.validated['file']
            filename = data.filename
            content_type = data.type
            in_file = data.file
        else:
            filename = first_document.title
            content_type = self.request.content_type
            in_file = self.request.body_file
        document = Document()
        document.id = self.request.matchdict['id']
        document.title = filename
        document.format = content_type
        document.datePublished = first_document.datePublished
        key = generate_id()
        document.url = self.request.route_url('Tender Award Documents', tender_id=tender.id, award_id=self.request.validated['award_id'], id=document.id, _query={'download': key})
        self.request.validated['award'].documents.append(document)
        upload_file(tender, document, key, in_file, self.request)
        save_tender(tender, src, self.request)
        return {'data': document.serialize("view")}

    @view(renderer='json', validators=(validate_patch_document_data, validate_tender_award_document_exists,))
    def patch(self):
        """Tender Award Document Update"""
        tender = self.request.validated['tender']
        if tender.status != 'qualification':
            self.request.errors.add('body', 'data', 'Can\'t update document in current tender status')
            self.request.errors.status = 403
            return
        document = self.request.validated['document']
        document_data = filter_data(self.request.validated['data'])
        if document_data:
            src = tender.serialize("plain")
            document.import_data(document_data)
            save_tender(tender, src, self.request)
        return {'data': document.serialize("view")}