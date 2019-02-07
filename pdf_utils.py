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
        'sphw' ]

def get_comparable_reports():
    return [
        'payments',
        'orders',
        'products',
        'traffic',
        'dpp',
        'dpt',
        'upt',
        'tphw',
        'sphw']

def get_totalled_reports(): 
    return [
        'summary', 'orders', 'payments',
        'products', 'dz_orders', 'dz_payments'
    ]

ReportMeta = namedtuple('ReportMeta', ('full_report_name', 'short_report_name', 'detailed_caption'))
def get_report_meta(report_name, period):
    period = period if period != 'period' else 'month'

    if period == 'year':
        postfix = 'this year and last year.'
    else:
        postfix = f'this {period}, last {period} and last year same {period}.'

    return {
        'summary': ReportMeta('Summary', 'summary', f'Overview of the main KPIs for the current {period}.'),
        'dz_payments': ReportMeta('Sales per Delivery Region', 'dz_payments', f'Payments made by delivery region, separated by Web/Retail for {postfix}'),
        'dz_orders': ReportMeta('Orders per Delivery Region', 'dz_orders', f'Orders made by delivery region, separated by Web/Retail for {postfix}'),
        'payments': ReportMeta('Sales', 'payments', f'Payments made by store, {postfix}'),
        'orders': ReportMeta('Orders', 'orders', f'Orders made by store, {postfix}'),
        'products': ReportMeta('Products', 'products', f'Products sold (unit) by store, {postfix}'),
        'traffic': ReportMeta('Traffic', 'traffic', f'Visits by store, {postfix}'),
        'dpp': ReportMeta('Dollars Per Product', 'dpp', f'Payments per product sold (unit) by store, {postfix}'),
        'dpt': ReportMeta('Dollars Per Order', 'dpt', f'Payments per product sold (unit) by store, {postfix}'),
        'upt': ReportMeta('Products Per Order', 'upt', f'Payments per order by store, {postfix}'),
        'tphw': ReportMeta('Traffic Per Worked Hours', 'tphw', f'Visits per hour worked by store, {postfix}'),
        'sphw': ReportMeta('Sales Per Worked Hours', 'sphw', f'Sales per hour worked by store, {postfix}'),
    }[report_name]

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

def generate_report_book(period=None, close_files=False):
    template_env = utils.get_jinja_template_env()

    class ReportBooklet(object):
        def __init__(self, title, report_names, period):
            self.title = title
            self.period = period

            self.report_names = report_names
            self.report_metas = None

        def get_report_metas(self): 
            if self.report_metas is None:
                self.report_metas = [
                    get_report_meta(report_name, self.period) 
                        for report_name in self.report_names ]

            return self.report_metas

        def get_content(self):
            report_book_template = template_env.get_template(f"templates/report_book.html")
            (template_name, context) = generate_report_context(
                report_name, 
                period=self.period, 
                totalled_reports=get_totalled_reports(),
                comparable_reports=get_comparable_reports())

            pdf_template = template_env.get_template(f'templates/{template_name}')
            return pdf_template.render(**context)

    class ReportBook(object):
        def __init__(self, sections, document):
            self.sections = sections
            self.document = document

            self.pages = None

        def get_no_of_pages():
            return len(self.document.pages)

        @staticmethod
        def assemble_report_book(pdf_file=None):
            if pdf_file is None:
                pdf_file = io.BytesIO()

            report_book = ReportBook.generate_report_book()
            report_book.document.save_pdf(pdf_file)

        @staticmethod
        def generate_report_book(date=None, period=None):
            get_quarter = lambda d: math.ceil(d.month/3.0)
            report_names = get_report_names()
            booklets = []

            if date is None:
                date = datetime.datetime.now()

            if period is None:
                booklets += [
                    ReportBooklet(date.strftime('WEEK %Y-W%V'), report_names, 'week'),
                    ReportBooklet(date.strftime('QUARTER %Y-Q%d' % get_quarter(date)), report_names, 'quarter'),
                    ReportBooklet(date.strftime('PERIOD %Y-P%m'), report_names, 'period'),
                    ReportBooklet(date.strftime('YEAR %Y'), report_names, 'year')]
            elif period == 'week':
                booklets.append(
                    ReportBooklet(date.strftime('WEEK %Y-W%V'), report_names, 'week'))
            elif period == 'quarter':
                booklets.append(
                    ReportBooklet(date.strftime('QUARTER %Y-Q%d' % get_quarter(date)), report_names, 'quarter'))
            elif period == 'period':
                booklets.append(
                    ReportBooklet(date.strftime('PERIOD %Y-P%m'), report_names, 'period'))
            elif period == 'year':
                booklets.append(
                    ReportBooklet(date.strftime('YEAR %Y'), report_names, 'year'))

            context = {
                'booklets': booklets,
                'generated_on': date.strftime('%D/%M/%Y'),
                'fiscal_period': date.strftime('2019-W%V'),
                'generated_at': date.strftime('%I:%S%p'),
                'get_logo': lambda: get_base64(get_abs_path("assets/bonlogo.jpg"))}
            report_book_template     = template_env.get_template(f"templates/report_book.html")
            report_book_html_content = report_book_template.render(**context)

            document = get_weasyprint_document(report_book_html_content)

            return ReportBook(document)

    #-------------------
    with open('latest_report.pdf', 'wb') as temp:
        temp.write(ReportBook.assemble_report_book())
