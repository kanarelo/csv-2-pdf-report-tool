import os

import base64
import jinja2
import io
import math
import pdfkit
import PyPDF2 as pyPdf
import datetime

from reports import generate_report_context
from tempfile import NamedTemporaryFile

from PIL import Image as PILImage, ImageChops, ImageDraw
from pdf2image import convert_from_bytes

import numpy as np
from collections import namedtuple, OrderedDict

import weasyprint
import utils

def get_periods():
    return [
        'week',
        'quarter',
        'period',
        'year'
    ]
    
def get_report_names():
    return [
        'summary',
        'dz_payments', #-0
        'dz_orders',
        'payments',
        'orders', #-1
        'products',
        'traffic',
        'dpp', #-2
        'dpt',
        'upt',
        'tphw', #-3
        'sphw',
        'comps' ]

def get_totalled_reports(): 
    return [
        'summary', 'orders', 'payments',
        'products', 'dz_orders', 'dz_payments'
    ]

ReportMeta = namedtuple('ReportMeta', ('full_report_name', 'orientation', 'short_report_name', 'detailed_caption'))
def get_report_meta(report_name, period):
    period = period if period != 'period' else 'month'

    if period == 'year':
        postfix = 'this year and last year.'
    else:
        postfix = f'this {period}, last {period} and last year same {period}.'

    return {
        'summary': ReportMeta('Summary', 'portrait', 'summary', f'Overview of the main KPIs for the current {period}.'),
        'dz_payments': ReportMeta('Sales per Delivery Region', 'landscape', 'dz_payments', f'Payments made by delivery region, separated by Web/Retail for {postfix}'),
        'dz_orders': ReportMeta('Orders per Delivery Region', 'portrait', 'dz_orders', f'Orders made by delivery region, separated by Web/Retail for {postfix}'),
        'payments': ReportMeta('Sales', 'portrait', 'payments', f'Payments made by store, {postfix}'),
        'orders': ReportMeta('Orders', 'portrait', 'orders', f'Orders made by store, {postfix}'),
        'products': ReportMeta('Units', 'portrait', 'products', f'Unit sold (product) by store, {postfix}'),
        'traffic': ReportMeta('Traffic', 'portrait', 'traffic', f'Visits by store, {postfix}'),
        'dpp': ReportMeta('Units Price', 'portrait', 'dpp', f'Payments per unit sold (product) by store, {postfix}'),
        'dpt': ReportMeta('Average order sales', 'portrait', 'dpt', f'Payments per orders by store, {postfix}'),
        'upt': ReportMeta('Units per transaction', 'portrait', 'upt', f'Units per order by store, {postfix}'),
        'tphw': ReportMeta('Traffic per worked hours (TPWH)', 'portrait', 'tphw', f'Visits per hour worked by store, {postfix}'),
        'sphw': ReportMeta('Sales per worked hours (SPWH)', 'portrait', 'sphw', f'Sales per hour worked by store, {postfix}'),
        'comps': ReportMeta('Comparable store performance', 'portrait', 'comps', f'Comparable store performance by store, {postfix}'),
    }[report_name]

def create_report(report_name, period, index=0):
    (template_name, context) = generate_report_context(
        report_name, 
        period=period, 
        totalled_reports=get_totalled_reports())

    pdf_template = utils\
        .get_jinja_template_env()\
        .get_template(f'templates/reports/{template_name}')

    if index is not None:
        context['report_index'] = (index + 1)

    report_meta = get_report_meta(report_name, period)
    
    context['full_report_name'] = report_meta.full_report_name
    context['detailed_caption'] = report_meta.detailed_caption
    context['orientation'] = report_meta.orientation

    return pdf_template.render(**context)

class ReportBooklet(object):
    def __init__(self, title, report_names, period):
        self.title = title
        self.period = period

        self.report_names = report_names
        self.report_metas = None

    def create_report(self, report_name, index):
        return create_report(report_name, self.period, index=index)

    def get_report_metas(self): 
        if self.report_metas is None:
            self.report_metas = [
                get_report_meta(report_name, self.period) 
                    for report_name in self.report_names ]

        return self.report_metas

    def get_content(self):
        return "\n".join([
            self.create_report(report_name, i)
                for (i, report_name) in enumerate(self.report_names)])

get_quarter = lambda d: math.ceil(d.month/3.0)
class ReportBook(object):
    def __init__(self, document):
        self.document = document

    def get_no_of_pages():
        return len(self.document.pages)

    @staticmethod
    def assemble_report_book():
        report_book = ReportBook.generate_report_book()
        report_book.document.write_pdf(
            datetime.datetime.now().strftime('final_reports/BLSR_BOOK_%Y-%m-%d.pdf'))

    @staticmethod
    def assemble_report_booklets(date=None, period=None):
        date = date or datetime.datetime.now()

        for period in (period and [period] or get_periods()):
            report_book = ReportBook.generate_report_book(date=date, period=period)
            if period == 'week':
                period_stamp = '%Y-W%U'
            elif period == 'quarter':
                period_stamp = f'%Y-Q{get_quarter(date)}'
            elif period == 'period':
                period_stamp = '%Y-P%m'
            elif period == 'year':
                period_stamp = '%Y-FY'

            report_book.document.write_pdf(date.strftime(
                f'final_reports/BLSR_{period_stamp}_%Y-%m-%d.pdf'))

    @staticmethod
    def generate_report_book(date=None, period=None):
        report_names = get_report_names()
        booklets = []
        fiscal_period_format = '%Y'

        if date is None:
            date = datetime.datetime.now()

        if period is None:
            booklets += [
                ReportBooklet(date.strftime('WEEK FY%Y-W%U'), report_names, 'week'),
                ReportBooklet(date.strftime(f'QUARTER FY%Y-Q{get_quarter(date)}'), report_names, 'quarter'),
                ReportBooklet(date.strftime('PERIOD FY%Y-P%m'), report_names, 'period'),
                ReportBooklet(date.strftime('YEAR FY%Y'), report_names, 'year')]
        else:
            if period == 'week':
                fiscal_period_format = '%Y-W%U'
            elif period == 'quarter':
                fiscal_period_format = f'%Y-Q{get_quarter(date)}'
            elif period == 'period':
                fiscal_period_format = '%Y-P%m'
            
            booklets.append(
                ReportBooklet(date.strftime(f'{period.upper()} FY{fiscal_period_format}'), report_names, period))
        
        context = {
            'booklets': booklets,
            'period_pct_complete': '56%',
            'generated_on': date.strftime('%d/%m/%Y'),
            'fiscal_period': date.strftime(f'FY{fiscal_period_format}'),
            'generated_at': date.strftime('%I:%M%p'),
            'get_logo': lambda: get_base64(get_abs_path("assets/bonlogo.jpg"))}
        report_book_template = utils\
            .get_jinja_template_env()\
            .get_template(f"templates/report_book.html")
        report_book_html_content = report_book_template.render(**context)

        document = get_weasyprint_document(report_book_html_content)
        return ReportBook(document)

def get_weasyprint_document(html_content):
    font_config = weasyprint.fonts.FontConfiguration()
    return weasyprint\
        .HTML(string=html_content)\
        .render(
            stylesheets=[weasyprint.CSS(string=utils.get_css())], 
            font_config=font_config)

def get_base64(image, image_format='png', as_string=True):
    if type(image) == str:
        image = PILImage.open(image)
    
    with io.BytesIO() as temp:
        image.save(temp, image_format.upper(), resolution=80)
        temp.seek(0)

        if as_string:
            return f"data:image/{image_format};base64,{base64.b64encode(temp.read()).decode('utf-8')}"

        return temp

def get_abs_path(url):
    return os.path.join(os.path.dirname(__file__), url)

def generate_report_book():
    ReportBook.assemble_report_book()
